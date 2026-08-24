from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError
from datetime import datetime, timezone
import os
import sys
import subprocess
import re
import urllib.parse
import logging
from bson.objectid import ObjectId

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import Config

logger = logging.getLogger(__name__)


def _env_int(name, default, min_value=None, max_value=None):
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    if min_value is not None:
        value = max(min_value, value)
    if max_value is not None:
        value = min(max_value, value)
    return value


def _normalize_email(email):
    return (email or "").strip().lower()


def _should_try_srv_fallback(exc):
    text = str(exc).lower()
    return any(
        marker in text
        for marker in (
            "dns",
            "srv",
            "resolution",
            "resolve",
            "name or service not known",
            "temporary failure",
            "query name does not exist",
        )
    )


def _resolve_mongodb_srv_via_nslookup(uri):
    """
    Fallback: resuelve mongodb+srv usando nslookup cuando la resolución DNS de Python falla.
    """
    try:
        parsed = urllib.parse.urlparse(uri)
        if parsed.scheme != "mongodb+srv":
            return None
        netloc = parsed.netloc
        if "@" in netloc:
            auth, host = netloc.rsplit("@", 1)
        else:
            auth, host = "", netloc
        host_clean = host.split("/")[0].split("?")[0]
        srv_host = f"_mongodb._tcp.{host_clean}"
        result = subprocess.run(
            ["nslookup", "-type=SRV", srv_host, "8.8.8.8"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return None
        shards = re.findall(r"svr hostname\s*=\s*(\S+\.mongodb\.net)", result.stdout)
        if not shards:
            return None
        db_name = Config.MONGODB_DB_NAME or "webdevai"
        hosts_str = ",".join(f"{s}:27017" for s in shards[:3])
        host0 = (shards[0] or "").split(".")[0]
        m = re.match(r"^(.+)-shard-\d+-\d+$", host0)
        replica_set = f"atlas-{m.group(1)}-shard-0" if m else None
        if not replica_set:
            return None
        opts = f"ssl=true&replicaSet={replica_set}&authSource=admin&retryWrites=true&w=majority"
        return f"mongodb://{auth}@{hosts_str}/{db_name}?{opts}"
    except Exception:
        return None


class ChatDatabase:
    """
    Clase para manejar la conexión y operaciones con MongoDB (usuarios, chats y proyectos).
    """
    def __init__(self):
        try:
            uri = (Config.MONGODB_URI or "").strip()
            if not uri:
                raise ValueError("MONGODB_URI no está configurada.")
            if not (uri.startswith('mongodb://') or uri.startswith('mongodb+srv://')):
                raise ValueError("URI inválida: debe comenzar con 'mongodb://' o 'mongodb+srv://'.")
            
            client_options = {
                "serverSelectionTimeoutMS": _env_int("MONGODB_SERVER_SELECTION_TIMEOUT_MS", 15000, min_value=1000),
                "connectTimeoutMS": _env_int("MONGODB_CONNECT_TIMEOUT_MS", 10000, min_value=1000),
                "socketTimeoutMS": _env_int("MONGODB_SOCKET_TIMEOUT_MS", 20000, min_value=1000),
                "retryWrites": True,
                "retryReads": True,
            }

            parsed_uri = urllib.parse.urlparse(uri)
            attempt_uris = [uri]
            fallback_attempted = False
            last_error = None
            index = 0

            while index < len(attempt_uris):
                attempt_uri = attempt_uris[index]
                index += 1
                if not attempt_uri:
                    continue
                try:
                    self.client = MongoClient(attempt_uri, **client_options)
                    self.db = self.client[Config.MONGODB_DB_NAME]
                    self.conversations = self.db['conversations']
                    self.messages = self.db['messages']
                    self.users = self.db['users']
                    self.projects = self.db['projects']
                    
                    self.has_primary = self._has_primary()
                    self._ensure_indexes()
                    logger.info("Conexión exitosa a MongoDB (%s)", Config.MONGODB_DB_NAME)
                    return
                except Exception as e:
                    last_error = e
                    if parsed_uri.scheme == "mongodb+srv" and not fallback_attempted and _should_try_srv_fallback(e):
                        fallback_attempted = True
                        fallback_uri = _resolve_mongodb_srv_via_nslookup(uri)
                        if fallback_uri:
                            attempt_uris.append(fallback_uri)
                            continue
                    if _should_try_srv_fallback(e):
                        continue
                    break
            raise last_error
        except Exception as e:
            logger.error("Error al conectar con MongoDB: %s", e)
            self.client = None

    def _has_primary(self) -> bool:
        try:
            td = getattr(self.client, "topology_description", None)
            if not td:
                return False
            return "RSPrimary" in str(td)
        except Exception:
            return False

    def _ensure_indexes(self):
        try:
            if not getattr(self, "has_primary", False):
                return
            index_specs = (
                (self.users, [('email', ASCENDING)], {"unique": True, "name": "email_unique"}),
                (self.users, [('github_id', ASCENDING)], {"unique": True, "sparse": True, "name": "github_id_unique_sparse"}),
                (self.users, [('google_id', ASCENDING)], {"unique": True, "sparse": True, "name": "google_id_unique_sparse"}),
                (self.conversations, [('user_id', ASCENDING), ('updated_at', DESCENDING)], {"name": "user_updated_at"}),
                (self.messages, [('conversation_id', ASCENDING), ('timestamp', ASCENDING)], {"name": "conversation_timestamp"}),
                (self.projects, [('created_at', DESCENDING)], {"name": "created_at_desc"}),
            )
            for collection, keys, kwargs in index_specs:
                try:
                    collection.create_index(keys, **kwargs)
                except OperationFailure as e:
                    logger.warning("No se pudo crear índice %s.%s: %s", collection.name, kwargs.get("name", keys), e)
        except Exception as e:
            logger.warning("Error al crear índices: %s", e)

    def _ensure_connection(self):
        if not self.client:
            logger.error("Error: MongoDB no conectado.")
            return False
        return True

    # Métodos de Usuario
    def create_user(self, email, password_hash):
        if not self._ensure_connection():
            return None
        email = _normalize_email(email)
        if not email:
            return None
        user_data = {
            'email': email,
            'password': password_hash,
            'created_at': datetime.now(timezone.utc)
        }
        result = self.users.insert_one(user_data)
        return str(result.inserted_id)

    def get_user_by_email(self, email):
        if not self._ensure_connection():
            return None
        email = _normalize_email(email)
        if not email:
            return None
        try:
            return self.users.find_one({'email': email})
        except Exception as e:
            logger.warning("Error buscando usuario por email: %s", e)
            return None

    def get_user_by_google_id(self, google_id):
        if not self._ensure_connection():
            return None
        return self.users.find_one({'google_id': google_id})

    def create_google_user(self, email, google_id, name=None):
        if not self._ensure_connection():
            return None
        email = _normalize_email(email)
        if not email:
            return None
        user_data = {
            'email': email,
            'google_id': google_id,
            'name': name or '',
            'password': None,
            'created_at': datetime.now(timezone.utc)
        }
        result = self.users.insert_one(user_data)
        return str(result.inserted_id)

    def link_google_to_user(self, user_id, google_id, name=None):
        if not self._ensure_connection():
            return False
        try:
            self.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'google_id': google_id, 'name': name or ''}}
            )
            return True
        except Exception:
            return False

    def get_user_by_github_id(self, github_id):
        if not self._ensure_connection():
            return None
        return self.users.find_one({'github_id': github_id})

    def create_github_user(self, email, github_id, name=None):
        if not self._ensure_connection():
            return None
        email = _normalize_email(email)
        if not email:
            return None
        user_data = {
            'email': email,
            'github_id': github_id,
            'name': name or '',
            'password': None,
            'created_at': datetime.now(timezone.utc)
        }
        result = self.users.insert_one(user_data)
        return str(result.inserted_id)

    def link_github_to_user(self, user_id, github_id, name=None):
        if not self._ensure_connection():
            return False
        try:
            self.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'github_id': github_id, 'name': name or ''}}
            )
            return True
        except Exception:
            return False

    def get_user_by_id(self, user_id):
        if not self._ensure_connection():
            return None
        try:
            return self.users.find_one({'_id': ObjectId(user_id)})
        except Exception:
            return None

    # Métodos de Conversación
    def create_conversation(self, user_id, title="Nueva Conversación"):
        if not self._ensure_connection():
            return None
        conversation = {
            'user_id': user_id,
            'title': title,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
        }
        result = self.conversations.insert_one(conversation)
        return str(result.inserted_id)

    def save_message(self, conversation_id, role, content):
        if not self._ensure_connection():
            return False
        message = {
            'conversation_id': conversation_id,
            'role': role,
            'content': content,
            'timestamp': datetime.now(timezone.utc)
        }
        self.messages.insert_one(message)
        self.conversations.update_one(
            {'_id': conversation_id},
            {'$set': {'updated_at': datetime.now(timezone.utc)}}
        )
        return True

    def get_conversation_history(self, conversation_id, limit=None, skip=0, newest_first=False):
        if not self._ensure_connection():
            return []
        try:
            conv_id = ObjectId(conversation_id)
        except Exception:
            return []
        query = self.messages.find({'conversation_id': conv_id}).sort('timestamp', -1 if newest_first else 1)
        if skip:
            query = query.skip(skip)
        if limit is not None:
            query = query.limit(limit)
        messages = list(query)
        
        for msg in messages:
            msg['_id'] = str(msg['_id'])
            msg['conversation_id'] = str(msg['conversation_id'])
        return messages

    def get_conversation_history_tail(self, conversation_id, limit=80):
        if not self._ensure_connection():
            return []
        try:
            conv_id = ObjectId(conversation_id)
        except Exception:
            return []
        if limit < 1:
            return []
        cursor = self.messages.find({'conversation_id': conv_id}).sort('timestamp', -1).limit(limit)
        messages = list(cursor)
        messages.reverse()
        for msg in messages:
            msg['_id'] = str(msg['_id'])
            msg['conversation_id'] = str(msg['conversation_id'])
        return messages

    def get_conversation_user_id(self, conversation_id):
        if not self._ensure_connection():
            return None
        try:
            oid = conversation_id if isinstance(conversation_id, ObjectId) else ObjectId(conversation_id)
        except Exception:
            return None
        doc = self.conversations.find_one({'_id': oid}, {'user_id': 1})
        if not doc:
            return None
        uid = doc.get('user_id')
        return str(uid) if uid is not None else None

    def get_user_conversations(self, user_id, limit=None, skip=0, archived=False):
        if not self._ensure_connection():
            return []
        query_filter = {'user_id': user_id}
        if archived:
            query_filter['archived'] = True
        else:
            query_filter['archived'] = {'$ne': True}
        query = self.conversations.find(query_filter).sort('updated_at', -1)
        if skip:
            query = query.skip(skip)
        if limit is not None:
            query = query.limit(limit)
        conversations = list(query)
        for conv in conversations:
            conv['_id'] = str(conv['_id'])
            if 'created_at' in conv and isinstance(conv['created_at'], datetime):
                conv['created_at'] = conv['created_at'].isoformat()
            if 'updated_at' in conv and isinstance(conv['updated_at'], datetime):
                conv['updated_at'] = conv['updated_at'].isoformat()
        return conversations

    def archive_conversation(self, conversation_id, user_id, archive_state=True):
        if not self._ensure_connection():
            return False
        try:
            conv_obj_id = ObjectId(conversation_id)
            result = self.conversations.update_one(
                {'_id': conv_obj_id, 'user_id': user_id},
                {'$set': {'archived': bool(archive_state)}}
            )
            return result.matched_count > 0
        except Exception:
            return False

    def delete_conversation(self, conversation_id, user_id):
        if not self._ensure_connection():
            return False
        try:
            conv_obj_id = ObjectId(conversation_id)
            conversation = self.conversations.find_one({'_id': conv_obj_id})
            if not conversation:
                return False
            if str(conversation.get('user_id')) != str(user_id):
                return False

            self.messages.delete_many({'conversation_id': conv_obj_id})
            result = self.conversations.delete_one({'_id': conv_obj_id})
            return result.deleted_count > 0
        except Exception:
            return False

    def get_conversation_with_messages(self, conversation_id, limit=None, skip=0, newest_first=False):
        if not self._ensure_connection():
            return None
        try:
            conv_obj_id = ObjectId(conversation_id)
            conversation = self.conversations.find_one({'_id': conv_obj_id})
            if not conversation:
                return None
            
            conversation['_id'] = str(conversation['_id'])
            conversation['messages'] = self.get_conversation_history(
                conversation_id,
                limit=limit,
                skip=skip,
                newest_first=newest_first
            )
            return conversation
        except Exception:
            return None

    # Métodos para Proyectos
    def create_project(self, title, description, imageUrl, projectUrl, codeSnippet):
        if not self._ensure_connection():
            return None
        project_data = {
            'title': title,
            'description': description,
            'imageUrl': imageUrl,
            'projectUrl': projectUrl,
            'codeSnippet': codeSnippet,
            'created_at': datetime.now(timezone.utc)
        }
        result = self.projects.insert_one(project_data)
        return str(result.inserted_id)

    def get_all_projects(self, limit=None, skip=0, include_code=True):
        if not self._ensure_connection():
            return []
        try:
            projection = None if include_code else {'codeSnippet': 0}
            query = self.projects.find({}, projection).sort('created_at', -1)
            if skip:
                query = query.skip(skip)
            if limit is not None:
                query = query.limit(limit)
            projects = list(query)
            for proj in projects:
                proj['_id'] = str(proj['_id'])
            return projects
        except Exception as e:
            logger.warning("Error al obtener proyectos: %s", e)
            return []

    def get_project_by_id(self, project_id, include_code=True):
        if not self._ensure_connection():
            return None
        try:
            projection = None if include_code else {'codeSnippet': 0}
            proj = self.projects.find_one({'_id': ObjectId(project_id)}, projection)
            if proj:
                proj['_id'] = str(proj['_id'])
            return proj
        except Exception:
            return None

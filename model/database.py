from pymongo import MongoClient
from pymongo.read_preferences import ReadPreference
from pymongo.errors import ServerSelectionTimeoutError
from datetime import datetime
import os
import sys
import subprocess
import re
import urllib.parse
import json
import time
import secrets
import socket
from bson.objectid import ObjectId

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import Config  # Asumo que tienes tu URI de Mongo en config.py


def _debug_log(location, message, data=None, runId="pre-fix", hypothesisId=None):
    """
    Debug NDJSON logger for Cursor debug mode.
    IMPORTANT: never log secrets (passwords, tokens, full URIs with creds).
    """
    try:
        payload = {
            "id": f"log_{int(time.time() * 1000)}_{secrets.token_hex(4)}",
            "timestamp": int(time.time() * 1000),
            "location": location,
            "message": message,
            "data": data or {},
            "runId": runId,
        }
        if hypothesisId:
            payload["hypothesisId"] = hypothesisId
        log_path = os.path.join(ROOT_DIR, ".cursor", "debug.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        # Never fail app due to logging
        pass


def _redact_mongo_uri(uri: str) -> str:
    """Return uri without credentials; keep hosts + db + query keys only."""
    try:
        if not uri:
            return ""
        parsed = urllib.parse.urlparse(uri)
        netloc = parsed.netloc
        if "@" in netloc:
            _, host = netloc.rsplit("@", 1)
        else:
            host = netloc
        # keep query keys only (values can contain sensitive info)
        q = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        keys = sorted(q.keys())
        safe_q = "&".join([f"{k}=*" for k in keys])
        path = parsed.path or ""
        return urllib.parse.urlunparse((parsed.scheme, host, path, "", safe_q, ""))
    except Exception:
        return "<unparseable_mongo_uri>"


def _mongo_uri_query_keys(uri: str):
    try:
        parsed = urllib.parse.urlparse(uri or "")
        q = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        return sorted(q.keys())
    except Exception:
        return []


def _mongo_uri_query_flag(uri: str, key: str):
    try:
        parsed = urllib.parse.urlparse(uri or "")
        q = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        if key not in q:
            return None
        vals = q.get(key) or []
        return vals[-1] if vals else ""
    except Exception:
        return None


def _tcp_reachability(host: str, port: int, timeout_s: float = 3.0):
    try:
        start = time.time()
        with socket.create_connection((host, port), timeout=timeout_s):
            pass
        return {"ok": True, "ms": int((time.time() - start) * 1000)}
    except Exception as e:
        return {"ok": False, "error_type": type(e).__name__, "error": str(e)}


def _extract_seed_hosts(uri: str):
    """Return list of hostnames from mongodb:// seedlist netloc."""
    try:
        parsed = urllib.parse.urlparse(uri or "")
        if parsed.scheme != "mongodb":
            return []
        netloc = parsed.netloc
        if "@" in netloc:
            _, netloc = netloc.rsplit("@", 1)
        hosts = []
        for part in netloc.split(","):
            part = part.strip()
            if not part:
                continue
            host = part.split(":")[0].strip("[]")
            if host:
                hosts.append(host)
        return hosts
    except Exception:
        return []


def _resolve_mongodb_srv_via_nslookup(uri):
    """
    Fallback: resuelve mongodb+srv usando nslookup (subprocess) cuando
    la resolución DNS de Python falla. Construye URI estándar mongodb://
    con hostnames. Requiere ejecutar fix_mongodb_dns.ps1 como admin para
    añadir hostnames al archivo hosts.
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
        db_name = Config.MONGODB_DB_NAME or "admin"
        hosts_str = ",".join(f"{s}:27017" for s in shards[:3])
        direct_uri = f"mongodb://{auth}@{shards[0]}:27017/admin?ssl=true&directConnection=true&authSource=admin"
        try:
            tmp_client = MongoClient(direct_uri, serverSelectionTimeoutMS=10000, connectTimeoutMS=10000)
            rs_status = tmp_client.admin.command("replSetGetStatus")
            tmp_client.close()
            replica_set = rs_status.get("set")
        except Exception:
            replica_set = "atlas-cdvd67-shard-0"
        opts = f"ssl=true&replicaSet={replica_set}&authSource=admin&retryWrites=true&w=majority"
        return f"mongodb://{auth}@{hosts_str}/{db_name}?{opts}"
    except Exception:
        return None


class ChatDatabase:
    """
    Clase para manejar la conexión y operaciones con MongoDB,
    incluyendo la gestión de usuarios, chats y proyectos.
    """
    def __init__(self):
        """Inicializa la conexión a MongoDB y las colecciones"""
        try:
            uri = (Config.MONGODB_URI or "").strip()
            if not uri:
                raise ValueError(
                    "MONGODB_URI no está configurada. En Render: Dashboard → tu servicio → Environment → añade MONGODB_URI con tu URI de Atlas (mongodb+srv://...)."
                )
            if not (uri.startswith('mongodb://') or uri.startswith('mongodb+srv://')):
                raise ValueError(f"URI inválida: debe comenzar con 'mongodb://' o 'mongodb+srv://' (revisa que MONGODB_URI esté bien en Environment de Render).")
            last_error = None
            # #region agent log
            _debug_log(
                location="model/database.py:ChatDatabase.__init__",
                message="Mongo init start",
                data={
                    "uri_redacted": _redact_mongo_uri(uri),
                    "query_keys": _mongo_uri_query_keys(uri),
                    "directConnection": _mongo_uri_query_flag(uri, "directConnection"),
                    "readPreference": _mongo_uri_query_flag(uri, "readPreference"),
                    "replicaSet": _mongo_uri_query_flag(uri, "replicaSet"),
                    "db_name": Config.MONGODB_DB_NAME,
                },
                runId="pre-fix",
                hypothesisId="A",
            )
            # #endregion
            # Opciones para entornos cloud (Render, etc.): timeouts más altos
            client_options = {
                "serverSelectionTimeoutMS": 30000,
                "connectTimeoutMS": 20000,
                "socketTimeoutMS": 20000,
                "retryWrites": True,
                # Evidence-based: primary is unreachable; allow reads from secondaries
                "read_preference": ReadPreference.SECONDARY_PREFERRED,
            }
            # Evidence-based ordering:
            # - mongodb+srv DNS is timing out in this environment, so try nslookup seedlist first
            parsed_uri = urllib.parse.urlparse(uri)
            fallback_uri = _resolve_mongodb_srv_via_nslookup(uri) if parsed_uri.scheme == "mongodb+srv" else None
            attempt_uris = [u for u in [fallback_uri, uri] if u] if parsed_uri.scheme == "mongodb+srv" else [uri]
            for attempt_uri in attempt_uris:
                if not attempt_uri:
                    continue
                try:
                    # #region agent log
                    _debug_log(
                        location="model/database.py:ChatDatabase.__init__",
                        message="Mongo attempt connect",
                        data={
                            "attempt_uri_redacted": _redact_mongo_uri(attempt_uri),
                            "attempt_query_keys": _mongo_uri_query_keys(attempt_uri),
                            "attempt_directConnection": _mongo_uri_query_flag(attempt_uri, "directConnection"),
                            "attempt_readPreference": _mongo_uri_query_flag(attempt_uri, "readPreference"),
                            "attempt_replicaSet": _mongo_uri_query_flag(attempt_uri, "replicaSet"),
                            "used_fallback": attempt_uri != uri,
                        },
                        runId="pre-fix",
                        hypothesisId="C",
                    )
                    # #endregion
                    self.client = MongoClient(
                        attempt_uri,
                        **client_options
                    )
                    self.db = self.client[Config.MONGODB_DB_NAME]
                    self.conversations = self.db['conversations']
                    self.messages = self.db['messages']
                    self.users = self.db['users']
                    self.projects = self.db['projects']
                    try:
                        # Use secondaryPreferred so we can still learn topology without a primary
                        hello = self.client.admin.with_options(read_preference=ReadPreference.SECONDARY_PREFERRED).command("hello")
                    except Exception as _hello_err:
                        hello = {"error": str(_hello_err)}
                    # #region agent log
                    _debug_log(
                        location="model/database.py:ChatDatabase.__init__",
                        message="Mongo connected; hello/topology snapshot",
                        data={
                            "uri_redacted": _redact_mongo_uri(attempt_uri),
                            "read_preference": "SECONDARY_PREFERRED",
                            "hello_keys": sorted(list(hello.keys())) if isinstance(hello, dict) else [],
                            "isWritablePrimary": hello.get("isWritablePrimary") if isinstance(hello, dict) else None,
                            "primary": hello.get("primary") if isinstance(hello, dict) else None,
                            "setName": hello.get("setName") if isinstance(hello, dict) else None,
                            "topology": str(getattr(self.client, "topology_description", "")),
                        },
                        runId="pre-fix",
                        hypothesisId="B",
                    )
                    # #endregion
                    # #region agent log
                    seed_hosts = _extract_seed_hosts(attempt_uri)
                    if seed_hosts:
                        checks = {h: _tcp_reachability(h, 27017, timeout_s=3.0) for h in seed_hosts[:5]}
                    else:
                        checks = {}
                    _debug_log(
                        location="model/database.py:ChatDatabase.__init__",
                        message="Mongo seed host TCP reachability",
                        data={
                            "seed_hosts": seed_hosts,
                            "checks": checks,
                        },
                        runId="pre-fix",
                        hypothesisId="E",
                    )
                    # #endregion
                    self.has_primary = self._has_primary()
                    # #region agent log
                    _debug_log(
                        location="model/database.py:ChatDatabase.__init__",
                        message="Mongo writable/primary check",
                        data={
                            "has_primary": bool(self.has_primary),
                            "topology": str(getattr(self.client, "topology_description", "")),
                        },
                        runId="pre-fix",
                        hypothesisId="B",
                    )
                    # #endregion
                    self._ensure_indexes()
                    if attempt_uri != uri:
                        print("Conexión exitosa a MongoDB (via resolución nslookup)")
                    else:
                        print("Conexión exitosa a MongoDB")
                    return
                except Exception as e:
                    last_error = e
                    # #region agent log
                    _debug_log(
                        location="model/database.py:ChatDatabase.__init__",
                        message="Mongo connect attempt failed",
                        data={
                            "attempt_uri_redacted": _redact_mongo_uri(attempt_uri),
                            "error_type": type(e).__name__,
                            "error": str(e),
                        },
                        runId="pre-fix",
                        hypothesisId="C",
                    )
                    # #endregion
                    if "resolution lifetime" in str(e).lower() or "dns" in str(e).lower():
                        continue
                    break
            raise last_error
        except Exception as e:
            print(f"Error al conectar con MongoDB: {e}")
            self.client = None

    def _has_primary(self) -> bool:
        """Best-effort: detect if a primary is reachable from this client."""
        try:
            td = getattr(self.client, "topology_description", None)
            if not td:
                return False
            sds = None
            if hasattr(td, "server_descriptions"):
                try:
                    sds = td.server_descriptions()
                except TypeError:
                    # some versions expose a property-like access
                    sds = td.server_descriptions
            if isinstance(sds, dict):
                for _addr, sd in sds.items():
                    name = getattr(sd, "server_type_name", None) or ""
                    if name == "RSPrimary":
                        return True
            # fallback to string match
            return "RSPrimary" in str(td)
        except Exception:
            return False

    def _ensure_indexes(self):
        """Crea índices para consultas frecuentes (idempotente)."""
        try:
            if not getattr(self, "has_primary", False):
                # #region agent log
                _debug_log(
                    location="model/database.py:ChatDatabase._ensure_indexes",
                    message="Skipping index creation (no reachable primary)",
                    data={
                        "topology": str(getattr(self.client, "topology_description", "")) if getattr(self, "client", None) else None
                    },
                    runId="pre-fix",
                    hypothesisId="B",
                )
                # #endregion
                return
            self.users.create_index('email')
            self.conversations.create_index([('user_id', 1), ('updated_at', -1)])
            self.messages.create_index([('conversation_id', 1), ('timestamp', 1)])
            self.projects.create_index('created_at')
        except Exception as e:
            print(f"Error al crear índices: {e}")
            # #region agent log
            _debug_log(
                location="model/database.py:ChatDatabase._ensure_indexes",
                message="Mongo index creation failed",
                data={
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "topology": str(getattr(self.client, "topology_description", "")) if getattr(self, "client", None) else None,
                },
                runId="pre-fix",
                hypothesisId="B",
            )
            # #endregion

    def _ensure_connection(self):
        if not self.client:
            print("Error: MongoDB no conectado.")
            return False
        return True

    # --- Métodos de Usuario (sin cambios) ---
    def create_user(self, email, password_hash):
        """
        Crea un nuevo usuario en la base de datos.
        """
        if not self._ensure_connection():
            return None
        user_data = {
            'email': email.lower(),
            'password': password_hash,
            'created_at': datetime.utcnow()
        }
        result = self.users.insert_one(user_data)
        return str(result.inserted_id)

    def get_user_by_email(self, email):
        """Busca un usuario por su email."""
        if not self._ensure_connection():
            return None
        try:
            return self.users.find_one({'email': email.lower()})
        except ServerSelectionTimeoutError as e:
            # #region agent log
            _debug_log(
                location="model/database.py:ChatDatabase.get_user_by_email",
                message="Mongo read failed (get_user_by_email)",
                data={
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "topology": str(getattr(self.client, "topology_description", "")),
                },
                runId="pre-fix",
                hypothesisId="B",
            )
            # #endregion
            return None
        except Exception as e:
            # #region agent log
            _debug_log(
                location="model/database.py:ChatDatabase.get_user_by_email",
                message="Mongo read failed (unexpected)",
                data={
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
                runId="pre-fix",
                hypothesisId="B",
            )
            # #endregion
            return None

    def get_user_by_google_id(self, google_id):
        """Busca un usuario por su ID de Google (OAuth)."""
        if not self._ensure_connection():
            return None
        return self.users.find_one({'google_id': google_id})

    def create_google_user(self, email, google_id, name=None):
        """Crea un usuario vinculado a Google (sin contraseña local)."""
        if not self._ensure_connection():
            return None
        user_data = {
            'email': email.lower(),
            'google_id': google_id,
            'name': name or '',
            'password': None,
            'created_at': datetime.utcnow()
        }
        result = self.users.insert_one(user_data)
        return str(result.inserted_id)

    def link_google_to_user(self, user_id, google_id, name=None):
        """Vincula una cuenta Google a un usuario existente (por email)."""
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

    def get_user_by_id(self, user_id):
        """Busca un usuario por su ID."""
        if not self._ensure_connection():
            return None
        try:
            return self.users.find_one({'_id': ObjectId(user_id)})
        except Exception:
            return None

    # --- Métodos de Conversación (sin cambios) ---
    def create_conversation(self, user_id, title="Nueva Conversación"):
        if not self._ensure_connection():
            return None
        conversation = {
            'user_id': user_id,
            'title': title,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }
        result = self.conversations.insert_one(conversation)
        return str(result.inserted_id)

    def save_message(self, conversation_id, role, content):
        if not self._ensure_connection():
            return False
        message = {
            'conversation_id': conversation_id, # Se espera un ObjectId
            'role': role,
            'content': content,
            'timestamp': datetime.utcnow()
        }
        self.messages.insert_one(message)
        self.conversations.update_one(
            {'_id': conversation_id},
            {'$set': {'updated_at': datetime.utcnow()}}
        )
        return True

    def get_conversation_history(self, conversation_id, limit=None, skip=0, newest_first=False):
        if not self._ensure_connection():
            return []
        try:
            conv_id = ObjectId(conversation_id)
        except Exception:
            return []
        query = self.messages.find(
            {'conversation_id': conv_id}
        ).sort('timestamp', -1 if newest_first else 1)
        if skip:
            query = query.skip(skip)
        if limit is not None:
            query = query.limit(limit)
        messages = list(query)
        
        for msg in messages:
            msg['_id'] = str(msg['_id'])
            msg['conversation_id'] = str(msg['conversation_id'])
        return messages

    def get_user_conversations(self, user_id, limit=None, skip=0):
        if not self._ensure_connection():
            return []
        query = self.conversations.find(
            {'user_id': user_id}
        ).sort('updated_at', -1)
        if skip:
            query = query.skip(skip)
        if limit is not None:
            query = query.limit(limit)
        conversations = list(query)
        
        for conv in conversations:
            conv['_id'] = str(conv['_id'])
        return conversations

    def delete_conversation(self, conversation_id, user_id):
        if not self._ensure_connection():
            return False
        try:
            conv_obj_id = ObjectId(conversation_id)
            conversation = self.conversations.find_one({
                '_id': conv_obj_id,
                'user_id': user_id
            })
            if not conversation:
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

    # --- NUEVOS MÉTODOS PARA PROYECTOS ---

    def create_project(self, title, description, imageUrl, projectUrl, codeSnippet):
        """
        Crea un nuevo proyecto en la base de datos.
        """
        if not self._ensure_connection():
            return None
        project_data = {
            'title': title,
            'description': description,
            'imageUrl': imageUrl,
            'projectUrl': projectUrl,
            'codeSnippet': codeSnippet,
            'created_at': datetime.utcnow()
        }
        result = self.projects.insert_one(project_data)
        return str(result.inserted_id)

    def get_all_projects(self, limit=None, skip=0):
        """
        Obtiene todos los proyectos de la base de datos, ordenados por fecha.
        """
        if not self._ensure_connection():
            return []
        try:
            # Ordena por 'created_at' descendente para mostrar los más nuevos primero
            query = self.projects.find().sort('created_at', -1)
            if skip:
                query = query.skip(skip)
            if limit is not None:
                query = query.limit(limit)
            projects = list(query)
            for proj in projects:
                proj['_id'] = str(proj['_id']) # Convertir ObjectId a string para JSON
            return projects
        except Exception as e:
            print(f"Error al obtener proyectos: {e}")
            # #region agent log
            _debug_log(
                location="model/database.py:ChatDatabase.get_all_projects",
                message="Mongo read failed (get_all_projects)",
                data={
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "topology": str(getattr(self.client, "topology_description", "")) if getattr(self, "client", None) else None,
                },
                runId="pre-fix",
                hypothesisId="B",
            )
            # #endregion
            return []

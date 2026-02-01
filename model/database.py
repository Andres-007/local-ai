from pymongo import MongoClient
from datetime import datetime
import os
import sys
from bson.objectid import ObjectId

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import Config  # Asumo que tienes tu URI de Mongo en config.py

class ChatDatabase:
    """
    Clase para manejar la conexión y operaciones con MongoDB,
    incluyendo la gestión de usuarios, chats y proyectos.
    """
    def __init__(self):
        """Inicializa la conexión a MongoDB y las colecciones"""
        try:
            uri = (Config.MONGODB_URI or "").strip()
            if not uri or not (uri.startswith('mongodb://') or uri.startswith('mongodb+srv://')):
                raise ValueError(f"URI inválida: debe comenzar con 'mongodb://' o 'mongodb+srv://'")
            self.client = MongoClient(
                uri,
                serverSelectionTimeoutMS=15000,
                connectTimeoutMS=10000
            )
            self.db = self.client[Config.MONGODB_DB_NAME]
            self.conversations = self.db['conversations']
            self.messages = self.db['messages']
            self.users = self.db['users']
            
            # --- NUEVA COLECCIÓN ---
            self.projects = self.db['projects'] # Nueva colección para los proyectos del carrusel
            self._ensure_indexes()
            
            print("Conexión exitosa a MongoDB")
        except Exception as e:
            print(f"Error al conectar con MongoDB: {e}")
            self.client = None

    def _ensure_indexes(self):
        """Crea índices para consultas frecuentes (idempotente)."""
        try:
            self.users.create_index('email')
            self.conversations.create_index([('user_id', 1), ('updated_at', -1)])
            self.messages.create_index([('conversation_id', 1), ('timestamp', 1)])
            self.projects.create_index('created_at')
        except Exception as e:
            print(f"Error al crear índices: {e}")

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
        return self.users.find_one({'email': email.lower()})

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
            return []

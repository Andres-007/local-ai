from pymongo import MongoClient
from datetime import datetime
from config import Config  # Asumo que tienes tu URI de Mongo en config.py
from bson.objectid import ObjectId

class ChatDatabase:
    """
    Clase para manejar la conexión y operaciones con MongoDB,
    incluyendo la gestión de usuarios, chats y proyectos.
    """
    def __init__(self):
        """Inicializa la conexión a MongoDB y las colecciones"""
        try:
            self.client = MongoClient(Config.MONGODB_URI)
            self.db = self.client[Config.MONGODB_DB_NAME]
            self.conversations = self.db['conversations']
            self.messages = self.db['messages']
            self.users = self.db['users']
            
            # --- NUEVA COLECCIÓN ---
            self.projects = self.db['projects'] # Nueva colección para los proyectos del carrusel
            
            print("✅ Conexión exitosa a MongoDB")
        except Exception as e:
            print(f"❌ Error al conectar con MongoDB: {e}")
            self.client = None

    # --- Métodos de Usuario (sin cambios) ---
    def create_user(self, email, password_hash):
        """
        Crea un nuevo usuario en la base de datos.
        """
        user_data = {
            'email': email.lower(),
            'password': password_hash,
            'created_at': datetime.utcnow()
        }
        result = self.users.insert_one(user_data)
        return str(result.inserted_id)

    def get_user_by_email(self, email):
        """Busca un usuario por su email."""
        return self.users.find_one({'email': email.lower()})

    def get_user_by_id(self, user_id):
        """Busca un usuario por su ID."""
        try:
            return self.users.find_one({'_id': ObjectId(user_id)})
        except:
            return None

    # --- Métodos de Conversación (sin cambios) ---
    def create_conversation(self, user_id, title="Nueva Conversación"):
        conversation = {
            'user_id': user_id,
            'title': title,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }
        result = self.conversations.insert_one(conversation)
        return str(result.inserted_id)

    def save_message(self, conversation_id, role, content):
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

    def get_conversation_history(self, conversation_id):
        messages = list(self.messages.find(
            {'conversation_id': ObjectId(conversation_id)}
        ).sort('timestamp', 1))
        
        for msg in messages:
            msg['_id'] = str(msg['_id'])
            msg['conversation_id'] = str(msg['conversation_id'])
        return messages

    def get_user_conversations(self, user_id):
        conversations = list(self.conversations.find(
            {'user_id': user_id}
        ).sort('updated_at', -1))
        
        for conv in conversations:
            conv['_id'] = str(conv['_id'])
        return conversations

    def delete_conversation(self, conversation_id, user_id):
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
        except:
            return False

    def get_conversation_with_messages(self, conversation_id):
        try:
            conv_obj_id = ObjectId(conversation_id)
            conversation = self.conversations.find_one({'_id': conv_obj_id})
            if not conversation:
                return None
            
            conversation['_id'] = str(conversation['_id'])
            conversation['messages'] = self.get_conversation_history(conversation_id)
            return conversation
        except:
            return None

    # --- NUEVOS MÉTODOS PARA PROYECTOS ---

    def create_project(self, title, description, imageUrl, projectUrl, codeSnippet):
        """
        Crea un nuevo proyecto en la base de datos.
        """
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

    def get_all_projects(self):
        """
        Obtiene todos los proyectos de la base de datos, ordenados por fecha.
        """
        try:
            # Ordena por 'created_at' descendente para mostrar los más nuevos primero
            projects = list(self.projects.find().sort('created_at', -1))
            for proj in projects:
                proj['_id'] = str(proj['_id']) # Convertir ObjectId a string para JSON
            return projects
        except Exception as e:
            print(f"❌ Error al obtener proyectos: {e}")
            return []

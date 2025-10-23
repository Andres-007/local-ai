from pymongo import MongoClient
from datetime import datetime
from config import Config
from bson.objectid import ObjectId

class ChatDatabase:
    """
    Clase para manejar la conexión y operaciones con MongoDB,
    incluyendo la gestión de usuarios.
    """
    def __init__(self):
        """Inicializa la conexión a MongoDB y las colecciones"""
        try:
            self.client = MongoClient(Config.MONGODB_URI)
            self.db = self.client[Config.MONGODB_DB_NAME]
            self.conversations = self.db['conversations']
            self.messages = self.db['messages']
            self.users = self.db['users']  # Nueva colección para usuarios
            print("✅ Conexión exitosa a MongoDB")
        except Exception as e:
            print(f"❌ Error al conectar con MongoDB: {e}")
            self.client = None

    # --- Métodos de Usuario ---
    def create_user(self, email, password_hash):
        """
        Crea un nuevo usuario en la base de datos.
        Args:
            email (str): Email del usuario.
            password_hash (str): Hash de la contraseña del usuario.
        Returns:
            str: El ID del usuario creado.
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

    # --- Métodos de Conversación (Actualizados) ---
    def create_conversation(self, user_id, title="Nueva Conversación"):
        """Crea una nueva conversación asociada a un user_id."""
        conversation = {
            'user_id': user_id,
            'title': title,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
        }
        result = self.conversations.insert_one(conversation)
        return str(result.inserted_id)

    def save_message(self, conversation_id, role, content):
        """Guarda un mensaje en una conversación."""
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
        """Obtiene el historial de mensajes de una conversación."""
        messages = list(self.messages.find(
            {'conversation_id': ObjectId(conversation_id)}
        ).sort('timestamp', 1))
        
        for msg in messages:
            msg['_id'] = str(msg['_id'])
            msg['conversation_id'] = str(msg['conversation_id'])
        return messages

    def get_user_conversations(self, user_id):
        """Obtiene todas las conversaciones de un usuario."""
        conversations = list(self.conversations.find(
            {'user_id': user_id}
        ).sort('updated_at', -1))
        
        for conv in conversations:
            conv['_id'] = str(conv['_id'])
        return conversations

    def delete_conversation(self, conversation_id, user_id):
        """Elimina una conversación y sus mensajes, verificando el propietario."""
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
        """Obtiene una conversación completa con sus mensajes."""
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

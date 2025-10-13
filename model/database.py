from pymongo import MongoClient
from datetime import datetime
import os
from config import Config

class ChatDatabase:
    """
    Clase para manejar la conexión y operaciones con MongoDB
    """
    def __init__(self):
        """Inicializa la conexión a MongoDB"""
        try:
            self.client = MongoClient(Config.MONGODB_URI)
            self.db = self.client[Config.MONGODB_DB_NAME]
            self.conversations = self.db['conversations']
            self.messages = self.db['messages']
            print("✅ Conexión exitosa a MongoDB")
        except Exception as e:
            print(f"❌ Error al conectar con MongoDB: {e}")
            self.client = None

    def create_conversation(self, user_id, title="Nueva Conversación"):
        """
        Crea una nueva conversación
        
        Args:
            user_id (str): ID del usuario
            title (str): Título de la conversación
            
        Returns:
            str: ID de la conversación creada
        """
        conversation = {
            'user_id': user_id,
            'title': title,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'message_count': 0
        }
        result = self.conversations.insert_one(conversation)
        return str(result.inserted_id)

    def save_message(self, conversation_id, role, content):
        """
        Guarda un mensaje en la conversación
        
        Args:
            conversation_id (str): ID de la conversación
            role (str): 'user' o 'bot'
            content (str): Contenido del mensaje
            
        Returns:
            str: ID del mensaje guardado
        """
        message = {
            'conversation_id': conversation_id,
            'role': role,
            'content': content,
            'timestamp': datetime.utcnow()
        }
        result = self.messages.insert_one(message)
        
        # Actualizar el contador de mensajes y la fecha de actualización
        self.conversations.update_one(
            {'_id': conversation_id},
            {
                '$inc': {'message_count': 1},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )
        
        return str(result.inserted_id)

    def get_conversation_history(self, conversation_id, limit=50):
        """
        Obtiene el historial de mensajes de una conversación
        
        Args:
            conversation_id (str): ID de la conversación
            limit (int): Número máximo de mensajes a obtener
            
        Returns:
            list: Lista de mensajes ordenados por fecha
        """
        messages = list(self.messages.find(
            {'conversation_id': conversation_id}
        ).sort('timestamp', 1).limit(limit))
        
        # Convertir ObjectId a string para JSON
        for msg in messages:
            msg['_id'] = str(msg['_id'])
            msg['timestamp'] = msg['timestamp'].isoformat()
        
        return messages

    def get_user_conversations(self, user_id, limit=20):
        """
        Obtiene todas las conversaciones de un usuario
        
        Args:
            user_id (str): ID del usuario
            limit (int): Número máximo de conversaciones
            
        Returns:
            list: Lista de conversaciones ordenadas por fecha
        """
        conversations = list(self.conversations.find(
            {'user_id': user_id}
        ).sort('updated_at', -1).limit(limit))
        
        # Convertir ObjectId a string para JSON
        for conv in conversations:
            conv['_id'] = str(conv['_id'])
            conv['created_at'] = conv['created_at'].isoformat()
            conv['updated_at'] = conv['updated_at'].isoformat()
        
        return conversations

    def delete_conversation(self, conversation_id):
        """
        Elimina una conversación y todos sus mensajes
        
        Args:
            conversation_id (str): ID de la conversación
            
        Returns:
            bool: True si se eliminó correctamente
        """
        # Eliminar todos los mensajes de la conversación
        self.messages.delete_many({'conversation_id': conversation_id})
        
        # Eliminar la conversación
        result = self.conversations.delete_one({'_id': conversation_id})
        
        return result.deleted_count > 0

    def update_conversation_title(self, conversation_id, new_title):
        """
        Actualiza el título de una conversación
        
        Args:
            conversation_id (str): ID de la conversación
            new_title (str): Nuevo título
            
        Returns:
            bool: True si se actualizó correctamente
        """
        result = self.conversations.update_one(
            {'_id': conversation_id},
            {'$set': {'title': new_title, 'updated_at': datetime.utcnow()}}
        )
        
        return result.modified_count > 0

    def get_conversation_with_messages(self, conversation_id):
        """
        Obtiene una conversación completa con todos sus mensajes
        
        Args:
            conversation_id (str): ID de la conversación
            
        Returns:
            dict: Conversación con sus mensajes
        """
        from bson.objectid import ObjectId
        
        conversation = self.conversations.find_one({'_id': ObjectId(conversation_id)})
        if not conversation:
            return None
        
        conversation['_id'] = str(conversation['_id'])
        conversation['created_at'] = conversation['created_at'].isoformat()
        conversation['updated_at'] = conversation['updated_at'].isoformat()
        
        messages = self.get_conversation_history(conversation_id)
        conversation['messages'] = messages
        
        return conversation

    def search_conversations(self, user_id, query):
        """
        Busca conversaciones por contenido
        
        Args:
            user_id (str): ID del usuario
            query (str): Texto a buscar
            
        Returns:
            list: Conversaciones que coinciden con la búsqueda
        """
        # Buscar en los mensajes
        messages = self.messages.find({
            '$text': {'$search': query}
        })
        
        # Obtener IDs únicos de conversaciones
        conversation_ids = list(set([msg['conversation_id'] for msg in messages]))
        
        # Obtener las conversaciones completas
        conversations = list(self.conversations.find({
            '_id': {'$in': conversation_ids},
            'user_id': user_id
        }).sort('updated_at', -1))
        
        # Convertir ObjectId a string
        for conv in conversations:
            conv['_id'] = str(conv['_id'])
            conv['created_at'] = conv['created_at'].isoformat()
            conv['updated_at'] = conv['updated_at'].isoformat()
        
        return conversations
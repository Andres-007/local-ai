import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """
    Clase de configuración para gestionar las variables de entorno
    """
    # API de Gemini
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # MongoDB
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb+srv://laia:mongo2025@dataforai.iqsajt7.mongodb.net/?retryWrites=true&w=majority&appName=DataforAI')
    MONGODB_DB_NAME = os.getenv('aidb', 'datagen')
    
    # Verificación de variables
    if not GEMINI_API_KEY:
        print("\n" + "="*50)
        print("⚠️ ALERTA: GEMINI_API_KEY no encontrada")
        print("Añade en tu archivo .env:")
        print("GEMINI_API_KEY=tu_clave_aqui")
        print("="*50 + "\n")
    
    if not os.getenv('MONGODB_URI'):
        print("\n" + "="*50)
        print("⚠️ ALERTA: MONGODB_URI no encontrada")
        print("Añade en tu archivo .env:")
        print("MONGODB_URI=mongodb://localhost:27017/")
        print("O usa MongoDB Atlas (gratis):")
        print("MONGODB_URI=mongodb+srv://usuario:password@cluster.mongodb.net/")
        print("="*50 + "\n")
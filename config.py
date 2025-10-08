import os
from dotenv import load_dotenv

# Carga las variables de entorno desde un archivo .env
load_dotenv()

class Config:
    """
    Clase de configuración para almacenar la clave de la API de Gemini.
    Es una buena práctica gestionar las claves secretas a través de variables de entorno.
    """
    # Obtiene la clave de la API de Google Gemini desde las variables de entorno.
    # Si no se encuentra, se le asigna un valor None.
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

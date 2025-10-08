import os
from dotenv import load_dotenv

# **FIX**: Añadido manejo de errores para saber si el .env no se carga.
try:
    # Carga las variables de entorno desde un archivo .env
    load_dotenv()
    print("Archivo .env cargado correctamente.")
except Exception as e:
    print(f"Error al cargar el archivo .env: {e}")


class Config:
    """
    Clase de configuración para gestionar las variables de entorno de la aplicación.
    """
    # Obtiene la clave de API de Gemini de las variables de entorno
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # **FIX**: Añadida una verificación para confirmar que la clave fue encontrada.
    if not GEMINI_API_KEY:
        print("\n" + "="*50)
        print("ALERTA: La variable de entorno GEMINI_API_KEY no fue encontrada.")
        print("Asegúrate de tener un archivo .env en la raíz del proyecto con el formato:")
        print("GEMINI_API_KEY=tu_clave_aqui")
        print("="*50 + "\n")


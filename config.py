import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env desde la raíz del proyecto (donde está app.py)
_root = Path(__file__).resolve().parent
load_dotenv(_root / '.env')

logger = logging.getLogger(__name__)

class Config:
	"""
	Clase de configuración para gestionar las variables de entorno
	"""
	# API de Gemini
	GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
	
	# MongoDB - URI válida por defecto para desarrollo local
	MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
	
	MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'webdevai')
	
	# Verificación de variables
	if not GEMINI_API_KEY:
		logger.warning("GEMINI_API_KEY no encontrada. Añade GEMINI_API_KEY=tu_clave_aqui en tu archivo .env.")

	if not MONGODB_URI:
		logger.warning("MONGODB_URI no encontrada. Usa mongodb://localhost:PORT/ o una URI de Atlas mongodb+srv://...")

	# Nueva verificación para el nombre de la BD
	if not MONGODB_DB_NAME:
		logger.warning("MONGODB_DB_NAME no encontrada. Usando valor por defecto: '%s'.", MONGODB_DB_NAME)

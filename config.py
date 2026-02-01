import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env desde la raíz del proyecto (donde está app.py)
_root = Path(__file__).resolve().parent
load_dotenv(_root / '.env')

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
		print("\n" + "="*50)
		print("⚠️ ALERTA: GEMINI_API_KEY no encontrada")
		print("Añade en tu archivo .env:")
		print("GEMINI_API_KEY=tu_clave_aqui")
		print("="*50 + "\n")
	
	if not MONGODB_URI:
		print("\n" + "="*50)
		print("MONGODB_URI no encontrada")
		print("Añade en tu archivo .env:")
		print("MONGODB_URI=mongodb://localhost:PORT/")
		print("O usa MongoDB Atlas:")
		print("MONGODB_URI=mongodb+srv://usuario:password@cluster.mongodb.net/")
		print("="*50 + "\n")
	
	# Nueva verificación para el nombre de la BD
	if not MONGODB_DB_NAME:
		print("\n" + "="*50)
		print("MONGODB_DB_NAME no encontrada")
		print(f"Usando valor por defecto: '{MONGODB_DB_NAME}'")
		print("Si es incorrecto, añade en tu archivo .env:")
		print("MONGODB_DB_NAME=tu_base_de_datos")
		print("="*50 + "\n")

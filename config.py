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
	MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
	
	# --- LÍNEA CORREGIDA ---
	# Ahora busca la variable de entorno 'MONGODB_DB_NAME'
	# Si no la encuentra, usa 'datagen' como valor por defecto.
	MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'datagen')
	
	# Verificación de variables
	if not GEMINI_API_KEY:
		print("\n" + "="*50)
		print("⚠️ ALERTA: GEMINI_API_KEY no encontrada")
		print("Añade en tu archivo .env:")
		print("GEMINI_API_KEY=tu_clave_aqui")
		print("="*50 + "\n")
	
	if not MONGODB_URI:
		print("\n" + "="*50)
		print("⚠️ ALERTA: MONGODB_URI no encontrada")
		print("Añade en tu archivo .env:")
		print("MONGODB_URI=mongodb://localhost:27017/")
		print("O usa MongoDB Atlas (gratis):")
		print("MONGODB_URI=mongodb+srv://usuario:password@cluster.mongodb.net/")
		print("="*50 + "\n")
	
	# Nueva verificación para el nombre de la BD
	if not MONGODB_DB_NAME:
		print("\n" + "="*50)
		print("⚠️ ALERTA: MONGODB_DB_NAME no encontrada")
		print(f"Usando valor por defecto: '{MONGODB_DB_NAME}'")
		print("Si es incorrecto, añade en tu archivo .env:")
		print("MONGODB_DB_NAME=tu_base_de_datos")
		print("="*50 + "\n")
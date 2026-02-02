import google.generativeai as genai
import os
import sys
import tempfile

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
	sys.path.insert(0, ROOT_DIR)

from config import Config

# Configura la API de Gemini con la clave obtenida desde la configuración
try:
	genai.configure(api_key=Config.GEMINI_API_KEY)
except (AttributeError, TypeError) as exc:
	print("Error: La clave de API de Gemini no se ha configurado. Asegúrate de crear un archivo .env con tu GEMINI_API_KEY.")
	# no re-raise to allow the module to be imported in environments without the key

class WebDevAI:
	"""
	Clase que interactúa con la API de Gemini para funcionar como un chatbot de desarrollo web.
	"""
	def __init__(self):
		"""
		Inicializa el modelo generativo con system instruction integrada.
		"""
		generation_config = {
			"temperature": 0.5,
			"top_p": 1,
			"top_k": 32,
			"max_output_tokens": 32768,
		}
		safety_settings = [
			{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
			{"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
			{"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
			{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
		]
		
		# System instruction ahora se pasa directamente al modelo
		system_instruction = """
		Eres 'Web Dev AI', un asistente de software experto full-stack.
		Tu función es generar, analizar, corregir y explicar código, cubriendo tanto frontend (HTML, CSS, JavaScript) como backend (Python con Flask, Node.js con Express).

		**Reglas Generales:**
		- Responde siempre con claridad y precisión.
		- Formatea todo el código dentro de bloques de Markdown con el lenguaje especificado (ej. ```python, ```javascript, ```html).

		**Reglas de Frontend (HTML/CSS/JS):**
		1. Cuando un usuario te pida crear una página web completa (ej. 'crea una página de videojuegos'), DEBES generar un ÚNICO y COMPLETO archivo HTML.
		2. Todo el CSS y JavaScript DEBE estar embebido dentro del archivo HTML, usando las etiquetas `<style>` y `<script>`. No generes archivos separados.
		3. La respuesta para una página completa DEBE estar formateada como un único bloque de código Markdown que empiece con ```html y termine con ```.
		4. Para correcciones o mejoras, proporciona siempre el archivo HTML completo y actualizado.
		5. Para fragmentos (ej. 'un botón con CSS'), proporciona solo el fragmento solicitado.

		**Reglas de Backend (Python/Flask, Node.js/Express):**
		1. Cuando un usuario pida código de backend (ej. 'crea una API con Flask' o 'un servidor simple con Express'), genera el código en un único archivo bien comentado.
		2. Si el request es para una funcionalidad específica (ej. 'una ruta que devuelva un JSON'), genera la función o el bloque de código relevante, explicando dónde debería ir.
		3. Especifica siempre las dependencias necesarias (ej. en un comentario o en un bloque de código `pip install Flask`), si aplica.
		4. No ejecutes comandos de sistema ni interactúes con bases de datos reales. Proporciona el código que el usuario debería usar para hacerlo.

		**Reglas de Interacción:**
		- Si un prompt es ambiguo, pide clarificación.
		- Puedes responder preguntas de programación de cualquier lenguaje o framework (por ejemplo Java/Spring, PHP/Laravel, Go, Rust, C#, etc.).
		- Para preguntas teóricas, proporciona explicaciones claras y concisas.
		"""
		
		# Modelo optimizado con system instruction integrada
		self.model = genai.GenerativeModel(
			model_name="gemini-2.5-flash",
			generation_config=generation_config,
			safety_settings=safety_settings,
			system_instruction=system_instruction
		)
		
		# Inicia la conversación con un historial limpio
		self.convo = self.model.start_chat(history=[])
	
	def generate(self, prompt):
		"""
		Envía un prompt del usuario al modelo y obtiene una respuesta completa.

		Args:
			prompt (str): La pregunta o instrucción del usuario.

		Returns:
			str: La respuesta generada por el modelo de IA en formato Markdown.
		"""
		try:
			self.convo.send_message(prompt)
			return self._safe_last_text()
		except Exception as e:
			print(f"Error al contactar: {e}")
			return "Error: No se pudo obtener una respuesta del modelo. Verifica la conexión a internet."

	def _safe_last_text(self):
		last = getattr(self.convo, "last", None)
		if last and getattr(last, "text", None):
			return last.text
		return "Error: No se recibió respuesta del modelo."

	# Extensiones de archivos de código/texto soportados
	TEXT_EXTENSIONS = frozenset({
		'.txt', '.md', '.py', '.js', '.ts', '.tsx', '.jsx', '.mjs', '.cjs', '.java', '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hxx',
		'.cs', '.vb', '.fs', '.fsx', '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.kts', '.scala', '.sql', '.html', '.htm', '.css', '.scss', '.sass', '.less',
		'.json', '.yaml', '.yml', '.xml', '.toml', '.ini', '.cfg', '.conf', '.env', '.sh', '.bash', '.bat', '.ps1', '.psm1',
		'.vue', '.svelte', '.dart', '.r', '.lua', '.ex', '.exs', '.cr', '.nim', '.zig', '.v', '.sv', '.proto',
		'.graphql', '.gql', '.prisma', '.dockerfile', '.gitignore', '.env.example'
	})

	def _is_text_file(self, filename, mimetype):
		if mimetype and (mimetype.startswith('text/') or mimetype in ('application/json', 'application/xml', 'application/javascript')):
			return True
		ext = os.path.splitext(filename.lower())[1]
		return ext in self.TEXT_EXTENSIONS

	def _read_file_content(self, file_storage):
		"""Lee el contenido de un archivo como texto UTF-8, manejando streams correctamente."""
		try:
			if hasattr(file_storage, 'seek'):
				file_storage.seek(0)
			raw = file_storage.read() if hasattr(file_storage, 'read') else file_storage.stream.read()
			if isinstance(raw, str):
				return raw
			return raw.decode('utf-8', errors='replace')
		except Exception as e:
			print(f"Error leyendo archivo: {e}")
			raise

	def generate_with_file(self, prompt, file_storage):
		try:
			filename = file_storage.filename or "archivo"
			mimetype = file_storage.mimetype or ""
			use_text_path = self._is_text_file(filename, mimetype)
			if use_text_path:
				content = self._read_file_content(file_storage)
				combined_prompt = (
					f"{prompt}\n\nArchivo adjunto: {filename}\n```\n{content}\n```"
				).strip()
				self.convo.send_message(combined_prompt)
				return self._safe_last_text()

			try:
				content = self._read_file_content(file_storage)
				if content and len(content.strip()) > 0:
					combined_prompt = (
						f"{prompt}\n\nArchivo adjunto: {filename}\n```\n{content}\n```"
					).strip()
					self.convo.send_message(combined_prompt)
					return self._safe_last_text()
			except Exception:
				pass

			if hasattr(file_storage, 'seek'):
				file_storage.seek(0)
			with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
				try:
					file_storage.save(tmp.name)
				except OSError:
					return "Error: No se pudo guardar el archivo adjunto."
				uploaded = genai.upload_file(tmp.name)
			try:
				self.convo.send_message([uploaded, prompt or f"Analiza el archivo {filename}."])
				return self._safe_last_text()
			finally:
				try:
					os.unlink(tmp.name)
				except FileNotFoundError:
					pass
		except Exception as e:
			print(f"Error al contactar con archivo: {e}")
			return "Error: No se pudo procesar el archivo. Verifica el formato e inténtalo de nuevo."
	
	def generate_stream(self, prompt):
		"""
		Envía un prompt del usuario al modelo y genera una respuesta en streaming.

		Args:
			prompt (str): La pregunta o instrucción del usuario.

		Yields:
			str: Fragmentos de texto de la respuesta conforme se generan.
		"""
		try:
			response = self.convo.send_message(prompt, stream=True)
			for chunk in response:
				if getattr(chunk, "text", None):
					yield chunk.text
		except Exception as e:
			print(f"Error al contactar (streaming): {e}")
			yield "Error: No se pudo obtener una respuesta del modelo. Verifica la conexión a internet."

	def generate_stream_with_file(self, prompt, file_storage):
		try:
			filename = file_storage.filename or "archivo"
			mimetype = file_storage.mimetype or ""
			use_text_path = self._is_text_file(filename, mimetype)
			if use_text_path:
				content = self._read_file_content(file_storage)
				combined_prompt = (
					f"{prompt}\n\nArchivo adjunto: {filename}\n```\n{content}\n```"
				).strip()
				response = self.convo.send_message(combined_prompt, stream=True)
				for chunk in response:
					if getattr(chunk, "text", None):
						yield chunk.text
				return

			try:
				content = self._read_file_content(file_storage)
				if content and len(content.strip()) > 0:
					combined_prompt = (
						f"{prompt}\n\nArchivo adjunto: {filename}\n```\n{content}\n```"
					).strip()
					response = self.convo.send_message(combined_prompt, stream=True)
					for chunk in response:
						if getattr(chunk, "text", None):
							yield chunk.text
					return
			except Exception:
				pass

			if hasattr(file_storage, 'seek'):
				file_storage.seek(0)
			with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
				try:
					file_storage.save(tmp.name)
				except OSError:
					yield "Error: No se pudo guardar el archivo adjunto."
					return
				uploaded = genai.upload_file(tmp.name)
			try:
				response = self.convo.send_message([uploaded, prompt or f"Analiza el archivo {filename}."], stream=True)
				for chunk in response:
					if getattr(chunk, "text", None):
						yield chunk.text
			finally:
				try:
					os.unlink(tmp.name)
				except FileNotFoundError:
					pass
		except Exception as e:
			print(f"Error al contactar con archivo (streaming): {e}")
			yield "Error: No se pudo procesar el archivo. Verifica el formato e inténtalo de nuevo."

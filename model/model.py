import google.generativeai as genai
import os
import sys
import tempfile
import io

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
		'.txt', '.md', '.mdx', '.markdown', '.py', '.pyw', '.pyi', '.js', '.ts', '.tsx', '.jsx', '.mjs', '.cjs',
		'.java', '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hxx', '.cs', '.vb', '.fs', '.fsx', '.go', '.rs',
		'.php', '.rb', '.erb', '.swift', '.kt', '.kts', '.scala', '.sql', '.html', '.htm', '.xhtml',
		'.css', '.scss', '.sass', '.less', '.json', '.yaml', '.yml', '.xml', '.toml', '.ini', '.cfg', '.conf',
		'.env', '.sh', '.bash', '.zsh', '.bat', '.cmd', '.ps1', '.psm1', '.psd1',
		'.vue', '.svelte', '.dart', '.r', '.lua', '.ex', '.exs', '.cr', '.nim', '.zig', '.v', '.sv', '.proto',
		'.graphql', '.gql', '.prisma', '.dockerfile', '.gitignore', '.env.example', '.csv', '.log', '.rst',
		'.tex', '.latex', '.pl', '.pm', '.t', '.hs', '.lhs', '.ml', '.mli', '.fsi', '.clj', '.cljs', '.edn',
		'.coffee', '.litcoffee', '.elm', '.purs', '.adb', '.ads', '.vhd', '.vhdl',
	})

	# Tamaño máximo (bytes) para incluir archivo completo como texto; el resto se trunca
	MAX_TEXT_FILE_BYTES = 1 * 1024 * 1024  # 1 MB

	# MIME types típicos de código y texto (además de text/*)
	TEXT_MIMETYPES = frozenset({
		'application/json', 'application/xml', 'application/javascript', 'application/typescript',
		'application/x-python', 'text/x-python', 'text/x-python3',
		'text/x-javascript', 'text/x-typescript', 'text/x-c', 'text/x-c++',
		'text/x-java', 'text/x-php', 'text/x-ruby', 'text/x-go', 'text/x-rust',
		'text/x-sh', 'text/x-shellscript', 'application/x-sh', 'application/x-bat',
		'application/x-yaml', 'application/yaml', 'text/yaml',
		'text/xml', 'text/csv', 'text/plain', 'text/markdown',
	})

	def _is_text_file(self, filename, mimetype):
		if mimetype:
			m = mimetype.split(';')[0].strip().lower()
			if m.startswith('text/') or m in self.TEXT_MIMETYPES:
				return True
		ext = os.path.splitext(filename.lower())[1]
		return ext in self.TEXT_EXTENSIONS

	def _lang_for_filename(self, filename):
		"""Devuelve el nombre del lenguaje para bloques de código (Markdown)."""
		ext = os.path.splitext(filename.lower())[1]
		lang_map = {
			'.py': 'python', '.pyw': 'python', '.pyi': 'python',
			'.js': 'javascript', '.mjs': 'javascript', '.cjs': 'javascript',
			'.ts': 'typescript', '.tsx': 'typescript', '.jsx': 'javascript',
			'.html': 'html', '.htm': 'html', '.xhtml': 'html',
			'.css': 'css', '.scss': 'scss', '.sass': 'sass', '.less': 'less',
			'.json': 'json', '.yaml': 'yaml', '.yml': 'yaml', '.xml': 'xml',
			'.md': 'markdown', '.mdx': 'markdown', '.markdown': 'markdown',
			'.java': 'java', '.c': 'c', '.cpp': 'cpp', '.h': 'c', '.hpp': 'cpp',
			'.cs': 'csharp', '.go': 'go', '.rs': 'rust', '.php': 'php', '.rb': 'ruby',
			'.swift': 'swift', '.kt': 'kotlin', '.kts': 'kotlin', '.scala': 'scala',
			'.sql': 'sql', '.sh': 'bash', '.bash': 'bash', '.ps1': 'powershell',
			'.vue': 'vue', '.svelte': 'svelte', '.dart': 'dart', '.lua': 'lua',
			'.r': 'r', '.graphql': 'graphql', '.gql': 'graphql', '.prisma': 'prisma',
			'.dockerfile': 'dockerfile', '.proto': 'protobuf', '.toml': 'toml',
			'.log': 'log', '.txt': 'text', '.csv': 'csv', '.rst': 'rst', '.tex': 'latex',
		}
		return lang_map.get(ext, '')

	def _is_pdf(self, filename, mimetype):
		if mimetype and mimetype == 'application/pdf':
			return True
		return os.path.splitext(filename.lower())[1] == '.pdf'

	def _read_file_content(self, file_storage):
		"""Lee el contenido de un archivo como texto, probando UTF-8, latin-1 y cp1252. Trunca si supera MAX_TEXT_FILE_BYTES."""
		try:
			if hasattr(file_storage, 'seek'):
				try:
					file_storage.seek(0)
				except (OSError, AttributeError):
					pass
			stream = getattr(file_storage, 'stream', file_storage)
			raw = stream.read() if hasattr(stream, 'read') else file_storage.read()
			if raw is None:
				raw = b""
			if isinstance(raw, str):
				raw = raw.encode('utf-8', errors='replace')
			if not isinstance(raw, (bytes, bytearray)):
				raw = bytes(raw) if raw else b""
			if len(raw) > self.MAX_TEXT_FILE_BYTES:
				raw = raw[:self.MAX_TEXT_FILE_BYTES]
				truncated_note = f"\n\n[... archivo truncado (máx. {self.MAX_TEXT_FILE_BYTES // 1024} KB) ...]"
			else:
				truncated_note = ""
			for encoding in ('utf-8', 'latin-1', 'cp1252', 'utf-8-sig'):
				try:
					return raw.decode(encoding) + truncated_note
				except (UnicodeDecodeError, LookupError):
					continue
			return raw.decode('utf-8', errors='replace') + truncated_note
		except Exception as e:
			print(f"Error leyendo archivo: {e}")
			raise

	def _read_pdf_content(self, file_storage):
		"""Extrae el texto de un PDF usando pypdf (o PyPDF2 como fallback)."""
		try:
			try:
				from pypdf import PdfReader
			except ImportError:
				from PyPDF2 import PdfReader
		except ImportError as e:
			print(f"Error: instala pypdf con 'pip install pypdf': {e}")
			raise
		try:
			if hasattr(file_storage, 'seek'):
				file_storage.seek(0)
			raw = file_storage.read() if hasattr(file_storage, 'read') else file_storage.stream.read()
			if not raw:
				return ""
			if isinstance(raw, str):
				raw = raw.encode('utf-8', errors='replace')
			if hasattr(file_storage, 'seek'):
				file_storage.seek(0)
			reader = PdfReader(io.BytesIO(raw))
			parts = []
			for page in reader.pages:
				try:
					text = page.extract_text()
					if text and isinstance(text, str):
						parts.append(text.strip())
				except Exception:
					pass
			return "\n\n".join(parts) if parts else ""
		except Exception as e:
			print(f"Error leyendo PDF: {e}")
			raise

	def _read_file_storage_once(self, file_storage):
		"""Lee el stream del archivo UNA sola vez y devuelve bytes. Evita 'I/O operation on closed file'."""
		try:
			if hasattr(file_storage, 'seek'):
				try:
					file_storage.seek(0)
				except (OSError, AttributeError):
					pass
			stream = getattr(file_storage, 'stream', file_storage)
			raw = stream.read() if hasattr(stream, 'read') else file_storage.read()
			if raw is None:
				return b""
			if isinstance(raw, str):
				raw = raw.encode('utf-8', errors='replace')
			return bytes(raw) if not isinstance(raw, bytes) else raw
		except Exception as e:
			print(f"Error leyendo archivo adjunto (una vez): {e}")
			return None

	def _wrap_bytes_as_file_like(self, raw_bytes, filename, mimetype):
		"""Envuelve bytes en un objeto tipo file (read/seek/filename/mimetype) para reutilizar sin cerrar el stream."""
		class _FileLike:
			__slots__ = ('_io', 'filename', 'mimetype')
			def __init__(self, raw, fn, mt):
				self._io = io.BytesIO(raw)
				self.filename = fn
				self.mimetype = mt or ""
			def read(self):
				return self._io.read()
			def seek(self, pos=0):
				return self._io.seek(pos)
			@property
			def stream(self):
				return self._io
		return _FileLike(raw_bytes, filename, mimetype)

	def _get_readable_content(self, file_storage, filename, mimetype):
		"""Obtiene el contenido como texto si el archivo es legible (texto, código o PDF)."""
		try:
			if self._is_pdf(filename, mimetype):
				text = self._read_pdf_content(file_storage)
				return text if text and text.strip() else None
			if self._is_text_file(filename, mimetype):
				return self._read_file_content(file_storage)
			return self._read_file_content(file_storage)
		except Exception as e:
			print(f"Error en _get_readable_content ({filename}): {e}")
			return None

	def generate_with_file(self, prompt, file_storage=None, file_bytes=None, filename=None, mimetype=None):
		try:
			if file_bytes is not None:
				raw = file_bytes if isinstance(file_bytes, bytes) else bytes(file_bytes)
				filename = filename or "archivo"
				mimetype = mimetype or ""
			else:
				if file_storage is None:
					return "Error: No se proporcionó archivo."
				filename = file_storage.filename or "archivo"
				mimetype = file_storage.mimetype or ""
				raw = self._read_file_storage_once(file_storage)
				if raw is None:
					return "Error: No se pudo leer el archivo adjunto (stream cerrado o no disponible)."
			file_like = self._wrap_bytes_as_file_like(raw, filename, mimetype)
			ext = os.path.splitext(filename.lower())[1]
			content = self._get_readable_content(file_like, filename, mimetype)

			if content is not None and len(content.strip()) > 0:
				lang = self._lang_for_filename(filename)
				code_block = f"```{lang}\n{content}\n```" if lang else f"```\n{content}\n```"
				combined_prompt = f"{prompt}\n\nArchivo adjunto: {filename}\n{code_block}".strip()
				self.convo.send_message(combined_prompt)
				return self._safe_last_text()

			if ext == ".pdf":
				return (
					"No se pudo extraer texto de este PDF. Puede estar escaneado (solo imágenes), "
					"protegido o dañado. Prueba con un PDF con texto seleccionable o con otro archivo."
				)

			if ext in self.TEXT_EXTENSIONS:
				try:
					content2 = self._read_file_content(file_like)
					if not content2 or not content2.strip():
						return "El archivo está vacío o no se pudo leer su contenido."
					lang = self._lang_for_filename(filename)
					code_block = f"```{lang}\n{content2}\n```" if lang else f"```\n{content2}\n```"
					combined_prompt = f"{prompt}\n\nArchivo adjunto: {filename}\n{code_block}".strip()
					self.convo.send_message(combined_prompt)
					return self._safe_last_text()
				except Exception as e2:
					print(f"Error leyendo archivo de código ({filename}): {e2}")
					return f"No se pudo leer el archivo {filename}. Comprueba que no esté dañado. Detalle: {e2}"

			tmp_path = None
			with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
				try:
					tmp.write(raw)
					tmp.flush()
					tmp.close()
					tmp_path = tmp.name
				except OSError:
					return "Error: No se pudo guardar el archivo adjunto."
			try:
				uploaded = genai.upload_file(tmp_path)
				self.convo.send_message([uploaded, prompt or f"Analiza el archivo {filename}."])
				return self._safe_last_text()
			finally:
				if tmp_path:
					try:
						os.unlink(tmp_path)
					except FileNotFoundError:
						pass
		except Exception as e:
			print(f"Error al contactar con archivo: {e}")
			err_msg = str(e).strip() if e else ""
			if "pypdf" in err_msg.lower() or "PyPDF" in err_msg or "pdf" in err_msg.lower():
				return "Error al leer el PDF. Asegúrate de tener instalado: pip install pypdf"
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

	def generate_stream_with_file(self, prompt, file_storage=None, file_bytes=None, filename=None, mimetype=None):
		try:
			if file_bytes is not None:
				raw = file_bytes if isinstance(file_bytes, bytes) else bytes(file_bytes)
				filename = filename or "archivo"
				mimetype = mimetype or ""
			else:
				if file_storage is None:
					yield "Error: No se proporcionó archivo."
					return
				filename = file_storage.filename or "archivo"
				mimetype = file_storage.mimetype or ""
				raw = self._read_file_storage_once(file_storage)
				if raw is None:
					yield "Error: No se pudo leer el archivo adjunto (stream cerrado o no disponible)."
					return
			file_like = self._wrap_bytes_as_file_like(raw, filename, mimetype)
			ext = os.path.splitext(filename.lower())[1]
			content = self._get_readable_content(file_like, filename, mimetype)

			if content is not None and len(content.strip()) > 0:
				lang = self._lang_for_filename(filename)
				code_block = f"```{lang}\n{content}\n```" if lang else f"```\n{content}\n```"
				combined_prompt = f"{prompt}\n\nArchivo adjunto: {filename}\n{code_block}".strip()
				response = self.convo.send_message(combined_prompt, stream=True)
				for chunk in response:
					if getattr(chunk, "text", None):
						yield chunk.text
				return

			if ext == ".pdf":
				yield (
					"No se pudo extraer texto de este PDF. Puede estar escaneado (solo imágenes), "
					"protegido o dañado. Prueba con un PDF con texto seleccionable o con otro archivo."
				)
				return

			if ext in self.TEXT_EXTENSIONS:
				try:
					content2 = self._read_file_content(file_like)
					if not content2 or not content2.strip():
						yield "El archivo está vacío o no se pudo leer su contenido."
						return
					lang = self._lang_for_filename(filename)
					code_block = f"```{lang}\n{content2}\n```" if lang else f"```\n{content2}\n```"
					combined_prompt = f"{prompt}\n\nArchivo adjunto: {filename}\n{code_block}".strip()
					response = self.convo.send_message(combined_prompt, stream=True)
					for chunk in response:
						if getattr(chunk, "text", None):
							yield chunk.text
					return
				except Exception as e2:
					print(f"Error leyendo archivo de código ({filename}): {e2}")
					yield f"No se pudo leer el archivo {filename}. Comprueba que no esté dañado. Detalle: {e2}"
					return

			tmp_path = None
			with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
				try:
					tmp.write(raw)
					tmp.flush()
					tmp.close()
					tmp_path = tmp.name
				except OSError:
					yield "Error: No se pudo guardar el archivo adjunto."
					return
			try:
				uploaded = genai.upload_file(tmp_path)
				response = self.convo.send_message([uploaded, prompt or f"Analiza el archivo {filename}."], stream=True)
				for chunk in response:
					if getattr(chunk, "text", None):
						yield chunk.text
			finally:
				if tmp_path:
					try:
						os.unlink(tmp_path)
					except FileNotFoundError:
						pass
		except Exception as e:
			print(f"Error al contactar con archivo (streaming): {e}")
			err_msg = str(e).strip() if e else ""
			if "pypdf" in err_msg.lower() or "PyPDF" in err_msg or "pdf" in err_msg.lower():
				yield "Error al leer el PDF. Asegúrate de tener instalado: pip install pypdf"
			else:
				yield "Error: No se pudo procesar el archivo. Verifica el formato e inténtalo de nuevo."

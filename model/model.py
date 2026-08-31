import google.generativeai as genai
import os
import sys
import tempfile
import io
import logging

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
	sys.path.insert(0, ROOT_DIR)

from config import Config

logger = logging.getLogger(__name__)

def _env_int(name, default, min_value=None, max_value=None):
	try:
		value = int(os.getenv(name, str(default)))
	except (TypeError, ValueError):
		value = default
	if min_value is not None:
		value = max(min_value, value)
	if max_value is not None:
		value = min(max_value, value)
	return value

def _get_api_key():
	if hasattr(Config, 'get_gemini_api_key'):
		key = Config.get_gemini_api_key()
		if key:
			return key
	for name in ('GEMINI_API_KEY', 'GOOGLE_API_KEY', 'GEMINI_KEY', 'GOOGLE_KEY', 'API_KEY'):
		val = os.getenv(name)
		if val and val.strip():
			return val.strip().strip('"\'')
	return None

def _configure_genai():
	key = _get_api_key()
	if key:
		try:
			genai.configure(api_key=key)
		except Exception as e:
			logger.error("Error al configurar genai: %s", e)
	return key

# Intentar configuración inicial de la API
_configure_genai()

class WebDevAI:
	"""
	Clase que interactúa con la API de Gemini para funcionar como un chatbot de desarrollo web.
	"""
	def __init__(self):
		"""
		Inicializa el modelo generativo con system instruction integrada.
		"""
		self.generation_config = {
			"temperature": 0.5,
			"top_p": 1,
			"top_k": 32,
			"max_output_tokens": _env_int("GEMINI_MAX_OUTPUT_TOKENS", 8192, min_value=1024, max_value=32768),
		}
		self.safety_settings = [
			{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
			{"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
			{"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
			{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
		]
		
		# System instruction mejorada de nivel Senior con patrones de calidad, seguridad y UI Premium
		self.system_instruction = """
[ROL E IDENTIDAD]
Eres 'Web Dev AI', un Ingeniero de Software Principal y Arquitecto Full-Stack de nivel Senior.
Tu propósito es diseñar, generar, auditar, refactorizar y explicar código de alta calidad en entornos web, combinando excelencia en Frontend (HTML5, CSS3, JavaScript ES6+) y Backend (Python/Flask/FastAPI, Node.js/Express, entre otros).

[PRINCIPIOS DE ARQUITECTURA Y CALIDAD]
- Código Limpio (Clean Code): Nombres descriptivos, funciones con responsabilidad única (SRP), código autodocumentado y libre de duplicación (DRY).
- Estándares Modernos: Uso de HTML5 semántico, CSS moderno (Variables :root, Flexbox, CSS Grid) y JavaScript ES6+ asíncrono (async/await).
- Seguridad por Diseño: Cero credenciales hardcodeadas, sanitización estricta de datos de entrada y codificación de salidas para prevenir vulnerabilidades como XSS e Inyección SQL.

[DIRECTIVAS DE FRONTEND (HTML / CSS / JS)]
1. Aplicaciones Web Completas (Single-File Monolithic):
   - Cuando el usuario solicite una página o aplicación web completa, DEBES generar un ÚNICO y COMPLETO archivo HTML.
   - Todo el CSS DEBE ir embebido dentro de la etiqueta <style> en el <head>.
   - Todo el JavaScript DEBE ir embebido dentro de la etiqueta <script> antes del cierre de </body>.
   - Incluye siempre un diseño estético moderno (UI/UX atractivo, modo oscuro/claro limpio, tipografía profesional, interfaz responsiva mobile-first y micro-animaciones en estados :hover/:focus).
   - La respuesta DEBE entregarse en un único bloque de código Markdown marcado como ```html.
2. Fragmentos y Componentes:
   - Si la solicitud es para un componente específico (ej. 'un modal en CSS' o 'un hook de JS'), genera exclusivamente el bloque de código solicitado con su uso de ejemplo.
3. Actualizaciones y Correcciones:
   - Al corregir o mejorar una página web completa, entrega siempre el archivo HTML completo actualizado para garantizar que sea listo para copiar y usar.

[DIRECTIVAS DE BACKEND (Python / Node.js / Multi-lenguaje)]
1. Servidores y APIs Robusta:
   - Al generar código backend (Flask, Express, FastAPI, etc.), incluye siempre estructuración de rutas RESTful, manejo explícito de errores con respuestas JSON estandarizadas y códigos de estado HTTP adecuados (200, 400, 401, 404, 500).
2. Seguridad y Configuración:
   - Gestiona secretos y claves mediante variables de entorno (process.env o os.getenv). Indica las variables necesarias en comentarios.
   - Especifica explícitamente los comandos de instalación de dependencias en un comentario al inicio (ej. # pip install flask dotenv).

[SEGURIDAD Y SANITIZACIÓN]
- Al manipular el DOM con JavaScript dinámico, prefiere textContent o document.createTextNode sobre innerHTML para evitar inyecciones XSS.
- Si se requiere manipular HTML dinámico enriquecido, incluye lógica de sanitización.

[INTERACCIÓN Y COMUNICACIÓN]
- Respuestas Directas y Precisas: Ve directo al grano. Acompaña el código con explicaciones concisas de decisiones técnicas clave.
- Manejo de Ambigüedad: Si el requerimiento del usuario carece de detalles, asume Defaults Profesionales de alto nivel y menciona brevemente las suposiciones realizadas.
- Flexibilidad Tecnológica: Puedes responder y resolver problemas en cualquier lenguaje o framework (Java/Spring, PHP/Laravel, C#/.NET, Go, Rust, React, Vue, Svelte, SQL, etc.).
"""
		self._init_generative_model()

	def _init_generative_model(self, preferred_model=None):
		model_name = preferred_model or getattr(Config, 'GEMINI_MODEL_NAME', 'gemini-1.5-flash')
		# Normalizar modelos no soportados en API pública (ej. gemini-3.6-flash -> gemini-1.5-flash)
		if '3.6' in model_name or '3.0' in model_name:
			model_name = 'gemini-1.5-flash'
		
		self.model_name = model_name
		logger.info(f"Inicializando GenerativeModel de Gemini con modelo: {self.model_name}")
		self.model = genai.GenerativeModel(
			model_name=self.model_name,
			generation_config=self.generation_config,
			safety_settings=self.safety_settings,
			system_instruction=self.system_instruction
		)

	def _ensure_ready(self):
		key = _configure_genai()
		if not key:
			return "Error: No se encontró la clave de API de Gemini (GEMINI_API_KEY). Añade GEMINI_API_KEY=tu_clave_aqui en tu archivo .env y reinicia el servidor."
		return None

	# Máximo de mensajes de historial (Mongo) pasados a Gemini por petición (optimizado a 16 para velocidad)
	MAX_GEMINI_HISTORY_MESSAGES = _env_int("MAX_GEMINI_HISTORY_MESSAGES", 16, min_value=1, max_value=80)

	def _normalize_history_for_gemini(self, db_messages):
		"""Quita mensajes user finales sin respuesta model (turnos incompletos)."""
		msgs = [m for m in (db_messages or []) if (m.get('content') or '').strip()]
		while msgs and msgs[-1].get('role') == 'user':
			msgs.pop()
		return msgs

	def _db_to_gemini_history(self, db_messages):
		hist = []
		for m in self._normalize_history_for_gemini(db_messages):
			role = m.get('role')
			content = (m.get('content') or '').strip()
			if not content:
				continue
			grole = 'user' if role == 'user' else 'model'
			hist.append({'role': grole, 'parts': [content]})
		return hist

	def _start_chat_from_history(self, history_messages=None):
		return self.model.start_chat(history=self._db_to_gemini_history(history_messages or []))

	def _safe_last_text(self, chat):
		last = getattr(chat, "last", None)
		if last and getattr(last, "text", None):
			return last.text
		return "Error: No se recibió respuesta del modelo."
	
	def generate(self, prompt, history_messages=None):
		"""
		Envía un prompt del usuario al modelo y obtiene una respuesta completa.
		"""
		not_ready_err = self._ensure_ready()
		if not_ready_err:
			return not_ready_err
		try:
			chat = self._start_chat_from_history(history_messages)
			chat.send_message(prompt)
			return self._safe_last_text(chat)
		except Exception as e:
			logger.exception("Error al contactar con Gemini: %s", e)
			err_str = str(e)
			if "404" in err_str or "not found" in err_str.lower():
				try:
					logger.info("Reintentando petición con modelo fallback gemini-1.5-flash...")
					self._init_generative_model("gemini-1.5-flash")
					chat = self._start_chat_from_history(history_messages)
					chat.send_message(prompt)
					return self._safe_last_text(chat)
				except Exception as e2:
					return f"Error: Modelo no encontrado ({self.model_name}). Verifica el nombre del modelo en tu .env. Detalle: {e2}"
			if "API_KEY_INVALID" in err_str or "API key not valid" in err_str or "DefaultCredentialsError" in err_str:
				return "Error: Clave de API de Gemini no válida o ausente. Revisa tu GEMINI_API_KEY en tu archivo .env."
			return f"Error: No se pudo obtener una respuesta del modelo. Detalle: {e}"

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
			logger.exception("Error leyendo archivo: %s", e)
			raise

	def _read_pdf_content(self, file_storage):
		"""Extrae el texto de un PDF usando pypdf (o PyPDF2 como fallback)."""
		try:
			try:
				from pypdf import PdfReader
			except ImportError:
				from PyPDF2 import PdfReader
		except ImportError as e:
			logger.exception("Error: instala pypdf con 'pip install pypdf': %s", e)
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
			logger.exception("Error leyendo PDF: %s", e)
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
			logger.exception("Error leyendo archivo adjunto (una vez): %s", e)
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
			logger.exception("Error en _get_readable_content (%s): %s", filename, e)
			return None

	def generate_with_file(self, prompt, file_storage=None, file_bytes=None, filename=None, mimetype=None, history_messages=None):
		not_ready_err = self._ensure_ready()
		if not_ready_err:
			return not_ready_err
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
			chat = self._start_chat_from_history(history_messages)
			file_like = self._wrap_bytes_as_file_like(raw, filename, mimetype)
			ext = os.path.splitext(filename.lower())[1]
			content = self._get_readable_content(file_like, filename, mimetype)

			if content is not None and len(content.strip()) > 0:
				lang = self._lang_for_filename(filename)
				code_block = f"```{lang}\n{content}\n```" if lang else f"```\n{content}\n```"
				combined_prompt = f"{prompt}\n\nArchivo adjunto: {filename}\n{code_block}".strip()
				chat.send_message(combined_prompt)
				return self._safe_last_text(chat)

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
					chat.send_message(combined_prompt)
					return self._safe_last_text(chat)
				except Exception as e2:
					logger.exception("Error leyendo archivo de código (%s): %s", filename, e2)
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
				chat.send_message([uploaded, prompt or f"Analiza el archivo {filename}."])
				return self._safe_last_text(chat)
			finally:
				if tmp_path:
					try:
						os.unlink(tmp_path)
					except FileNotFoundError:
						pass
		except Exception as e:
			logger.exception("Error al contactar con archivo: %s", e)
			err_msg = str(e).strip() if e else ""
			if "pypdf" in err_msg.lower() or "PyPDF" in err_msg or "pdf" in err_msg.lower():
				return "Error al leer el PDF. Asegúrate de tener instalado: pip install pypdf"
			return "Error: No se pudo procesar el archivo. Verifica el formato e inténtalo de nuevo."
	
	def _safe_chunk_text(self, chunk):
		try:
			if getattr(chunk, "text", None):
				return chunk.text
		except (ValueError, AttributeError):
			pass
		try:
			candidates = getattr(chunk, "candidates", [])
			if candidates and candidates[0].content and candidates[0].content.parts:
				return "".join(part.text for part in candidates[0].content.parts if getattr(part, "text", None))
		except (IndexError, AttributeError):
			pass
		return ""

	def generate_stream(self, prompt, history_messages=None):
		"""
		Envía un prompt del usuario al modelo y genera una respuesta en streaming.
		"""
		not_ready_err = self._ensure_ready()
		if not_ready_err:
			yield not_ready_err
			return
		try:
			chat = self._start_chat_from_history(history_messages)
			response = chat.send_message(prompt, stream=True)
			for chunk in response:
				txt = self._safe_chunk_text(chunk)
				if txt:
					yield txt
		except Exception as e:
			logger.exception("Error al contactar con Gemini (streaming): %s", e)
			err_str = str(e)
			if "404" in err_str or "not found" in err_str.lower():
				try:
					logger.info("Reintentando streaming con modelo fallback gemini-1.5-flash...")
					self._init_generative_model("gemini-1.5-flash")
					chat = self._start_chat_from_history(history_messages)
					response = chat.send_message(prompt, stream=True)
					for chunk in response:
						txt = self._safe_chunk_text(chunk)
						if txt:
							yield txt
					return
				except Exception as e2:
					yield f"Error: Modelo no encontrado ({self.model_name}). Detalle: {e2}"
					return
			if "API_KEY_INVALID" in err_str or "API key not valid" in err_str or "DefaultCredentialsError" in err_str:
				yield "Error: Clave de API de Gemini no válida o ausente. Revisa tu GEMINI_API_KEY en tu archivo .env."
			else:
				yield f"Error: No se pudo obtener respuesta del modelo ({e})."

	def generate_stream_with_file(self, prompt, file_storage=None, file_bytes=None, filename=None, mimetype=None, history_messages=None):
		not_ready_err = self._ensure_ready()
		if not_ready_err:
			yield not_ready_err
			return
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
			chat = self._start_chat_from_history(history_messages)
			file_like = self._wrap_bytes_as_file_like(raw, filename, mimetype)
			ext = os.path.splitext(filename.lower())[1]
			content = self._get_readable_content(file_like, filename, mimetype)

			if content is not None and len(content.strip()) > 0:
				lang = self._lang_for_filename(filename)
				code_block = f"```{lang}\n{content}\n```" if lang else f"```\n{content}\n```"
				combined_prompt = f"{prompt}\n\nArchivo adjunto: {filename}\n{code_block}".strip()
				response = chat.send_message(combined_prompt, stream=True)
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
					response = chat.send_message(combined_prompt, stream=True)
					for chunk in response:
						if getattr(chunk, "text", None):
							yield chunk.text
					return
				except Exception as e2:
					logger.exception("Error leyendo archivo de código (%s): %s", filename, e2)
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
				response = chat.send_message([uploaded, prompt or f"Analiza el archivo {filename}."], stream=True)
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
			logger.exception("Error al contactar con archivo (streaming): %s", e)
			err_msg = str(e).strip() if e else ""
			if "pypdf" in err_msg.lower() or "PyPDF" in err_msg or "pdf" in err_msg.lower():
				yield "Error al leer el PDF. Asegúrate de tener instalado: pip install pypdf"
			else:
				yield "Error: No se pudo procesar el archivo. Verifica el formato e inténtalo de nuevo."

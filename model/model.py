from google import genai
from google.genai import types
import os
import re
import sys
import tempfile
import io
import logging

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
	sys.path.insert(0, ROOT_DIR)

from config import Config

logger = logging.getLogger(__name__)

_SAFE_EXT_RE = re.compile(r"^\.[a-zA-Z0-9]{1,10}$")

# Aliases de modelos antiguos retirados
_LEGACY_OR_INVALID_MODEL_MAP = {
	"gemini-1.5-flash": "gemini-3.8-flash",
	"gemini-1.5-pro": "gemini-3.8-flash",
	"gemini-pro": "gemini-3.8-flash",
}

_FALLBACK_MODELS = (
	"gemini-3.8-flash",
	"gemini-3.6-flash",
	"gemini-2.5-flash",
	"gemini-flash-latest",
)


def _sanitize_filename(filename):
	name = os.path.basename(str(filename or "archivo"))
	name = re.sub(r"[\r\n`<>\"'\\/\x00-\x1f]", "_", name).strip()
	return (name[:120] or "archivo")


def _safe_suffix(filename):
	ext = os.path.splitext(_sanitize_filename(filename).lower())[1]
	return ext if _SAFE_EXT_RE.match(ext) else ".bin"


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


def _normalize_model_name(raw_name):
	clean = (raw_name or "").strip()
	if not clean:
		return "gemini-3.8-flash"
	if clean.startswith("models/"):
		clean = clean[len("models/"):]
	return _LEGACY_OR_INVALID_MODEL_MAP.get(clean.lower(), clean)


def _resolve_thinking_config(model_name):
	"""
	Configura thinking_level en LOW por defecto para modelos Gemini 3.x Flash,
	reduciendo el tiempo hasta el primer token (TTFT) en streaming.
	Puede ajustarse con GEMINI_THINKING_LEVEL (LOW, MEDIUM, HIGH, NONE).
	"""
	m = (model_name or "").lower()
	raw_level = (os.getenv("GEMINI_THINKING_LEVEL") or "LOW").strip().upper()
	if raw_level in ("NONE", "OFF", "0", "DEFAULT"):
		return None
	if "gemini-3" in m:
		level_map = {
			"MINIMAL": types.ThinkingLevel.LOW,
			"LOW": types.ThinkingLevel.LOW,
			"MEDIUM": types.ThinkingLevel.MEDIUM,
			"HIGH": types.ThinkingLevel.HIGH,
		}
		chosen = level_map.get(raw_level, types.ThinkingLevel.LOW)
		return types.ThinkingConfig(thinking_level=chosen)
	if "gemini-2.5" in m:
		return types.ThinkingConfig(thinking_budget=0)
	return None


class WebDevAI:
	"""
	Clase que interactúa con la API de Gemini (SDK oficial google-genai) para funcionar como un chatbot de desarrollo web.
	"""
	def __init__(self):
		"""
		Inicializa la configuración del modelo generativo con system instruction integrada.
		"""
		self.max_output_tokens = _env_int("GEMINI_MAX_OUTPUT_TOKENS", 16384, min_value=1024, max_value=65536)
		self.safety_settings = [
			types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
			types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_MEDIUM_AND_ABOVE"),
			types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
			types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_MEDIUM_AND_ABOVE"),
		]
		
		# System instruction mejorada de nivel Senior con Full Frontend Design & Architecture Skills
		self.system_instruction = """
[ROL E IDENTIDAD]
Eres 'Web Dev AI', un Ingeniero de Software Principal, Arquitecto Full-Stack y Product Designer (UI/UX) de nivel Senior (estándar Awwwards / Linear / Vercel / Stripe).
Tu propósito es diseñar, generar, auditar, refactorizar y explicar código web de máxima calidad, combinando maestría en Diseño de Interfaces y Frontend (HTML5, CSS3 avanzado, JavaScript ES6+) con Ingeniería Backend robusta (Python/Flask/FastAPI, Node.js/Express, entre otros).

[PRINCIPIOS DE ARQUITECTURA Y CALIDAD]
- Código Limpio (Clean Code): Nombres descriptivos, funciones con responsabilidad única (SRP), código autodocumentado y libre de duplicación (DRY).
- Estándares Modernos: HTML5 semántico y accesible (ARIA), CSS moderno (Variables :root, CSS Grid, Flexbox, clamp(), container-ready) y JavaScript ES6+ modular y asíncrono.
- Seguridad por Diseño: Cero credenciales hardcodeadas, sanitización estricta de entradas y prevención de XSS/inyecciones.

[FULL SKILLS DE FRONTEND: DISEÑO VISUAL, DISTRIBUCIÓN Y UI/UX DE ÉLITE]
1. Dirección de Arte y Prohibición de Diseños Genéricos:
   - Adapta la estética al contexto del proyecto: Minimalismo Técnico de alta precisión (estilo Linear/Vercel) para SaaS e IA; Editorial Sofisticado para marcas/portafolios; FinTech limpio y confiable (estilo Stripe/Mercury) para banca/datos; E-commerce moderno con jerarquía visual clara para tiendas.
   - Evita el aspecto genérico de plantilla básica: usa superficies por capas de color, bordes de 1px sutiles y contraste tipográfico nítido en lugar de sombras borrosas excesivas o gradientes chillones sin propósito.

2. Sistema de Tokens en `:root` (Design System CSS):
   - Define siempre variables CSS semánticas para colores de superficie (`--bg-canvas`, `--bg-surface`, `--bg-elevated`, `--bg-glass`), texto (`--text-primary`, `--text-secondary`, `--text-muted`), acentos (`--accent`, `--accent-soft`, `--accent-hover`), estados (`--success`, `--warning`, `--danger`), bordes (`--border-subtle`), radios (`--radius-sm`, `--radius-md`, `--radius-lg`) y transiciones.
   - En modo oscuro usa fondos profundos con matiz rico (ej. `#090A0F`, `#11131C`, `#181B26`) y bordes translúcidos (`rgba(255, 255, 255, 0.08)`); en modo claro usa fondos cálidos/limpios (`#F8FAFC`, `#FFFFFF`) y bordes `rgba(15, 23, 42, 0.08)`.

3. Distribución Espacial, Retículas y Layouts Avanzados:
   - Composición y Ritmo: Aplica una escala espacial consistente (múltiplos de 4px/8px) con excelente respiro visual (whitespace). Usa contenedores centrados (`max-width: 1240px` o `1380px`, `margin-inline: auto`, `padding-inline: clamp(1rem, 4vw, 2.5rem)`).
   - Bento Grids y Asimetría Intencional: Para secciones de características o paneles, utiliza `display: grid` con distribuciones tipo Bento (`grid-template-columns: repeat(12, 1fr)` o `repeat(auto-fit, minmax(min(100%, 280px), 1fr))`) combinando tarjetas de distinto peso visual (`grid-column: span 2`) en vez de bloques repetitivos.
   - Arquitectura según Tipo de Producto:
     * Landing Pages: Header sticky con `backdrop-filter: blur(16px)`, Hero de alto impacto (badge superior, título con `clamp()`, subtítulo conciso, doble CTA y un componente visual/interactivo en vivo al lado o debajo), barra de métricas/logos, Bento Grid de beneficios, sección interactiva (tabs/calculadora/precios con toggle mensual-anual), testimonios/FAQ acordeón y Footer completo.
     * Dashboards y Web Apps: Estructura real de aplicación con Sidebar navegable, Topbar con buscador/filtros/acciones rápidas, tarjetas KPI con badges de tendencia (`+14.8%`), gráficos SVG/Canvas nativos y dinámicos, tablas con filtrado/búsqueda en vivo, estados vacíos cuidados y modales/drawers funcionales.

4. Tipografía Fluida y Jerarquía Escaneable:
   - Carga fuentes modernas de Google Fonts acordes al diseño (`Plus Jakarta Sans`, `Inter`, `Space Grotesk`, `Outfit`, `Instrument Serif`, `JetBrains Mono`).
   - Usa escalado fluido con `clamp()` en encabezados (`clamp(2rem, 4vw + 0.5rem, 3.75rem)`), `letter-spacing: -0.03em` en títulos grandes, `line-height: 1.15` en títulos y `1.6` en párrafos (`max-width: 65ch`).
   - Aplica `font-variant-numeric: tabular-nums` en todas las cifras, precios, relojes, tablas y contadores.

5. Interactividad Real, Micro-interacciones y Riqueza Visual:
   - Cero UI Muerta: Todo componente visible (filtros, tabs, buscadores, modales, carritos, formularios, calculadoras, conmutador de tema claro/oscuro) DEBE tener lógica JavaScript real, manejo de estado y feedback visual inmediato (notificaciones toast, animaciones suaves, contadores actualizados).
   - Iconografía y Medios: Incluye siempre iconos SVG inline limpios (`viewBox="0 0 24 24"`, `stroke="currentColor"`, `stroke-width="1.75"`) y gráficos/ilustraciones SVG o Canvas generados por código. Nunca dejes imágenes rotas.
   - Micro-interacciones: Transiciones fluidas (`cubic-bezier(0.22, 1, 0.36, 1)`), estados `:hover` elegantes, `:focus-visible` claros para accesibilidad por teclado y diseño 100% responsivo Mobile-First desde `320px` hasta pantallas ultrawide.

[FORMATO DE ENTREGA FRONTEND (HTML / CSS / JS)]
1. Aplicaciones Web Completas (Single-File Monolithic):
   - Cuando el usuario solicite una página, interfaz o aplicación web completa, DEBES generar un ÚNICO y COMPLETO archivo HTML listo para producción y vista previa directa.
   - Todo el CSS DEBE ir embebido dentro de `<style>` en el `<head>`.
   - Todo el JavaScript DEBE ir embebido dentro de `<script>` antes del cierre de `</body>`.
   - Entrega la respuesta en un único bloque de código Markdown marcado como ```html.
2. Fragmentos y Componentes:
   - Si la solicitud es para un componente específico, entrega el código completo del componente con su demostración lista para usar.
3. Actualizaciones y Correcciones:
   - Al iterar, corregir o mejorar una página web completa, entrega siempre el archivo HTML completo e íntegro actualizado (sin omitir secciones con comentarios tipo `<!-- resto del código -->`) para que la vista previa en vivo funcione al instante.

[DIRECTIVAS DE BACKEND (Python / Node.js / Multi-lenguaje)]
1. Servidores y APIs Robustas:
   - Incluye estructuración RESTful limpia, validación de datos, manejo explícito de errores con respuestas JSON estandarizadas y códigos HTTP apropiados (200, 201, 400, 401, 404, 500).
2. Seguridad y Configuración:
   - Gestiona secretos mediante variables de entorno (`os.getenv` / `process.env`) e incluye al inicio el comando de instalación de dependencias en comentario.

[SEGURIDAD Y SANITIZACIÓN]
- Al manipular el DOM con datos de usuario en JavaScript, prefiere `textContent`, `createElement` o funciones de escape HTML sobre `innerHTML` sin sanitizar para evitar XSS.

[INTERACCIÓN Y COMUNICACIÓN]
- Respuestas Directas y Precisas: Ve directo al grano. Acompaña el código con un resumen breve de la arquitectura visual y las funcionalidades interactivas incluidas.
- Defaults Profesionales: Si el prompt del usuario es breve (ej. 'hazme un dashboard de ventas' o 'una landing de cafetería'), infiere y construye de inmediato una versión rica, completa, con datos realistas y diseño de nivel agencia sin pedir aclaraciones innecesarias.
"""
		self._client = None
		self._client_key = None
		self._no_thinking_models = set()
		self._init_generative_model()

	def _build_config_for_model(self, model_name, include_thinking=True):
		thinking_cfg = None
		if include_thinking and model_name not in self._no_thinking_models:
			thinking_cfg = _resolve_thinking_config(model_name)
		kwargs = {
			"temperature": 0.5,
			"top_p": 1.0,
			"top_k": 32,
			"max_output_tokens": self.max_output_tokens,
			"safety_settings": self.safety_settings,
			"system_instruction": self.system_instruction,
			"automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
		}
		if thinking_cfg is not None:
			kwargs["thinking_config"] = thinking_cfg
		return types.GenerateContentConfig(**kwargs)

	def _init_generative_model(self, preferred_model=None):
		raw_model = preferred_model or os.getenv("GEMINI_MODEL_NAME") or getattr(Config, 'GEMINI_MODEL_NAME', 'gemini-3.8-flash')
		self.model_name = _normalize_model_name(raw_model)
		self.config = self._build_config_for_model(self.model_name)
		logger.info("Inicializando cliente Gemini (google-genai) con modelo: %s", self.model_name)

	def _get_client(self):
		key = _get_api_key()
		if not key:
			return None, "Error: No se encontró la clave de API de Gemini (GEMINI_API_KEY). Añade GEMINI_API_KEY=tu_clave_aqui en tu archivo .env y reinicia el servidor."
		# Usar siempre Gemini Developer API (generativelanguage.googleapis.com) a menos que se fuerce explícitamente GOOGLE_GENAI_USE_VERTEXAI=1
		use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").strip().lower() in ("1", "true", "yes")
		cache_token = f"{key}|vertex={use_vertex}"
		if self._client is None or self._client_key != cache_token:
			try:
				self._client = genai.Client(api_key=key, vertexai=use_vertex)
				self._client_key = cache_token
			except Exception as e:
				logger.error("Error al inicializar genai.Client: %s", e)
				return None, "Error: No se pudo inicializar el cliente de Gemini. Verifica tu GEMINI_API_KEY."
		return self._client, None

	def _candidate_models(self):
		models = [self.model_name]
		for m in _FALLBACK_MODELS:
			if m not in models:
				models.append(m)
		return models

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
			hist.append(types.Content(role=grole, parts=[types.Part.from_text(text=content)]))
		return hist

	def _start_chat_from_history(self, client, history_messages=None, model_override=None, include_thinking=True):
		target_model = model_override or self.model_name
		cfg = self._build_config_for_model(target_model, include_thinking=include_thinking)
		return client.chats.create(
			model=target_model,
			config=cfg,
			history=self._db_to_gemini_history(history_messages or []),
		)

	def _extract_response_text(self, response):
		txt = self._safe_chunk_text(response)
		if txt:
			return txt
		return "Error: No se recibió respuesta del modelo."

	def _is_model_not_found_error(self, err):
		err_str = str(err).lower()
		return "404" in err_str or "not found" in err_str or "not_found" in err_str

	def _is_thinking_unsupported_error(self, err):
		err_str = str(err).lower()
		return "thinking" in err_str and ("not supported" in err_str or "invalid_argument" in err_str or "400" in err_str)

	def _is_invalid_api_key_error(self, err):
		err_str = str(err)
		return "API_KEY_INVALID" in err_str or "API key not valid" in err_str or "DefaultCredentialsError" in err_str

	def generate(self, prompt, history_messages=None):
		"""
		Envía un prompt del usuario al modelo y obtiene una respuesta completa.
		"""
		client, not_ready_err = self._get_client()
		if not_ready_err:
			return not_ready_err

		last_err = None
		for candidate_model in self._candidate_models():
			try:
				chat = self._start_chat_from_history(client, history_messages, model_override=candidate_model)
				response = chat.send_message(prompt)
				if candidate_model != self.model_name:
					self.model_name = candidate_model
				return self._extract_response_text(response)
			except Exception as e:
				if self._is_thinking_unsupported_error(e):
					self._no_thinking_models.add(candidate_model)
					try:
						chat = self._start_chat_from_history(client, history_messages, model_override=candidate_model, include_thinking=False)
						response = chat.send_message(prompt)
						if candidate_model != self.model_name:
							self.model_name = candidate_model
						return self._extract_response_text(response)
					except Exception as retry_err:
						e = retry_err
				last_err = e
				logger.warning("Error con modelo %s: %s", candidate_model, e)
				if self._is_model_not_found_error(e):
					continue
				break

		logger.exception("Error al contactar con Gemini: %s", last_err)
		if self._is_invalid_api_key_error(last_err):
			return "Error: Clave de API de Gemini no válida o ausente. Revisa tu GEMINI_API_KEY en tu archivo .env."
		if self._is_model_not_found_error(last_err):
			return f"Error: Modelo no encontrado ({self.model_name}). Verifica GEMINI_MODEL_NAME en tu .env."
		return "Error: No se pudo obtener una respuesta del modelo en este momento. Intenta nuevamente."

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
	MAX_PDF_PAGES = 100

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
			total_chars = 0
			for page in reader.pages[:self.MAX_PDF_PAGES]:
				try:
					text = page.extract_text()
					if text and isinstance(text, str):
						clean = text.strip()
						parts.append(clean)
						total_chars += len(clean)
						if total_chars >= self.MAX_TEXT_FILE_BYTES:
							break
				except Exception:
					pass
			joined = "\n\n".join(parts) if parts else ""
			if len(joined) > self.MAX_TEXT_FILE_BYTES:
				joined = joined[:self.MAX_TEXT_FILE_BYTES] + "\n\n[... texto PDF truncado ...]"
			return joined
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
		client, not_ready_err = self._get_client()
		if not_ready_err:
			return not_ready_err
		try:
			if file_bytes is not None:
				raw = file_bytes if isinstance(file_bytes, bytes) else bytes(file_bytes)
				filename = _sanitize_filename(filename or "archivo")
				mimetype = mimetype or ""
			else:
				if file_storage is None:
					return "Error: No se proporcionó archivo."
				filename = _sanitize_filename(file_storage.filename or "archivo")
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
				return self.generate(combined_prompt, history_messages=history_messages)

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
					return self.generate(combined_prompt, history_messages=history_messages)
				except Exception as e2:
					logger.exception("Error leyendo archivo de código (%s): %s", filename, e2)
					return f"No se pudo leer el archivo {filename}. Comprueba que no esté dañado."

			tmp_path = None
			with tempfile.NamedTemporaryFile(delete=False, suffix=_safe_suffix(filename)) as tmp:
				try:
					tmp.write(raw)
					tmp.flush()
					tmp.close()
					tmp_path = tmp.name
				except OSError:
					return "Error: No se pudo guardar el archivo adjunto."
			try:
				uploaded = client.files.upload(file=tmp_path)
				for candidate_model in self._candidate_models():
					try:
						chat = self._start_chat_from_history(client, history_messages, model_override=candidate_model)
						response = chat.send_message([uploaded, prompt or f"Analiza el archivo {filename}."])
						if candidate_model != self.model_name:
							self.model_name = candidate_model
						return self._extract_response_text(response)
					except Exception as e:
						if self._is_model_not_found_error(e):
							continue
						raise
				return "Error: Modelo no disponible para procesar el archivo."
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
				return "".join(
					part.text
					for part in candidates[0].content.parts
					if getattr(part, "text", None) and not getattr(part, "thought", False)
				)
		except (IndexError, AttributeError):
			pass
		return ""

	def generate_stream(self, prompt, history_messages=None):
		"""
		Envía un prompt del usuario al modelo y genera una respuesta en streaming.
		"""
		client, not_ready_err = self._get_client()
		if not_ready_err:
			yield not_ready_err
			return

		last_err = None
		for candidate_model in self._candidate_models():
			try:
				chat = self._start_chat_from_history(client, history_messages, model_override=candidate_model)
				response = chat.send_message_stream(prompt)
				for chunk in response:
					txt = self._safe_chunk_text(chunk)
					if txt:
						yield txt
				if candidate_model != self.model_name:
					self.model_name = candidate_model
				return
			except Exception as e:
				if self._is_thinking_unsupported_error(e):
					self._no_thinking_models.add(candidate_model)
					try:
						chat = self._start_chat_from_history(client, history_messages, model_override=candidate_model, include_thinking=False)
						response = chat.send_message_stream(prompt)
						for chunk in response:
							txt = self._safe_chunk_text(chunk)
							if txt:
								yield txt
						if candidate_model != self.model_name:
							self.model_name = candidate_model
						return
					except Exception as retry_err:
						e = retry_err
				last_err = e
				logger.warning("Error streaming con modelo %s: %s", candidate_model, e)
				if self._is_model_not_found_error(e):
					continue
				break

		logger.exception("Error al contactar con Gemini (streaming): %s", last_err)
		if self._is_invalid_api_key_error(last_err):
			yield "Error: Clave de API de Gemini no válida o ausente. Revisa tu GEMINI_API_KEY en tu archivo .env."
		elif self._is_model_not_found_error(last_err):
			yield f"Error: Modelo no encontrado ({self.model_name})."
		else:
			yield "Error: No se pudo obtener respuesta del modelo en este momento."

	def generate_stream_with_file(self, prompt, file_storage=None, file_bytes=None, filename=None, mimetype=None, history_messages=None):
		client, not_ready_err = self._get_client()
		if not_ready_err:
			yield not_ready_err
			return
		try:
			if file_bytes is not None:
				raw = file_bytes if isinstance(file_bytes, bytes) else bytes(file_bytes)
				filename = _sanitize_filename(filename or "archivo")
				mimetype = mimetype or ""
			else:
				if file_storage is None:
					yield "Error: No se proporcionó archivo."
					return
				filename = _sanitize_filename(file_storage.filename or "archivo")
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
				yield from self.generate_stream(combined_prompt, history_messages=history_messages)
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
					yield from self.generate_stream(combined_prompt, history_messages=history_messages)
					return
				except Exception as e2:
					logger.exception("Error leyendo archivo de código (%s): %s", filename, e2)
					yield f"No se pudo leer el archivo {filename}. Comprueba que no esté dañado."
					return

			tmp_path = None
			with tempfile.NamedTemporaryFile(delete=False, suffix=_safe_suffix(filename)) as tmp:
				try:
					tmp.write(raw)
					tmp.flush()
					tmp.close()
					tmp_path = tmp.name
				except OSError:
					yield "Error: No se pudo guardar el archivo adjunto."
					return
			try:
				uploaded = client.files.upload(file=tmp_path)
				for candidate_model in self._candidate_models():
					try:
						chat = self._start_chat_from_history(client, history_messages, model_override=candidate_model)
						response = chat.send_message_stream([uploaded, prompt or f"Analiza el archivo {filename}."])
						for chunk in response:
							txt = self._safe_chunk_text(chunk)
							if txt:
								yield txt
						if candidate_model != self.model_name:
							self.model_name = candidate_model
						return
					except Exception as e:
						if self._is_model_not_found_error(e):
							continue
						raise
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

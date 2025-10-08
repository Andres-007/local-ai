import google.generativeai as genai
from config import Config

# Configura la API de Gemini con la clave obtenida desde la configuración
try:
    genai.configure(api_key=Config.GEMINI_API_KEY)
except (AttributeError, TypeError):
    print("Error: La clave de API de Gemini no se ha configurado. Asegúrate de crear un archivo .env con tu GEMINI_API_KEY.")
    pass

class WebDevAI:
    """
    Clase que interactúa con la API de Gemini para funcionar como un chatbot de desarrollo web.
    """
    def __init__(self):
        """
        Inicializa el modelo generativo de Gemini y el historial de conversación.
        """
        generation_config = {
            "temperature": 0.5,
            "top_p": 1,
            "top_k": 32,
            "max_output_tokens": 8192, # Aumentado para páginas más complejas
        }
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        # **FIX**: Instrucción del sistema mucho más específica y robusta
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
        - Si te piden código en un lenguaje o framework que no manejas (ej. Java/Spring, PHP/Laravel), explica educadamente tus capacidades actuales (Frontend, Python/Flask, Node.js/Express) y ofrece generar una solución con esas tecnologías.
        - Para preguntas teóricas, proporciona explicaciones claras y concisas.  
        """
        # Inicia la conversación con la instrucción del sistema
        self.convo = self.model.start_chat(history=[
            {'role': 'user', 'parts': [system_instruction]},
            {'role': 'model', 'parts': ["Entendido. Soy un asistente de IA especializado únicamente en generar código web completo en un solo archivo HTML. ¿Qué página web necesitas que construya?"]}
        ])
    def generate(self, prompt):
        """
        Envía un prompt del usuario al modelo y obtiene una respuesta.

        Args:
            prompt (str): La pregunta o instrucción del usuario.

        Returns:
            str: La respuesta generada por el modelo de IA en formato Markdown.
        """
        try:
            self.convo.send_message(prompt)
            return self.convo.last.text
        except Exception as e:
            print(f"Error al contactar la API de Gemini: {e}")
            return "Error: No se pudo obtener una respuesta del modelo. Verifica tu clave de API y la conexión a internet."

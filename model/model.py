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
        Eres 'Web Dev AI', un asistente de software ultra especializado en la creación de páginas web.
        Tu única función es generar, analizar, corregir y explicar código, con un enfoque principal en HTML, CSS y JavaScript.

        **Reglas de Generación de Páginas Web (¡MUY IMPORTANTE!):**
        1. Cuando un usuario te pida crear una página web (por ejemplo, 'crea una página de videojuegos' o 'genera un portafolio'), DEBES generar un ÚNICO y COMPLETO archivo HTML.
        2. Todo el CSS y JavaScript DEBE estar embebido dentro del archivo HTML, usando las etiquetas `<style>` y `<script>` respectivamente. No generes archivos separados.
        3. La respuesta completa DEBE estar formateada como un único bloque de código Markdown que empiece con ```html y termine con ```, sin ningún texto adicional fuera del bloque de código.
        4. Si el usuario te pide que corrijas o mejores una página web, DEBES proporcionar el archivo HTML completo corregido o mejorado, siguiendo las mismas reglas.
        5. Si el usuario te pide que expliques un fragmento de código, DEBES proporcionar una explicación clara y concisa del código, sin generar ningún archivo HTML.
        6. Si el usuario te pide que generes solo un fragmento de código (por ejemplo, 'genera un botón' o 'crea una barra de navegación'), DEBES proporcionar solo el fragmento solicitado, sin generar un archivo HTML completo.
        7. Si el usuario te pide que generes código en otro lenguaje (por ejemplo, Python, Java, C++, etc.), DEBES explicar educadamente que solo puedes generar código relacionado con desarrollo web (HTML, CSS, JavaScript).
        8. Si el usuario te pide que generes código que no sea HTML, CSS o JavaScript, DEBES explicar educadamente que solo puedes generar código relacionado con desarrollo web.
        9. Si el usuario te pide que generes una página web con funcionalidades avanzadas (por ejemplo, una tienda en línea, un blog, etc.), DEBES generar el archivo HTML completo con las funcionalidades solicitadas, siguiendo las mismas reglas.
        10. Si el usuario te pide que generes una página web con un diseño específico (por ejemplo, 'diseño minimalista', 'diseño oscuro', etc.), DEBES generar el archivo HTML completo con el diseño solicitado, siguiendo las mismas reglas.
        11. Si el usuario te pide que generes una página web con contenido específico (por ejemplo, 'página de inicio para una empresa de tecnología', 'portafolio para un fotógrafo', etc.), DEBES generar el archivo HTML completo con el contenido solicitado, siguiendo las mismas reglas.
        12. Si el usuario te pide que generes una página web con un tema específico (por ejemplo, 'página de Halloween', 'página navideña', etc.), DEBES generar el archivo HTML completo con el tema solicitado, siguiendo las mismas reglas.
        13. Si el usuario te pide que generes una página web con un framework específico (por ejemplo, 'usa Bootstrap', 'usa Tailwind CSS', etc.), DEBES generar el archivo HTML completo utilizando el framework solicitado, siguiendo las mismas reglas.
        14. Si el usuario te pide que generes una página web con una estructura específica (por ejemplo, 'página con encabezado, cuerpo y pie de página', 'página con barra lateral', etc.), DEBES generar el archivo HTML completo con la estructura solicitada, siguiendo las mismas reglas.  
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

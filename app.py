from flask import Flask, render_template, request, jsonify
from model.model import WebDevAI

# Inicializa la aplicación Flask
# Se especifican las carpetas de plantillas y archivos estáticos
app = Flask(__name__, template_folder='web/templates', static_folder='web/static')

# Inicializa la instancia de nuestro modelo de IA
ai_model = WebDevAI()

@app.route('/')
def index():
    """
    Ruta principal que renderiza la interfaz de chat.
    """
    return render_template('index.html')

@app.route('/api/generate', methods=['POST'])
def api_generate():
    """
    Endpoint de la API para procesar las solicitudes del chat.
    Recibe un prompt del usuario y devuelve la respuesta de la IA.
    """
    if not request.is_json:
        return jsonify({"error": "La solicitud debe ser de tipo JSON"}), 400

    data = request.get_json()
    prompt = data.get('prompt')

    if not prompt:
        return jsonify({"error": "Falta el parámetro 'prompt'"}), 400

    try:
        # Llama al método 'generate' de nuestro modelo de IA
        # Pasamos un prompt único en lugar de tarea y código por separado
        response_text = ai_model.generate(prompt)
        # Devuelve la respuesta en formato JSON
        return jsonify({"response": response_text})
    except Exception as e:
        # Manejo de errores en caso de que algo falle en el backend
        print(f"Error en la API: {e}")
        return jsonify({"error": "Ocurrió un error interno en el servidor"}), 500

if __name__ == '__main__':
    # Ejecuta la aplicación en modo de depuración
    app.run(debug=True)


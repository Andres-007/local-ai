from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from model.model import WebDevAI
from model.database import ChatDatabase
import secrets
import os

app = Flask(__name__, template_folder='web/templates', static_folder='web/static')
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))

# Habilitar CORS
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://.io", "http://localhost:5000"],
        "supports_credentials": True
    }
})

# Inicializar servicios
ai_model = WebDevAI()
db = ChatDatabase()

@app.route('/')
def index():
    """Ruta principal"""
    # Generar user_id único si no existe
    if 'user_id' not in session:
        session['user_id'] = secrets.token_hex(8)
    return render_template('index.html')

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Obtiene todas las conversaciones del usuario"""
    user_id = session.get('user_id', 'anonymous')
    conversations = db.get_user_conversations(user_id)
    return jsonify({"conversations": conversations})

@app.route('/api/conversations', methods=['POST'])
def create_conversation():
    """Crea una nueva conversación"""
    user_id = session.get('user_id', 'anonymous')
    data = request.get_json()
    title = data.get('title', 'Nueva Conversación')
    
    conversation_id = db.create_conversation(user_id, title)
    return jsonify({"conversation_id": conversation_id})

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Obtiene una conversación específica con sus mensajes"""
    conversation = db.get_conversation_with_messages(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversación no encontrada"}), 404
    return jsonify(conversation)

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Elimina una conversación"""
    success = db.delete_conversation(conversation_id)
    if success:
        return jsonify({"message": "Conversación eliminada"})
    return jsonify({"error": "No se pudo eliminar"}), 400

@app.route('/api/conversations/<conversation_id>/title', methods=['PUT'])
def update_conversation_title(conversation_id):
    """Actualiza el título de una conversación"""
    data = request.get_json()
    new_title = data.get('title')
    
    if not new_title:
        return jsonify({"error": "Título requerido"}), 400
    
    success = db.update_conversation_title(conversation_id, new_title)
    if success:
        return jsonify({"message": "Título actualizado"})
    return jsonify({"error": "No se pudo actualizar"}), 400

@app.route('/api/generate', methods=['POST'])
def api_generate():
    """Endpoint principal para generar respuestas de la IA"""
    if not request.is_json:
        return jsonify({"error": "La solicitud debe ser JSON"}), 400

    data = request.get_json()
    prompt = data.get('prompt')
    conversation_id = data.get('conversation_id')
    
    if not prompt:
        return jsonify({"error": "Falta el parámetro 'prompt'"}), 400

    try:
        # Si no hay conversation_id, crear una nueva conversación
        if not conversation_id:
            user_id = session.get('user_id', 'anonymous')
            # Generar título automático del primer mensaje
            title = prompt[:50] + "..." if len(prompt) > 50 else prompt
            conversation_id = db.create_conversation(user_id, title)
        
        # Guardar el mensaje del usuario
        db.save_message(conversation_id, 'user', prompt)
        
        # Generar respuesta de la IA
        response_text = ai_model.generate(prompt)
        
        # Guardar la respuesta de la IA
        db.save_message(conversation_id, 'bot', response_text)
        
        return jsonify({
            "response": response_text,
            "conversation_id": conversation_id
        })
        
    except Exception as e:
        print(f"Error en la API: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@app.route('/api/search', methods=['POST'])
def search_conversations():
    """Busca en las conversaciones del usuario"""
    user_id = session.get('user_id', 'anonymous')
    data = request.get_json()
    query = data.get('query', '')
    
    if not query:
        return jsonify({"error": "Query requerido"}), 400
    
    results = db.search_conversations(user_id, query)
    return jsonify({"results": results})

if __name__ == '__main__':
    app.run(debug=True)
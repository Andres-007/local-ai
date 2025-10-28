from flask import Flask, render_template, request, jsonify, session, Response, redirect, url_for
from flask_cors import CORS
from model.model import WebDevAI
from model.database import ChatDatabase
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import secrets
import os
from bson.objectid import ObjectId

app = Flask(__name__, template_folder='web/templates', static_folder='web/static')
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))

# Configuración de CORS más específica si es necesario, pero esto funciona para desarrollo
CORS(app) 

# Inicializar servicios
ai_model = WebDevAI()
db = ChatDatabase()

# --- Decorador para rutas protegidas ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({"error": "Autenticación requerida"}), 401
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# --- Rutas de Autenticación y Vistas ---
@app.route('/')
def index():
    """
    Muestra la página de inicio (login.html) si el usuario no está en sesión.
    Si ya está logueado, lo redirige al chat.
    """
    if 'user_id' in session:
        return redirect(url_for('chat'))
    # Esta es la página que contiene el carrusel
    return render_template('login.html') 

@app.route('/chat')
@login_required
def chat():
    """
    Ruta principal de la aplicación de chat (index.html), protegida por login.
    """
    return render_template('index.html') # Asumo que tu chat está en index.html

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email y contraseña son requeridos"}), 400

    user = db.get_user_by_email(email)

    if user and check_password_hash(user['password'], password):
        session['user_id'] = str(user['_id'])
        session['user_email'] = user['email']
        return jsonify({"message": "Inicio de sesión exitoso"}), 200
    
    return jsonify({"error": "Credenciales inválidas"}), 401

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email y contraseña son requeridos"}), 400

    if db.get_user_by_email(email):
        return jsonify({"error": "El email ya está registrado"}), 409

    hashed_password = generate_password_hash(password)
    user_id = db.create_user(email, hashed_password)
    
    session['user_id'] = user_id
    session['user_email'] = email

    return jsonify({"message": "Registro exitoso", "user_id": user_id}), 201

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/check_auth')
def check_auth():
    if 'user_id' in session:
        return jsonify({"authenticated": True, "email": session.get('user_email')})
    return jsonify({"authenticated": False})


# --- NUEVA RUTA PÚBLICA PARA PROYECTOS ---
@app.route('/api/projects', methods=['GET'])
def get_projects():
    """
    Obtiene la lista de todos los proyectos para mostrar en el carrusel.
    Esta es una ruta pública, no requiere autenticación,
    ya que se muestra en la página de login (index).
    """
    try:
        projects = db.get_all_projects()
        # Devuelve los proyectos en un objeto JSON
        return jsonify({"projects": projects})
    except Exception as e:
        print(f"Error en /api/projects: {e}")
        return jsonify({"error": "Error interno al obtener proyectos"}), 500


# --- Rutas de la API de Chat (Protegidas) ---
@app.route('/api/conversations', methods=['GET'])
@login_required
def get_conversations():
    user_id = session['user_id']
    conversations = db.get_user_conversations(user_id)
    return jsonify({"conversations": conversations})

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
@login_required
def get_conversation(conversation_id):
    conversation = db.get_conversation_with_messages(conversation_id)
    if not conversation or conversation['user_id'] != session['user_id']:
        return jsonify({"error": "Conversación no encontrada o no autorizada"}), 404
    return jsonify(conversation)

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
@login_required
def delete_conversation(conversation_id):
    success = db.delete_conversation(conversation_id, session['user_id'])
    if success:
        return jsonify({"message": "Conversación eliminada"})
    return jsonify({"error": "No se pudo eliminar o no tienes permiso"}), 400

@app.route('/api/generate', methods=['POST'])
@login_required
def api_generate():
    data = request.get_json()
    prompt = data.get('prompt')
    conversation_id_str = data.get('conversation_id')
    user_id = session['user_id']
    
    if not prompt:
        return jsonify({"error": "Falta el parámetro 'prompt'"}), 400

    try:
        if not conversation_id_str:
            title = prompt[:50] + "..." if len(prompt) > 50 else prompt
            conversation_id_str = db.create_conversation(user_id, title)
        
        conversation_id = ObjectId(conversation_id_str)
        db.save_message(conversation_id, 'user', prompt)
        response_text = ai_model.generate(prompt)
        db.save_message(conversation_id, 'bot', response_text)
        
        return jsonify({
            "response": response_text,
            "conversation_id": conversation_id_str
        })
    except Exception as e:
        print(f"Error en la API: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500

@app.route('/api/generate-stream', methods=['POST'])
@login_required
def api_generate_stream():
    data = request.get_json()
    prompt = data.get('prompt')
    conversation_id_str = data.get('conversation_id')
    
    if not prompt or not conversation_id_str:
        return jsonify({"error": "Faltan 'prompt' o 'conversation_id'"}), 400

    def generate():
        full_response = ""
        try:
            conversation_id = ObjectId(conversation_id_str)
            db.save_message(conversation_id, 'user', prompt)
            
            for chunk in ai_model.generate_stream(prompt):
                full_response += chunk
                yield chunk
            
            db.save_message(conversation_id, 'bot', full_response)
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(f"Error en streaming: {e}")
            yield error_msg
    
    return Response(generate(), mimetype='text/plain')

if __name__ == '__main__':
    # Asegúrate de que 'host' sea '0.0.0.0' si necesitas acceder desde otros dispositivos en la red
    app.run(debug=True, host='0.0.0.0', port=4000)

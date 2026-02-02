from flask import Flask, render_template, request, jsonify, session, Response, redirect, url_for
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth
from model.model import WebDevAI
from model.database import ChatDatabase
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import secrets
import os
from bson.objectid import ObjectId
from bson.errors import InvalidId

app = Flask(__name__, template_folder='web/templates', static_folder='web/static')
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))

# OAuth Google (opcional: requiere GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET en .env)
oauth = OAuth(app)
google_client_id = os.getenv('GOOGLE_CLIENT_ID', '').strip()
google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
if google_client_id and google_client_secret:
    oauth.register(
        name='google',
        client_id=google_client_id,
        client_secret=google_client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

# Configuración de CORS más específica si es necesario, pero esto funciona para desarrollo
CORS(app) 

# Inicializar servicios
ai_model = WebDevAI()
db = ChatDatabase()

def _parse_paging_args(default_limit=50, max_limit=200):
    try:
        limit = request.args.get('limit', default_limit, type=int)
        offset = request.args.get('offset', 0, type=int)
    except ValueError:
        limit = default_limit
        offset = 0
    limit = max(1, min(limit, max_limit))
    offset = max(0, offset)
    return limit, offset

def _extract_request_data():
    if request.is_json:
        data = request.get_json(silent=True) or {}
        prompt = data.get('prompt')
        conversation_id = data.get('conversation_id')
        file = None
    else:
        prompt = request.form.get('prompt')
        conversation_id = request.form.get('conversation_id')
        file = request.files.get('file')
    return (prompt or '').strip(), conversation_id, file

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
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email y contraseña son requeridos"}), 400

    if not db._ensure_connection():
        return jsonify({"error": "Servicio no disponible. Intenta más tarde."}), 503

    user = db.get_user_by_email(email)

    if not user or not user.get('password'):
        return jsonify({"error": "Credenciales inválidas"}), 401
    if check_password_hash(user['password'], password):
        session['user_id'] = str(user['_id'])
        session['user_email'] = user['email']
        return jsonify({"message": "Inicio de sesión exitoso"}), 200

    return jsonify({"error": "Credenciales inválidas"}), 401

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email y contraseña son requeridos"}), 400

    if not db._ensure_connection():
        return jsonify({"error": "Servicio no disponible. Intenta más tarde."}), 503

    if db.get_user_by_email(email):
        return jsonify({"error": "El email ya está registrado"}), 409

    hashed_password = generate_password_hash(password)
    user_id = db.create_user(email, hashed_password)
    if not user_id:
        return jsonify({"error": "No se pudo crear la cuenta. Verifica la conexión a la base de datos."}), 503

    session['user_id'] = user_id
    session['user_email'] = email

    return jsonify({"message": "Registro exitoso", "user_id": user_id}), 201

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Recuperar contraseña: recibe email y responde siempre igual por seguridad."""
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip()
    if not email:
        return jsonify({"error": "El email es requerido"}), 400
    # Por seguridad no revelamos si el email existe. Aquí podrías enviar un correo real con Flask-Mail.
    return jsonify({
        "message": "Si existe una cuenta con ese email, recibirás un enlace para restablecer tu contraseña en unos minutos."
    }), 200


@app.route('/auth/google')
def auth_google():
    """Redirige a Google para iniciar sesión con OAuth."""
    if not google_client_id or not google_client_secret:
        return redirect(url_for('index') + '?error=google_not_configured')
    return oauth.google.authorize_redirect(url_for('auth_google_callback', _external=True))


@app.route('/auth/google/callback')
def auth_google_callback():
    """Callback de Google OAuth: crea o obtiene usuario y deja sesión iniciada."""
    if not google_client_id or not google_client_secret:
        return redirect(url_for('index'))
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo') or {}
        email = (user_info.get('email') or '').strip().lower()
        google_id = user_info.get('sub')
        name = user_info.get('name') or ''
        if not email or not google_id:
            return redirect(url_for('index') + '?error=invalid_google_user')
        if not db._ensure_connection():
            return redirect(url_for('index') + '?error=service_unavailable')
        user = db.get_user_by_google_id(google_id)
        if not user:
            user = db.get_user_by_email(email)
            if user:
                db.link_google_to_user(str(user['_id']), google_id, name)
                user_id = str(user['_id'])
            else:
                user_id = db.create_google_user(email, google_id, name)
                if not user_id:
                    return redirect(url_for('index') + '?error=create_failed')
        else:
            user_id = str(user['_id'])
        session['user_id'] = user_id
        session['user_email'] = email
        return redirect(url_for('chat'))
    except Exception as e:
        print(f"Google OAuth error: {e}")
        return redirect(url_for('index') + '?error=oauth_failed')


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
        limit, offset = _parse_paging_args(default_limit=12, max_limit=100)
        projects = db.get_all_projects(limit=limit + 1, skip=offset)
        has_more = len(projects) > limit
        projects = projects[:limit]
        # Devuelve los proyectos en un objeto JSON
        return jsonify({"projects": projects, "has_more": has_more, "limit": limit, "offset": offset})
    except Exception as e:
        print(f"Error en /api/projects: {e}")
        return jsonify({"error": "Error interno al obtener proyectos"}), 500


# --- Rutas de la API de Chat (Protegidas) ---
@app.route('/api/conversations', methods=['GET'])
@login_required
def get_conversations():
    user_id = session['user_id']
    limit, offset = _parse_paging_args(default_limit=30, max_limit=200)
    conversations = db.get_user_conversations(user_id, limit=limit + 1, skip=offset)
    has_more = len(conversations) > limit
    conversations = conversations[:limit]
    return jsonify({"conversations": conversations, "has_more": has_more, "limit": limit, "offset": offset})

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
@login_required
def get_conversation(conversation_id):
    limit, offset = _parse_paging_args(default_limit=50, max_limit=200)
    conversation = db.get_conversation_with_messages(
        conversation_id,
        limit=limit + 1,
        skip=offset,
        newest_first=True
    )
    if not conversation or conversation.get('user_id') != session['user_id']:
        return jsonify({"error": "Conversación no encontrada o no autorizada"}), 404
    conversation['messages'] = conversation.get('messages') or []
    has_more = len(conversation['messages']) > limit
    if has_more:
        conversation['messages'] = conversation['messages'][:limit]
    conversation['messages'].reverse()
    conversation['has_more_messages'] = has_more
    conversation['limit'] = limit
    conversation['offset'] = offset
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
    prompt, conversation_id_str, file = _extract_request_data()
    user_id = session['user_id']
    
    if not prompt and not file:
        return jsonify({"error": "Falta el parámetro 'prompt'"}), 400

    try:
        if not conversation_id_str:
            title_source = prompt or (file.filename if file else "Nueva Conversación")
            title = title_source[:50] + "..." if len(title_source) > 50 else title_source
            conversation_id_str = db.create_conversation(user_id, title)
            if not conversation_id_str:
                return jsonify({"error": "No se pudo crear la conversación. Verifica la conexión a la base de datos."}), 503

        try:
            conversation_id = ObjectId(conversation_id_str)
        except InvalidId:
            return jsonify({"error": "conversation_id inválido"}), 400

        user_message = prompt or (f"Archivo adjunto: {file.filename}" if file else "")
        if user_message:
            db.save_message(conversation_id, 'user', user_message)
        if file:
            response_text = ai_model.generate_with_file(prompt, file)
        else:
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
    prompt, conversation_id_str, file = _extract_request_data()
    
    if (not prompt and not file) or not conversation_id_str:
        return jsonify({"error": "Faltan 'prompt' o 'conversation_id'"}), 400

    def generate():
        full_response = ""
        try:
            try:
                conversation_id = ObjectId(conversation_id_str)
            except InvalidId:
                yield "Error: conversation_id inválido"
                return

            user_message = prompt or (f"Archivo adjunto: {file.filename}" if file else "")
            if user_message:
                db.save_message(conversation_id, 'user', user_message)
            
            stream = ai_model.generate_stream_with_file(prompt, file) if file else ai_model.generate_stream(prompt)
            for chunk in stream:
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

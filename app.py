from flask import Flask, render_template, request, jsonify, session, Response, redirect, url_for, send_from_directory, make_response
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth
from model.model import WebDevAI
from model.database import ChatDatabase
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from functools import wraps
import secrets
import os
import time
import json
from datetime import timedelta
from urllib.parse import urlparse
from bson.objectid import ObjectId
from bson.errors import InvalidId


def _is_trusted_proxy_hosting():
    """Vercel, Render, etc. send X-Forwarded-*; needed for correct https URLs and OAuth redirect_uri."""
    return (
        os.getenv("VERCEL", "").strip() == "1"
        or os.getenv("TRUST_PROXY", "").strip().lower() in ("1", "true", "yes")
    )


def _is_production_like():
    """HTTPS-only cookies and stricter session expectations."""
    return (
        os.getenv("FLASK_ENV", "").strip().lower() == "production"
        or os.getenv("VERCEL", "").strip() == "1"
    )


app = Flask(__name__, template_folder='web/templates', static_folder='web/static')
_secret_from_env = os.getenv("SECRET_KEY", "").strip()
if _secret_from_env:
    app.secret_key = _secret_from_env
else:
    app.secret_key = secrets.token_hex(16)

# Production / Vercel: a random secret per process breaks signed session cookies (login → /chat → landing).
if not _secret_from_env and _is_production_like():
    raise RuntimeError(
        "SECRET_KEY must be set when FLASK_ENV=production or on Vercel (VERCEL=1). "
        "Without a stable value, Flask cannot verify the session on the next request, so /chat redirects back to /."
    )

if _is_trusted_proxy_hosting():
    # So request.scheme / url_for(..., _external=True) match the browser (https://…)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

if _is_production_like():
    app.config["PREFERRED_URL_SCHEME"] = "https"

# region agent log
_DEBUG_LOG_PATH = os.path.join(os.path.dirname(__file__), ".cursor", "debug.log")


def _debug_log_app(location, message, data=None, runId="debug", hypothesisId=None):
    """
    NDJSON logger for debug mode.
    IMPORTANT: never log secrets (passwords, tokens, full URIs with creds).
    """
    try:
        payload = {
            "id": f"log_{int(time.time() * 1000)}_{secrets.token_hex(4)}",
            "timestamp": int(time.time() * 1000),
            "location": location,
            "message": message,
            "data": data or {},
            "runId": runId,
        }
        if hypothesisId:
            payload["hypothesisId"] = hypothesisId
        os.makedirs(os.path.dirname(_DEBUG_LOG_PATH), exist_ok=True)
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        # Never fail app due to logging
        pass
# endregion

# OAuth GitHub (opcional: requiere GITHUB_CLIENT_ID y GITHUB_CLIENT_SECRET en .env)
oauth = OAuth(app)
github_client_id = os.getenv('GITHUB_CLIENT_ID', '').strip()
github_client_secret = os.getenv('GITHUB_CLIENT_SECRET', '').strip()
if github_client_id and github_client_secret:
    oauth.register(
        name='github',
        client_id=github_client_id,
        client_secret=github_client_secret,
        access_token_url='https://github.com/login/oauth/access_token',
        authorize_url='https://github.com/login/oauth/authorize',
        api_base_url='https://api.github.com/',
        client_kwargs={'scope': 'read:user user:email'}
    )

# Configuración de CORS más específica si es necesario, pero esto funciona para desarrollo
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = _is_production_like()
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Configuración de CORS restringida
allowed_origins = os.getenv('CORS_ORIGINS', 'http://localhost:4000,http://127.0.0.1:4000').split(',')
CORS(app, origins=[o.strip() for o in allowed_origins], supports_credentials=True)

# Inicializar servicios
ai_model = WebDevAI()
db = ChatDatabase()


def _no_store_redirect(location):
    """Auth-related redirects must not be cached at the edge (stale 302 → wrong page after login)."""
    r = redirect(location)
    r.headers["Cache-Control"] = "no-store, private"
    r.headers["Pragma"] = "no-cache"
    return r


@app.after_request
def _no_store_auth_post_responses(response):
    if request.method == "POST" and request.path in ("/login", "/register", "/forgot-password"):
        response.headers.setdefault("Cache-Control", "no-store, private")
        response.headers.setdefault("Pragma", "no-cache")
    return response


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
    """Extrae prompt, conversation_id y archivo. Si hay archivo, lo lee YA en memoria (evita stream cerrado en streaming)."""
    if request.is_json:
        data = request.get_json(silent=True) or {}
        prompt = data.get('prompt')
        conversation_id = data.get('conversation_id')
        file_bytes = None
        file_filename = None
        file_mimetype = None
    else:
        prompt = request.form.get('prompt')
        conversation_id = request.form.get('conversation_id')
        uploaded_file = request.files.get('file')
        file_bytes = None
        file_filename = None
        file_mimetype = None
        if uploaded_file:
            try:
                file_bytes = uploaded_file.read()
                file_filename = uploaded_file.filename or "archivo"
                file_mimetype = uploaded_file.mimetype or ""
                if file_bytes is None:
                    file_bytes = b""
                elif isinstance(file_bytes, str):
                    file_bytes = file_bytes.encode("utf-8", errors="replace")
                else:
                    file_bytes = bytes(file_bytes)
            except Exception as e:
                print(f"Error leyendo archivo adjunto en request: {e}")
                file_bytes = None
                file_filename = None
                file_mimetype = None
    return (prompt or '').strip(), conversation_id, file_bytes, file_filename, file_mimetype


def _prepare_generation_context(conversation_id_str, user_id):
    try:
        conversation_id = ObjectId(conversation_id_str)
    except InvalidId:
        return None, None, jsonify({"error": "conversation_id inválido"}), 400

    owner = db.get_conversation_user_id(conversation_id)
    if not _user_ids_match(owner, user_id):
        return None, None, jsonify({"error": "Conversación no encontrada o no autorizada"}), 404

    history_tail = db.get_conversation_history_tail(
        conversation_id_str, limit=WebDevAI.MAX_GEMINI_HISTORY_MESSAGES
    )
    return conversation_id, history_tail, None, None


def _user_ids_match(stored_user_id, session_user_id):
    """True si el user_id de Mongo (str u ObjectId) coincide con session['user_id'] (str)."""
    if stored_user_id is None or session_user_id is None:
        return False
    return str(stored_user_id) == str(session_user_id)


# --- Decorador para rutas protegidas ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({"error": "Autenticación requerida"}), 401
            return _no_store_redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# --- Rutas de Autenticación y Vistas ---
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(app.static_folder, 'favicon.svg', mimetype='image/svg+xml')


@app.route('/')
def index():
    """
    Muestra la página de inicio (login.html) si el usuario no está en sesión.
    Si ya está logueado, lo redirige al chat.
    """
    if 'user_id' in session:
        return _no_store_redirect(url_for('chat'))
    # Esta es la página que contiene el carrusel
    return render_template('login.html')

@app.route('/chat')
@login_required
def chat():
    """
    Ruta principal de la aplicación de chat (index.html), protegida por login.
    """
    r = make_response(render_template('index.html'))
    r.headers['Cache-Control'] = 'no-store, private'
    r.headers['Pragma'] = 'no-cache'
    return r

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email y contraseña son requeridos"}), 400

    if not db._ensure_connection():
        return jsonify({"error": "Servicio no disponible. Intenta más tarde."}), 503

    try:
        user = db.get_user_by_email(email)
    except Exception as e:
        # Fallback safety: never crash login on DB selection errors
        print(f"Error en login (DB): {e}")
        return jsonify({"error": "Servicio no disponible. Intenta más tarde."}), 503

    if not user or not user.get('password'):
        return jsonify({"error": "Credenciales inválidas"}), 401
    if check_password_hash(user['password'], password):
        session.permanent = True
        session['user_id'] = str(user['_id'])
        session['user_email'] = user['email']
        session.modified = True
        return jsonify({"message": "Inicio de sesión exitoso"}), 200

    return jsonify({"error": "Credenciales inválidas"}), 401

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email y contraseña son requeridos"}), 400

    if len(password) < 8:
        return jsonify({"error": "La contraseña debe tener al menos 8 caracteres"}), 400

    if not db._ensure_connection():
        return jsonify({"error": "Servicio no disponible. Intenta más tarde."}), 503

    if db.get_user_by_email(email):
        return jsonify({"error": "El email ya está registrado"}), 409

    hashed_password = generate_password_hash(password)
    user_id = db.create_user(email, hashed_password)
    if not user_id:
        return jsonify({"error": "No se pudo crear la cuenta. Verifica la conexión a la base de datos."}), 503

    session.permanent = True
    session['user_id'] = user_id
    session['user_email'] = email
    session.modified = True

    return jsonify({"message": "Registro exitoso", "user_id": user_id}), 201

@app.route('/logout')
def logout():
    session.clear()
    return _no_store_redirect(url_for('index'))


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


def _github_oauth_redirect_uri():
    """
    Exact callback URL sent to GitHub (authorize + token exchange must match).
    Prefer GITHUB_REDIRECT_URI or PUBLIC_BASE_URL on Vercel so it never depends on proxy headers alone.
    """
    env_redirect_uri = (os.getenv("GITHUB_REDIRECT_URI") or "").strip()
    if env_redirect_uri:
        return env_redirect_uri
    env_base_url = (os.getenv("PUBLIC_BASE_URL") or "").strip()
    if env_base_url:
        return env_base_url.rstrip("/") + "/auth/github/callback"
    return url_for("auth_github_callback", _external=True)


@app.route('/auth/github')
def auth_github():
    """Redirige a GitHub para iniciar sesión con OAuth."""
    if not github_client_id or not github_client_secret:
        return _no_store_redirect(url_for('index') + '?error=github_not_configured')
    redirect_uri = _github_oauth_redirect_uri()
    if (os.getenv("GITHUB_REDIRECT_URI") or "").strip():
        redirect_source = "GITHUB_REDIRECT_URI"
    elif (os.getenv("PUBLIC_BASE_URL") or "").strip():
        redirect_source = "PUBLIC_BASE_URL"
    else:
        redirect_source = "url_for(_external=True)"

    try:
        p = urlparse(redirect_uri)
        redirect_uri_safe = f"{p.scheme}://{p.netloc}{p.path}"
    except Exception:
        redirect_uri_safe = "<unparseable>"
    _debug_log_app(
        location="app.py:auth_github",
        message="GitHub OAuth authorize_redirect",
        data={
            "has_github_client_id": bool(github_client_id),
            "has_github_client_secret": bool(github_client_secret),
            "redirect_uri": redirect_uri_safe,
            "redirect_source": redirect_source,
        },
        runId="debug1",
        hypothesisId="A",
    )
    return oauth.github.authorize_redirect(redirect_uri)


@app.route('/auth/github/callback')
def auth_github_callback():
    """Callback de GitHub OAuth: crea o obtiene usuario y deja sesión iniciada."""
    if not github_client_id or not github_client_secret:
        return _no_store_redirect(url_for('index'))
    _debug_log_app(
        location="app.py:auth_github_callback",
        message="GitHub OAuth callback hit",
        data={
            "args_keys": sorted(list(request.args.keys())),
            "error": request.args.get("error"),
        },
        runId="debug1",
        hypothesisId="D",
    )
    try:
        token = oauth.github.authorize_access_token(redirect_uri=_github_oauth_redirect_uri())
        # GitHub no devuelve userinfo en el token; hay que pedirlo a la API
        resp = oauth.github.get('/user', token=token)
        user_info = resp.json() if resp else {}
        github_id = str(user_info.get('id', ''))
        name = user_info.get('name') or user_info.get('login') or ''
        email = (user_info.get('email') or '').strip().lower()
        # Si el email no está público, pedirlo al endpoint de emails
        if not email:
            try:
                emails_resp = oauth.github.get('/user/emails', token=token)
                if emails_resp:
                    for e in (emails_resp.json() or []):
                        if e.get('primary') and e.get('verified'):
                            email = (e.get('email') or '').strip().lower()
                            break
                        if not email and e.get('verified'):
                            email = (e.get('email') or '').strip().lower()
            except Exception:
                pass
        if not github_id:
            return _no_store_redirect(url_for('index') + '?error=invalid_github_user')
        if not email:
            return _no_store_redirect(url_for('index') + '?error=github_email_required')
        if not db._ensure_connection():
            return _no_store_redirect(url_for('index') + '?error=service_unavailable')
        user = db.get_user_by_github_id(github_id)
        if not user:
            user = db.get_user_by_email(email)
            if user:
                db.link_github_to_user(str(user['_id']), github_id, name)
                user_id = str(user['_id'])
            else:
                user_id = db.create_github_user(email, github_id, name)
                if not user_id:
                    return _no_store_redirect(url_for('index') + '?error=create_failed')
        else:
            user_id = str(user['_id'])
        session.permanent = True
        session['user_id'] = user_id
        session['user_email'] = email
        session.modified = True
        return _no_store_redirect(url_for('chat'))
    except Exception as e:
        print(f"GitHub OAuth error: {e}")
        return _no_store_redirect(url_for('index') + '?error=oauth_failed')


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

@app.route('/api/conversations', methods=['POST'])
@login_required
def create_conversation():
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or "Nueva Conversación").strip()
    if not title:
        title = "Nueva Conversación"
    if len(title) > 80:
        title = title[:80]
    conversation_id = db.create_conversation(session['user_id'], title)
    if not conversation_id:
        return jsonify({"error": "No se pudo crear la conversación"}), 503
    return jsonify({"conversation_id": conversation_id, "title": title}), 201

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
    if not conversation or not _user_ids_match(conversation.get('user_id'), session.get('user_id')):
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
    prompt, conversation_id_str, file_bytes, file_filename, file_mimetype = _extract_request_data()
    user_id = session['user_id']
    
    if not prompt and file_bytes is None:
        return jsonify({"error": "Falta el parámetro 'prompt'"}), 400

    try:
        if not conversation_id_str:
            title_source = prompt or (file_filename if file_filename else "Nueva Conversación")
            title = title_source[:50] + "..." if len(title_source) > 50 else title_source
            conversation_id_str = db.create_conversation(user_id, title)
            if not conversation_id_str:
                return jsonify({"error": "No se pudo crear la conversación. Verifica la conexión a la base de datos."}), 503

        conversation_id, history_tail, error_response, error_code = _prepare_generation_context(conversation_id_str, user_id)
        if error_response:
            return error_response, error_code

        user_message = prompt or (f"Archivo adjunto: {file_filename}" if file_filename else "")
        if user_message:
            db.save_message(conversation_id, 'user', user_message)
        if file_bytes is not None:
            response_text = ai_model.generate_with_file(
                prompt,
                file_bytes=file_bytes,
                filename=file_filename,
                mimetype=file_mimetype,
                history_messages=history_tail,
            )
        else:
            response_text = ai_model.generate(prompt, history_messages=history_tail)
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
    prompt, conversation_id_str, file_bytes, file_filename, file_mimetype = _extract_request_data()
    user_id = session['user_id']

    if (not prompt and file_bytes is None) or not conversation_id_str:
        return jsonify({"error": "Faltan 'prompt' o 'conversation_id'"}), 400

    def generate():
        full_response = ""
        try:
            conversation_id, history_tail, error_response, error_code = _prepare_generation_context(conversation_id_str, user_id)
            if error_response:
                try:
                    payload = error_response.get_json(silent=True) or {}
                    yield f"Error: {payload.get('error', 'Error interno del servidor')}"
                except Exception:
                    yield "Error: No se pudo procesar la solicitud."
                return

            user_message = prompt or (f"Archivo adjunto: {file_filename}" if file_filename else "")
            if user_message:
                db.save_message(conversation_id, 'user', user_message)

            if file_bytes is not None:
                stream = ai_model.generate_stream_with_file(
                    prompt,
                    file_bytes=file_bytes,
                    filename=file_filename,
                    mimetype=file_mimetype,
                    history_messages=history_tail,
                )
            else:
                stream = ai_model.generate_stream(prompt, history_messages=history_tail)
            for chunk in stream:
                full_response += chunk
                yield chunk

            db.save_message(conversation_id, 'bot', full_response)
        except Exception as e:
            print(f"Error en streaming: {e}")
            yield "Error: No se pudo completar la respuesta. Inténtalo de nuevo."
    
    return Response(generate(), mimetype='text/plain')

if __name__ == '__main__':
    # Asegúrate de que 'host' sea '0.0.0.0' si necesitas acceder desde otros dispositivos en la red
    app.run(debug=True, host='0.0.0.0', port=4000)

## WebDevAI — Flask + Gemini + MongoDB

Aplicación web full‑stack que combina:

- **Landing pública** (`/`) con login/registro y un carrusel de **Proyectos Destacados**
- **Chat protegido** (`/chat`) que conversa con **Gemini** y guarda historial en **MongoDB**
- **Adjuntos** (código/texto/PDF) para dar contexto a la IA (con streaming opcional)

---

## Tabla de contenidos

- [Demo local](#demo-local)
- [Características](#características)
- [Stack](#stack)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Variables de entorno](#variables-de-entorno)
- [Ejecutar en local](#ejecutar-en-local)
- [Poblar proyectos (seed)](#poblar-proyectos-seed)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Endpoints/API](#endpointsapi)
- [Deploy (Render)](#deploy-render)
- [Troubleshooting](#troubleshooting)
- [Seguridad](#seguridad)

---

## Demo local

- **Landing (login + proyectos)**: `http://localhost:4000/`
- **Chat (requiere sesión)**: `http://localhost:4000/chat`

---

## Características

- **Autenticación**
  - Login/registro con email + contraseña (hash con Werkzeug)
  - **Google OAuth opcional** (si configuras credenciales)
  - Sesión con cookies de Flask (`SECRET_KEY`)
- **Chat con IA (Gemini)**
  - Respuestas normales (`/api/generate`)
  - **Streaming** (`/api/generate-stream`)
  - Adjuntar archivos (texto/código y PDF)
    - Texto/código: se incrusta en el prompt como bloque Markdown
    - PDF: intenta extraer texto; si no, sube el archivo a Gemini como fallback
- **MongoDB**
  - Guarda usuarios, conversaciones, mensajes y proyectos
  - Carrusel de proyectos en la landing consume `/api/projects` (público)

---

## Stack

- **Backend**: Python + Flask, Flask-CORS, Authlib (Google OAuth)
- **IA**: `google-generativeai` (modelo configurado en `model/model.py`)
- **DB**: MongoDB (PyMongo + dnspython para `mongodb+srv://`)
- **Frontend**: HTML/CSS/JS (templates en `web/templates/`)
  - Carrusel: Swiper (CDN)
  - Highlight: highlight.js (CDN)

---

## Requisitos

- **Python 3.10+** (recomendado)
- **MongoDB**:
  - Local (`mongodb://localhost:27017/`) o
  - Atlas (`mongodb+srv://...`)
- Una **API key de Gemini** (variable `GEMINI_API_KEY`)

---

## Instalación

1) Crear y activar entorno virtual.

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS/Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

2) Instalar dependencias:

```bash
pip install -r requirements.txt
```

---

## Variables de entorno

Este proyecto carga variables desde `.env` (ver `config.py`). **No se versiona** (está en `.gitignore`).

Crea un archivo `.env` en la raíz (junto a `app.py`) con algo como:

```dotenv
# Requerido (IA)
GEMINI_API_KEY=tu_api_key_de_gemini

# Requerido (DB) — en local puedes dejar el default
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB_NAME=webdevai

# Recomendado (sesiones Flask)
SECRET_KEY=una_cadena_larga_aleatoria

# Opcional (Google OAuth)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

Notas:

- **`MONGODB_URI`** acepta `mongodb://` o `mongodb+srv://` (Atlas).
- **`SECRET_KEY`**: si no lo defines, la app genera uno temporal en cada arranque (en **Vercel/serverless** esto rompe el login con GitHub: debes definir `SECRET_KEY` en el panel de variables).
- **Google OAuth** solo se registra si `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET` están presentes.

Para generar un `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Ejecutar en local

Desde la raíz del proyecto:

```bash
python app.py
```

Por defecto levanta en:

- `http://0.0.0.0:4000` (accesible como `http://localhost:4000`)

---

## Poblar proyectos (seed)

El carrusel de la landing lee proyectos desde MongoDB (colección `projects`). Para cargar ejemplos:

```bash
python seed.py
```

Esto hace *upsert* por `title` para evitar duplicados y deja los proyectos listos para `/api/projects`.

---

## Estructura del proyecto

```
.
├─ app.py                    # Flask app + rutas (auth, chat, projects)
├─ config.py                 # Carga .env y expone Config (Gemini/Mongo)
├─ requirements.txt
├─ seed.py                   # Pobla proyectos de ejemplo en Mongo
├─ model/
│  ├─ model.py               # Integración con Gemini + adjuntos + streaming
│  └─ database.py            # Acceso a MongoDB (users, conversations, messages, projects)
└─ web/
   ├─ templates/
   │  ├─ login.html          # Landing pública (proyectos + login/registro)
   │  └─ index.html          # UI del chat (protegida)
   └─ static/
      ├─ stylelog.css        # Estilos landing
      ├─ style.css           # Estilos chat
      └─ js/
         ├─ jslog.js         # JS landing (Swiper + fetch de projects)
         └─ script.js        # JS chat (conversaciones, streaming, etc.)
```

---

## Endpoints/API

### Auth / Sesión

- **GET `/`**
  - Si estás logueado: redirige a `/chat`
  - Si no: muestra `login.html`
- **GET `/chat`** *(protegido)*
  - Renderiza `index.html`
- **POST `/login`**
  - Body JSON: `{ "email": "...", "password": "..." }`
- **POST `/register`**
  - Body JSON: `{ "email": "...", "password": "..." }`
- **GET `/logout`**
  - Limpia sesión y vuelve a `/`
- **GET `/api/check_auth`**
  - Devuelve `{ authenticated: true/false, email?: string }`

### GitHub OAuth (opcional)

- **GET `/auth/github`**
- **GET `/auth/github/callback`**

Requiere `GITHUB_CLIENT_ID` y `GITHUB_CLIENT_SECRET`. Añade en GitHub OAuth App la URL de callback indicada abajo.

**Vercel (p. ej. [https://webdevai-blue.vercel.app/](https://webdevai-blue.vercel.app/))**

En **Settings → Environment Variables** define al menos:

| Variable | Ejemplo |
|----------|---------|
| `SECRET_KEY` | **Obligatorio** en Vercel / `FLASK_ENV=production`: misma clave en todos los arranques (p. ej. `python -c "import secrets; print(secrets.token_hex(32))"`). Sin esto, la cookie de sesión no se valida entre instancias: tras login te devuelve al landing en lugar de `/chat`, y GitHub OAuth también falla. |
| `PUBLIC_BASE_URL` | `https://webdevai-blue.vercel.app` (sin barra final) **o** |
| `GITHUB_REDIRECT_URI` | `https://webdevai-blue.vercel.app/auth/github/callback` (debe coincidir **exactamente** con la callback en GitHub) |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | Credenciales de la OAuth App |

En GitHub → **Settings → Developer settings → OAuth Apps** → tu app → **Authorization callback URL** debe ser exactamente:

`https://webdevai-blue.vercel.app/auth/github/callback`

La app activa `ProxyFix` cuando `VERCEL=1` para que las URLs públicas usen `https` detrás del proxy.

### Proyectos (landing)

- **GET `/api/projects`** *(público)*
  - Query params: `limit`, `offset`
  - Respuesta: `{ projects: [...], has_more, limit, offset }`

### Chat (protegido)

- **GET `/api/conversations`**
  - Query params: `limit`, `offset`
- **GET `/api/conversations/<conversation_id>`**
  - Query params: `limit`, `offset`
- **DELETE `/api/conversations/<conversation_id>`**
- **POST `/api/generate`**
  - Acepta JSON o `multipart/form-data` (para adjuntos)
  - Crea conversación si no hay `conversation_id`
- **POST `/api/generate-stream`**
  - Igual que generate, pero responde en streaming (texto plano)

---

## Deploy (Render)

Hay una guía específica en `RENDER.md` (MongoDB Atlas + variables de entorno).

Checklist rápido:

- Atlas → **Network Access** → permitir `0.0.0.0/0`
- Render → **Environment**:
  - `MONGODB_URI`, `MONGODB_DB_NAME`, `GEMINI_API_KEY`, `SECRET_KEY`
- Si usas contraseña con caracteres especiales en MongoDB URI, **URL‑encode**.

---

## Troubleshooting

### No conecta a MongoDB Atlas (timeouts / DNS)

- Revisa Network Access en Atlas, la URI en variables de entorno y que la contraseña esté URL‑encodeada.
- En Windows, si tu red/ISP provoca fallos resolviendo `mongodb+srv://`, revisa DNS o añade al archivo `hosts` los hostnames que Atlas indica para tu cluster (solo si tu proveedor lo recomienda).

### “GEMINI_API_KEY no encontrada”

- Crea `.env` en la raíz y añade `GEMINI_API_KEY=...`.
- Reinicia la app.

### Vercel: “No flask entrypoint found”

- El runtime importa el proyecto para localizar la variable Flask ``app``. Si el módulo **falla al importar** (por ejemplo un ``RuntimeError`` al cargar), Vercel muestra este mensaje aunque exista ``app.py``.
- Asegura **raíz del proyecto en Vercel** = carpeta donde están ``app.py`` / ``wsgi.py`` y ``requirements.txt`` (no un subdirectorio equivocado).
- Hay un **`wsgi.py`** que reexporta ``app`` por si el detector prioriza ``wsgi:app``.
- Si tienes **`pyproject.toml`** vacío o a medias, Vercel puede usar **uv** y dejar de instalar bien las deps; o bien completa dependencias en `pyproject.toml`, o evita el conflicto (por ejemplo no versionar un `pyproject.toml` a medias, o ver la nota de Vercel sobre `requirements.txt` vs uv).

---

## Seguridad

- **No subas tu `.env`** (está en `.gitignore`).
- Rota credenciales si se filtraron (MongoDB URI, Gemini API key, OAuth).
- En producción, define un `SECRET_KEY` estable y fuerte.

---

## Producción (Gunicorn)

`gunicorn` está incluido en `requirements.txt` y se usa típicamente en Linux (por ejemplo, Render).

Ejemplo de comando (Linux):

```bash
gunicorn app:app --bind 0.0.0.0:${PORT:-4000}
# o, explícito con wsgi.py:
gunicorn wsgi:app --bind 0.0.0.0:${PORT:-4000}
```

Notas:

- En **Windows**, `gunicorn` normalmente **no funciona**. Para producción en Windows, usa un servidor WSGI compatible (por ejemplo Waitress) o despliega en Linux.
- El `app.run(...)` de `app.py` está pensado para **desarrollo local**.

---

## Contribuir

- Abre un issue con el cambio propuesto.
- Si vas a tocar frontend, revisa `web/templates/` y `web/static/`.
- Si vas a tocar backend, revisa rutas en `app.py` y persistencia en `model/database.py`.

---

## Licencia

Este repositorio **no incluye una licencia** en este momento. Si quieres permitir uso/redistribución, añade un archivo `LICENSE` (por ejemplo MIT).


# Desplegar en Render.com y conectar con MongoDB Atlas

Si Render **no conecta** con tu cluster de MongoDB Atlas, revisa estos puntos en orden.

---

## 1. Red en MongoDB Atlas (lo más habitual)

Render usa IPs que cambian. Atlas por defecto solo permite IPs que tú añades.

1. Entra en [MongoDB Atlas](https://cloud.mongodb.com) → tu proyecto → **Network Access** (menú izquierda).
2. Pulsa **Add IP Address**.
3. Elige **Allow access from anywhere** (añade `0.0.0.0/0`).
4. Confirma con **Confirm**.

Sin esto, la conexión desde Render suele fallar por tiempo de espera.

---

## 2. Variables de entorno en Render

En tu servicio de Render:

1. **Dashboard** → tu Web Service → **Environment**.
2. Añade (o revisa) estas variables:

| Variable          | Valor |
|-------------------|--------|
| `MONGODB_URI`     | Tu URI completa de Atlas (ej. `mongodb+srv://usuario:password@cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority`) |
| `MONGODB_DB_NAME` | Nombre de la base de datos (ej. `DataforAI`) |
| `GEMINI_API_KEY`  | Tu clave de la API de Gemini |
| `SECRET_KEY`      | Una cadena aleatoria larga para sesiones (ej. genera una con Python: `python -c "import secrets; print(secrets.token_hex(32))"`) |

**Importante:** Si la contraseña de MongoDB tiene caracteres especiales (`@`, `#`, `:`, etc.), hay que codificarla en URL (por ejemplo `@` → `%40`). Puedes generar la URI desde Atlas: **Connect** → **Drivers** → copia la cadena y reemplaza `<password>` por tu contraseña ya codificada.

---

## 3. Región del cluster

Para menos latencia:

- Crea (o usa) un cluster de Atlas en **AWS** y en una región cercana a la de tu servicio en Render (por ejemplo mismo país/continente).
- En Render puedes ver la región en la configuración del servicio.

---

## 4. Dependencia `dnspython`

Este proyecto ya incluye **dnspython** en `requirements.txt`. PyMongo la usa para resolver correctamente las URIs `mongodb+srv://` en entornos como Render.

Si desplegaste antes de añadirla, haz un **redeploy** en Render para que instale de nuevo las dependencias.

---

## 5. Comprobar la conexión

Tras un deploy:

1. Abre los **Logs** del servicio en Render.
2. Si la conexión va bien deberías ver algo como: `Conexión exitosa a MongoDB`.
3. Si falla, verás el mensaje de error de PyMongo (timeout, DNS, auth, etc.).

Errores típicos:

- **Timeout / "connection refused"** → Revisa **Network Access** en Atlas (paso 1) y que `MONGODB_URI` esté bien en Render.
- **Authentication failed** → Usuario/contraseña incorrectos o contraseña con caracteres especiales sin codificar en la URI.
- **DNS / resolution** → Asegúrate de que `dnspython` está en `requirements.txt` y que Render ha hecho un deploy reciente.

---

## Resumen rápido

1. Atlas → **Network Access** → **Allow access from anywhere** (`0.0.0.0/0`).
2. Render → **Environment** → `MONGODB_URI`, `MONGODB_DB_NAME`, `GEMINI_API_KEY`, `SECRET_KEY`.
3. Contraseña con caracteres raros → codificada en la URI.
4. Redeploy en Render si acabas de añadir `dnspython` o cambiar variables.

Si tras esto sigue sin conectar, copia el mensaje de error exacto de los logs de Render y revísalo (Atlas también muestra intentos de conexión bloqueados en Network Access).

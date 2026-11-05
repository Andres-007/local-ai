import hashlib
import logging
import os
import re
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Configurar entorno de pruebas antes de importar app
os.environ["FLASK_ENV"] = "development"
os.environ["TRUST_PROXY"] = "0"
os.environ["MONGODB_SERVER_SELECTION_TIMEOUT_MS"] = "1000"
os.environ["MONGODB_CONNECT_TIMEOUT_MS"] = "1000"
os.environ["MONGODB_SOCKET_TIMEOUT_MS"] = "1000"

import app as app_module
from model.database import ChatDatabase, _resolve_mongodb_srv_via_nslookup
from model.model import WebDevAI, _sanitize_filename, _safe_suffix
from werkzeug.security import generate_password_hash


class SecurityAuditTests(unittest.TestCase):
    def setUp(self):
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()
        app_module._RATE_BUCKETS.clear()

    def _get_csrf_token(self):
        """Obtiene el token CSRF desde la sesión tras cargar la página inicial."""
        self.client.get("/")
        with self.client.session_transaction() as sess:
            return sess.get("_csrf_token")

    # 1. Prueba de vulnerabilidad: SECRET_KEY no debe reutilizar GEMINI_API_KEY ni usar secreto público fijo
    def test_01_secret_key_not_using_gemini_key_or_public_hardcoded_string(self):
        public_fallback = "webdevia-production-serverless-secret-2026"
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.assertNotEqual(
            app_module.app.secret_key,
            public_fallback,
            "VULNERABILIDAD: app.secret_key usa un string público hardcodeado en el repositorio.",
        )
        if gemini_key:
            self.assertNotEqual(
                app_module.app.secret_key,
                gemini_key,
                "VULNERABILIDAD: app.secret_key reutiliza directamente GEMINI_API_KEY.",
            )

    # 2. Prueba de vulnerabilidad: Rate limit bypass mediante falsificación de X-Forwarded-For
    @patch.object(app_module.db, "_ensure_connection", return_value=True)
    @patch.object(app_module.db, "get_user_by_email", return_value=None)
    def test_02_rate_limit_cannot_be_bypassed_via_x_forwarded_for_spoofing(self, _mock_user, _mock_conn):
        csrf = self._get_csrf_token()
        headers_base = {"X-CSRFToken": csrf, "Content-Type": "application/json"}

        statuses = []
        for i in range(12):
            headers = dict(headers_base)
            headers["X-Forwarded-For"] = f"203.0.113.{i}"
            res = self.client.post(
                "/login",
                json={"email": "test@example.com", "password": "wrongpassword"},
                headers=headers,
            )
            statuses.append(res.status_code)

        self.assertIn(
            429,
            statuses,
            f"VULNERABILIDAD: El rate-limit de /login fue evadido falsificando X-Forwarded-For (estados={statuses}).",
        )

    # 3. Prueba de vulnerabilidad: /reset-password debe tener Rate Limiting
    @patch.object(app_module.db, "reset_password_with_token", return_value=False)
    def test_03_reset_password_is_rate_limited(self, _mock_reset):
        csrf = self._get_csrf_token()
        headers = {"X-CSRFToken": csrf, "Content-Type": "application/json"}
        statuses = []
        for _ in range(10):
            res = self.client.post(
                "/reset-password",
                json={"token": "invalid-token", "password": "newpassword123"},
                headers=headers,
            )
            statuses.append(res.status_code)

        self.assertIn(
            429,
            statuses,
            "VULNERABILIDAD: /reset-password no tiene rate limiting contra fuerza bruta.",
        )

    # 4. Prueba de vulnerabilidad: Inyección de tipos JSON / NoSQL (objetos/listas en vez de strings)
    @patch.object(app_module.db, "_ensure_connection", return_value=True)
    def test_04_json_type_confusion_and_nosql_payloads_return_400_not_500(self, _mock_conn):
        csrf = self._get_csrf_token()
        headers = {"X-CSRFToken": csrf, "Content-Type": "application/json"}

        payloads = [
            ("/login", {"email": {"$ne": ""}, "password": "password123"}),
            ("/login", {"email": "user@example.com", "password": ["a", "b", "c", "d", "e", "f", "g", "h"]}),
            ("/register", {"email": ["user@example.com"], "password": "password123"}),
            ("/register", {"email": "user@example.com", "password": {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6, "g": 7, "h": 8}}),
            ("/forgot-password", {"email": {"$gt": ""}}),
            ("/reset-password", {"token": {"$exists": True}, "password": "password123"}),
        ]
        for endpoint, body in payloads:
            app_module._RATE_BUCKETS.clear()
            res = self.client.post(endpoint, json=body, headers=headers)
            self.assertEqual(
                res.status_code,
                400,
                f"VULNERABILIDAD en {endpoint} con payload {body}: devolvió {res.status_code} en lugar de 400.",
            )

    # 5. Prueba de vulnerabilidad: DoS por contraseñas gigantes (PBKDF2/scrypt CPU exhaustion) y email inválido
    @patch.object(app_module.db, "_ensure_connection", return_value=True)
    @patch.object(app_module.db, "get_user_by_email", return_value=None)
    def test_05_password_max_length_and_email_validation(self, _mock_user, _mock_conn):
        csrf = self._get_csrf_token()
        headers = {"X-CSRFToken": csrf, "Content-Type": "application/json"}

        huge_password = "A" * 5000
        res = self.client.post(
            "/register",
            json={"email": "valid@example.com", "password": huge_password},
            headers=headers,
        )
        self.assertEqual(
            res.status_code,
            400,
            "VULNERABILIDAD: /register permite contraseñas de miles de caracteres (riesgo de CPU DoS en hash).",
        )

        res_bad_email = self.client.post(
            "/register",
            json={"email": "not-an-email", "password": "validPassword123"},
            headers=headers,
        )
        self.assertEqual(
            res_bad_email.status_code,
            400,
            "VULNERABILIDAD: /register acepta emails sin formato válido.",
        )

    # 6. Prueba de vulnerabilidad: Fuga de token de recuperación en logs y almacenamiento en texto plano
    @patch.object(app_module.db, "get_user_by_email", return_value={"_id": "507f1f77bcf86cd799439011", "email": "victim@example.com"})
    @patch.object(app_module.db, "create_password_reset_token", return_value=True)
    def test_06_forgot_password_does_not_leak_token_in_logs(self, mock_create_token, _mock_user):
        csrf = self._get_csrf_token()
        headers = {"X-CSRFToken": csrf, "Content-Type": "application/json"}

        with self.assertLogs(app_module.logger, level="INFO") as cm:
            app_module.logger.info("test_marker")
            self.client.post(
                "/forgot-password",
                json={"email": "victim@example.com"},
                headers=headers,
            )

        self.assertTrue(mock_create_token.called)
        passed_token = mock_create_token.call_args[0][1]
        logged_output = "\n".join(cm.output)
        self.assertNotIn(
            passed_token,
            logged_output,
            "VULNERABILIDAD: El token de restablecimiento de contraseña se escribe en texto plano en los logs.",
        )

    # 7. Prueba de vulnerabilidad: Almacenamiento del reset_token con hash en MongoDB y bloqueo NoSQL
    def test_07_database_hashes_reset_token_and_blocks_nosql_dict_token(self):
        db_inst = ChatDatabase.__new__(ChatDatabase)
        db_inst.client = MagicMock()
        db_inst.users = MagicMock()

        raw_token = "secret-reset-token-12345"
        db_inst.create_password_reset_token("victim@example.com", raw_token, "2099-01-01")
        self.assertTrue(db_inst.users.update_one.called)
        update_doc = db_inst.users.update_one.call_args[0][1]["$set"]
        stored_token = update_doc.get("reset_token")
        self.assertNotEqual(
            stored_token,
            raw_token,
            "VULNERABILIDAD: create_password_reset_token guarda el token en texto plano en MongoDB en lugar de su hash SHA-256.",
        )
        self.assertEqual(stored_token, hashlib.sha256(raw_token.encode("utf-8")).hexdigest())

        db_inst.users.find_one.reset_mock()
        result = db_inst.reset_password_with_token({"$exists": True}, "new_hash")
        self.assertFalse(result)
        self.assertFalse(
            db_inst.users.find_one.called,
            "VULNERABILIDAD: reset_password_with_token ejecuta find_one con un dict (NoSQL Injection).",
        )

    # 8. Prueba de vulnerabilidad: Cabeceras de seguridad HTTP (CSP, X-Frame-Options, nosniff)
    def test_08_security_headers_present(self):
        res = self.client.get("/")
        self.assertEqual(
            res.headers.get("X-Content-Type-Options"),
            "nosniff",
            "VULNERABILIDAD: Falta cabecera X-Content-Type-Options: nosniff.",
        )
        self.assertIn(
            res.headers.get("X-Frame-Options"),
            ("DENY", "SAMEORIGIN"),
            "VULNERABILIDAD: Falta cabecera X-Frame-Options contra Clickjacking.",
        )
        self.assertIsNotNone(
            res.headers.get("Content-Security-Policy"),
            "VULNERABILIDAD: Falta cabecera Content-Security-Policy.",
        )
        self.assertIsNotNone(
            res.headers.get("Referrer-Policy"),
            "VULNERABILIDAD: Falta cabecera Referrer-Policy.",
        )

    # 9. Prueba de vulnerabilidad: Validación de hostname en _resolve_mongodb_srv_via_nslookup
    @patch("subprocess.run")
    def test_09_srv_fallback_rejects_malicious_hostnames(self, mock_subproc):
        malicious_uri = "mongodb+srv://user:pass@-malicious-flag.mongodb.net/db"
        res = _resolve_mongodb_srv_via_nslookup(malicious_uri)
        self.assertIsNone(res)
        self.assertFalse(
            mock_subproc.called,
            "VULNERABILIDAD: _resolve_mongodb_srv_via_nslookup invoca subprocess.run con un host que empieza con '-'.",
        )

    # 10. Prueba de vulnerabilidad y bugs críticos en frontend (script.js, jslog.js, templates)
    def test_10_frontend_integrity_and_xss_protections(self):
        root = Path(__file__).resolve().parent.parent
        script_js = (root / "web" / "static" / "js" / "script.js").read_text(encoding="utf-8")
        jslog_js = (root / "web" / "static" / "js" / "jslog.js").read_text(encoding="utf-8")
        index_html = (root / "web" / "templates" / "index.html").read_text(encoding="utf-8")
        login_html = (root / "web" / "templates" / "login.html").read_text(encoding="utf-8")

        self.assertIn(
            "function escapeHtml(",
            script_js,
            "BUG CRÍTICO: escapeHtml() es llamada pero no está definida en script.js.",
        )
        self.assertIn(
            "function renderAttachmentPreview(",
            script_js,
            "BUG CRÍTICO: renderAttachmentPreview() es llamada pero no está definida en script.js.",
        )
        self.assertIn(
            "function formatFileSize(",
            script_js,
            "BUG CRÍTICO: formatFileSize() es llamada pero no está definida en script.js.",
        )
        self.assertIn(
            "conversationsList.appendChild(itemEl)",
            script_js,
            "BUG CRÍTICO: itemEl se crea en displayConversations() pero nunca se añade al DOM con appendChild.",
        )
        self.assertNotIn(
            "allow-forms",
            index_html,
            "VULNERABILIDAD: El iframe de previsualización en index.html permite allow-forms innecesariamente.",
        )
        self.assertNotIn(
            "allow-forms",
            login_html,
            "VULNERABILIDAD: El iframe de previsualización en login.html permite allow-forms innecesariamente.",
        )
        self.assertIn(
            "escapeHtml(safeHttpImageUrl(",
            jslog_js.replace(" ", ""),
            "VULNERABILIDAD: imageUrl en jslog.js no se escapa con escapeHtml antes de insertarse en el atributo src.",
        )

    # 11. Prueba de vulnerabilidad: Prevención de Session Fixation y Logout Cross-Site
    @patch.object(app_module.db, "_ensure_connection", return_value=True)
    def test_11_session_regeneration_and_cross_site_logout_protection(self, _mock_conn):
        initial_csrf = self._get_csrf_token()
        with self.client.session_transaction() as sess:
            sess["attacker_injected_key"] = "malicious"

        pw_hash = generate_password_hash("CorrectHorseBattery1")
        with patch.object(
            app_module.db,
            "get_user_by_email",
            return_value={"_id": "507f1f77bcf86cd799439011", "email": "user@example.com", "password": pw_hash},
        ):
            res = self.client.post(
                "/login",
                json={"email": "user@example.com", "password": "CorrectHorseBattery1"},
                headers={"X-CSRFToken": initial_csrf, "Content-Type": "application/json"},
            )
            self.assertEqual(res.status_code, 200)

        with self.client.session_transaction() as sess:
            self.assertNotIn("attacker_injected_key", sess, "VULNERABILIDAD: La sesión previa no se limpia al iniciar sesión (Session Fixation).")
            self.assertNotEqual(sess.get("_csrf_token"), initial_csrf, "VULNERABILIDAD: El token CSRF no se rota al autenticar.")

        # Un GET cross-site (p. ej. <img src="/logout">) debe ser rechazado
        res_cross_logout = self.client.get("/logout", headers={"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Dest": "image"})
        self.assertEqual(res_cross_logout.status_code, 400)

    # 12. Prueba de vulnerabilidad: Sanitización de nombres de archivo y sufijos seguros en model.py
    def test_12_filename_and_suffix_sanitization(self):
        dirty_name = "../../etc/passwd\n```\nINJECTED_PROMPT.py"
        clean_name = _sanitize_filename(dirty_name)
        self.assertNotIn("..", clean_name)
        self.assertNotIn("\n", clean_name)
        self.assertNotIn("`", clean_name)
        self.assertEqual(_safe_suffix("script.py"), ".py")
        self.assertEqual(_safe_suffix("malicious.ext_with_weird_chars$!"), ".bin")

    # 13. Prueba de migración a google-genai con gemini-3.8-flash y ThinkingLevel.MINIMAL
    def test_13_google_genai_sdk_and_model_fallback(self):
        ai = WebDevAI()
        self.assertEqual(ai.model_name, "gemini-3.8-flash")
        ai._init_generative_model("models/gemini-3.8-flash")
        self.assertEqual(ai.model_name, "gemini-3.8-flash")

        cfg = ai._build_config_for_model(ai.model_name)
        self.assertIsNotNone(cfg.thinking_config)

        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = "Respuesta desde google-genai"
        mock_chat.send_message.return_value = mock_resp
        mock_client.chats.create.return_value = mock_chat

        with patch.object(ai, "_get_client", return_value=(mock_client, None)):
            out = ai.generate("Hola", history_messages=[{"role": "user", "content": "prev"}, {"role": "bot", "content": "ok"}])
            self.assertEqual(out, "Respuesta desde google-genai")
            self.assertTrue(mock_client.chats.create.called)


if __name__ == "__main__":
    unittest.main()

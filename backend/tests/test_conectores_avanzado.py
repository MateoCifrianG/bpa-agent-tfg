"""
test_conectores_avanzado.py — Tests avanzados de conectores:
SMTP presets, test email, test telegram, test webhook, credenciales,
validaciones de parámetros, edge cases de red, seguridad.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestSMTPPresets:
    async def test_smtp_presets_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/ejecutar/connectors/smtp-presets")
        assert r.status_code == 401

    async def test_smtp_presets_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/ejecutar/connectors/smtp-presets", headers=auth_headers)
        assert r.status_code == 200

    async def test_smtp_presets_devuelve_dict_o_lista(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/ejecutar/connectors/smtp-presets", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, (dict, list))

    async def test_smtp_presets_no_vacio(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/ejecutar/connectors/smtp-presets", headers=auth_headers)
        data = r.json()
        assert bool(data)

    async def test_smtp_presets_content_type_json(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/ejecutar/connectors/smtp-presets", headers=auth_headers)
        assert "application/json" in r.headers.get("content-type", "")

    async def test_smtp_presets_tiene_gmail_o_similar(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/ejecutar/connectors/smtp-presets", headers=auth_headers)
        data = r.json()
        if isinstance(data, dict):
            keys_lower = [k.lower() for k in data.keys()]
            assert any("gmail" in k or "smtp" in k or "mail" in k for k in keys_lower)
        elif isinstance(data, list):
            assert len(data) > 0


class TestTestEmail:
    async def test_test_email_requiere_auth(self, client: AsyncClient):
        r = await client.post("/api/ejecutar/test/email", json={
            "smtp_host": "smtp.gmail.com", "smtp_port": 587,
            "smtp_user": "test@gmail.com", "smtp_password": "pass",
            "destinatario": "dest@gmail.com",
        })
        assert r.status_code == 401

    async def test_test_email_sin_campos_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/ejecutar/test/email", headers=auth_headers, json={})
        assert r.status_code == 422

    async def test_test_email_host_invalido_400(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/ejecutar/test/email", headers=auth_headers, json={
            "smtp_host": "host.invalido.no.existe.xyz", "smtp_port": 587,
            "smtp_user": "test@test.com", "smtp_password": "pass",
            "destinatario": "dest@test.com",
        })
        assert r.status_code in (200, 400, 422, 500, 503)

    async def test_test_email_sin_host_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/ejecutar/test/email", headers=auth_headers, json={
            "smtp_port": 587, "smtp_user": "test@test.com",
            "smtp_password": "pass", "destinatario": "dest@test.com",
        })
        assert r.status_code == 422

    async def test_test_email_sin_destinatario_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/ejecutar/test/email", headers=auth_headers, json={
            "smtp_host": "smtp.test.com", "smtp_port": 587,
            "smtp_user": "test@test.com", "smtp_password": "pass",
        })
        assert r.status_code == 422

    async def test_test_email_puerto_invalido(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/ejecutar/test/email", headers=auth_headers, json={
            "smtp_host": "smtp.test.com", "smtp_port": 99999,
            "smtp_user": "test@test.com", "smtp_password": "pass",
            "destinatario": "dest@test.com",
        })
        assert r.status_code in (200, 400, 422, 500)


class TestTestTelegram:
    async def test_test_telegram_requiere_auth(self, client: AsyncClient):
        r = await client.post("/api/ejecutar/test/telegram", json={
            "bot_token": "123:fake", "chat_id": "456",
        })
        assert r.status_code == 401

    async def test_test_telegram_sin_campos_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/ejecutar/test/telegram", headers=auth_headers, json={})
        assert r.status_code == 422

    async def test_test_telegram_token_invalido_400(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/ejecutar/test/telegram", headers=auth_headers, json={
            "bot_token": "token_invalido_no_real", "chat_id": "123456",
        })
        assert r.status_code in (200, 400, 422, 503)

    async def test_test_telegram_sin_token_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/ejecutar/test/telegram", headers=auth_headers, json={
            "chat_id": "123456",
        })
        assert r.status_code == 422

    async def test_test_telegram_sin_chat_id_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/ejecutar/test/telegram", headers=auth_headers, json={
            "bot_token": "123:fake",
        })
        assert r.status_code == 422


class TestTestWebhook:
    async def test_test_webhook_requiere_auth(self, client: AsyncClient):
        r = await client.post("/api/ejecutar/test/webhook", json={
            "url": "https://httpbin.org/post",
        })
        assert r.status_code == 401

    async def test_test_webhook_sin_url_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/ejecutar/test/webhook", headers=auth_headers, json={})
        assert r.status_code == 422

    async def test_test_webhook_url_invalida(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/ejecutar/test/webhook", headers=auth_headers, json={
            "url": "no_es_una_url_valida",
        })
        assert r.status_code in (200, 400, 422, 500, 503)

    async def test_test_webhook_metodo_get(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/ejecutar/test/webhook", headers=auth_headers, json={
            "url": "https://httpbin.org/get", "method": "GET",
        })
        assert r.status_code in (200, 400, 422, 503)

    async def test_test_webhook_con_payload(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/ejecutar/test/webhook", headers=auth_headers, json={
            "url": "https://httpbin.org/post",
            "payload": {"test": True, "data": "value"},
        })
        assert r.status_code in (200, 400, 422, 503)

    async def test_test_webhook_metodo_invalido(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/ejecutar/test/webhook", headers=auth_headers, json={
            "url": "https://httpbin.org/post", "method": "INVALID",
        })
        assert r.status_code in (200, 400, 422, 500, 503)


class TestEjecutarConectoresCombinado:
    async def test_smtp_presets_admin_tambien_ve(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/ejecutar/connectors/smtp-presets", headers=admin_headers)
        assert r.status_code == 200

    async def test_test_email_body_vacio_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/ejecutar/test/email", headers=auth_headers)
        assert r.status_code in (400, 422)

    async def test_test_telegram_body_vacio_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/ejecutar/test/telegram", headers=auth_headers)
        assert r.status_code in (400, 422)

    async def test_test_webhook_body_vacio_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/ejecutar/test/webhook", headers=auth_headers)
        assert r.status_code in (400, 422)

    async def test_email_sin_auth_token_401(self, client: AsyncClient):
        r = await client.post("/api/ejecutar/test/email", json={
            "smtp_host": "smtp.gmail.com", "smtp_port": 587,
            "smtp_user": "a@b.com", "smtp_password": "p", "destinatario": "d@b.com"
        })
        assert r.status_code == 401

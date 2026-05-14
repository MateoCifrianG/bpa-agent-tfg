"""
test_ejecutar_endpoints.py — Tests del router de ejecución de automatizaciones.
"""
import pytest
from httpx import AsyncClient
pytestmark = pytest.mark.asyncio


class TestEjecutarScheduler:
    async def test_scheduler_jobs_ok(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/ejecutar/scheduler/jobs", headers=auth_headers)
        assert r.status_code == 200

    async def test_scheduler_jobs_sin_auth(self, client: AsyncClient):
        r = await client.get("/api/ejecutar/scheduler/jobs")
        assert r.status_code in (401, 403)

    async def test_scheduler_jobs_devuelve_lista(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/ejecutar/scheduler/jobs", headers=auth_headers)
        data = r.json()
        assert isinstance(data, (list, dict))

    async def test_smtp_presets_ok(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/ejecutar/connectors/smtp-presets", headers=auth_headers)
        assert r.status_code == 200

    async def test_smtp_presets_sin_auth(self, client: AsyncClient):
        r = await client.get("/api/ejecutar/connectors/smtp-presets")
        assert r.status_code in (401, 403)

    async def test_smtp_presets_devuelve_datos(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/ejecutar/connectors/smtp-presets", headers=auth_headers)
        data = r.json()
        assert isinstance(data, (list, dict))


class TestTestEmail:
    async def test_test_email_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/ejecutar/test/email", json={
            "smtp_host": "smtp.gmail.com", "smtp_port": 587,
            "smtp_user": "test@test.com", "smtp_password": "pass",
            "destinatario": "dest@test.com"
        })
        assert r.status_code in (401, 403)

    async def test_test_email_con_smtp_invalido(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/ejecutar/test/email", headers=auth_headers, json={
            "smtp_host": "smtp.invalido.localhost.test", "smtp_port": 587,
            "smtp_user": "test@test.com", "smtp_password": "pass",
            "destinatario": "dest@test.com"
        })
        assert r.status_code in (200, 400, 422, 500)

    async def test_test_email_falta_campo(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/ejecutar/test/email", headers=auth_headers, json={
            "smtp_host": "smtp.test.com"
        })
        assert r.status_code in (200, 400, 422)


class TestTestTelegram:
    async def test_test_telegram_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/ejecutar/test/telegram", json={
            "bot_token": "FAKE", "chat_id": "123"
        })
        assert r.status_code in (401, 403)

    async def test_test_telegram_token_invalido(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/ejecutar/test/telegram", headers=auth_headers, json={
            "bot_token": "0000:FAKE_TOKEN", "chat_id": "12345"
        })
        assert r.status_code in (200, 400)

    async def test_test_telegram_falta_chat_id(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/ejecutar/test/telegram", headers=auth_headers, json={
            "bot_token": "FAKE"
        })
        assert r.status_code in (200, 400, 422)


class TestTestWebhook:
    async def test_test_webhook_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/ejecutar/test/webhook", json={"url": "http://test.com"})
        assert r.status_code in (401, 403)

    async def test_test_webhook_url_invalida(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/ejecutar/test/webhook", headers=auth_headers, json={
            "url": "http://localhost.invalid.test/hook"
        })
        assert r.status_code in (200, 400)

    async def test_test_webhook_sin_url(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/ejecutar/test/webhook", headers=auth_headers, json={})
        assert r.status_code in (200, 400, 422)


class TestEjecutarAuto:
    async def test_ejecutar_auto_inexistente(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/ejecutar/auto-id-no-existe", headers=auth_headers)
        assert r.status_code in (200, 400, 404)

    async def test_ejecutar_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/ejecutar/some-auto-id")
        assert r.status_code in (401, 403)

    async def test_historial_sin_auth(self, client: AsyncClient):
        r = await client.get("/api/ejecutar/some-auto-id/historial")
        assert r.status_code in (401, 403)

    async def test_programar_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/ejecutar/some-id/programar", json={"cron_expr": "0 9 * * *"})
        assert r.status_code in (401, 403)

    async def test_desprogramar_sin_auth(self, client: AsyncClient):
        r = await client.delete("/api/ejecutar/some-id/programar")
        assert r.status_code in (401, 403)

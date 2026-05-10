"""
test_ejecutar.py — Tests de ejecución de automatizaciones: historial, scheduler, connectors.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestHistorial:
    async def test_historial_vacio(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.get(f"/api/ejecutar/{test_auto['id']}/historial", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_historial_requiere_auth(self, client: AsyncClient, test_auto):
        r = await client.get(f"/api/ejecutar/{test_auto['id']}/historial")
        assert r.status_code == 401

    async def test_historial_auto_no_existe(self, client: AsyncClient, auth_headers):
        r = await client.get(
            "/api/ejecutar/00000000-0000-0000-0000-000000000000/historial",
            headers=auth_headers,
        )
        assert r.status_code == 404

    async def test_historial_auto_otro_usuario(
        self, client: AsyncClient, auth_headers, admin_headers, test_user, admin_user
    ):
        cr = await client.post("/api/automatizaciones", headers=admin_headers, json={
            "nombre": "Auto Admin Historial",
        })
        auto_id = cr.json()["id"]
        r = await client.get(f"/api/ejecutar/{auto_id}/historial", headers=auth_headers)
        assert r.status_code == 404

    async def test_historial_limit_param(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.get(
            f"/api/ejecutar/{test_auto['id']}/historial?limit=5",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert len(r.json()) <= 5

    async def test_historial_tras_ejecucion(self, client: AsyncClient, test_user, auth_headers, test_auto):
        # Ejecutar primero
        await client.post(f"/api/ejecutar/{test_auto['id']}", headers=auth_headers)
        r = await client.get(f"/api/ejecutar/{test_auto['id']}/historial", headers=auth_headers)
        assert r.status_code == 200
        # Debe tener al menos 1 entrada
        assert len(r.json()) >= 1

    async def test_historial_entradas_tienen_campos(self, client: AsyncClient, test_user, auth_headers, test_auto):
        await client.post(f"/api/ejecutar/{test_auto['id']}", headers=auth_headers)
        r = await client.get(f"/api/ejecutar/{test_auto['id']}/historial", headers=auth_headers)
        if r.json():
            entrada = r.json()[0]
            for campo in ["id", "estado", "triggered_by"]:
                assert campo in entrada


class TestEjecutarAhora:
    async def test_ejecutar_sin_auth(self, client: AsyncClient, test_auto):
        r = await client.post(f"/api/ejecutar/{test_auto['id']}")
        assert r.status_code == 401

    async def test_ejecutar_auto_no_existe(self, client: AsyncClient, auth_headers):
        r = await client.post(
            "/api/ejecutar/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        # 400 si falla la ejecución, 404 si no existe
        assert r.status_code in (400, 404)

    async def test_ejecutar_auto_devuelve_resultado(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.post(f"/api/ejecutar/{test_auto['id']}", headers=auth_headers)
        # La ejecución puede tener éxito o fallar graciosamente
        assert r.status_code in (200, 400)

    async def test_ejecutar_auto_otro_usuario(
        self, client: AsyncClient, auth_headers, admin_headers, test_user, admin_user
    ):
        cr = await client.post("/api/automatizaciones", headers=admin_headers, json={
            "nombre": "Auto Admin Exec",
        })
        auto_id = cr.json()["id"]
        r = await client.post(f"/api/ejecutar/{auto_id}", headers=auth_headers)
        assert r.status_code in (400, 404)


class TestScheduler:
    async def test_scheduler_jobs_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/ejecutar/scheduler/jobs")
        assert r.status_code == 401

    async def test_scheduler_jobs_lista(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/ejecutar/scheduler/jobs", headers=auth_headers)
        assert r.status_code == 200
        # Devuelve lista de jobs (puede estar vacía)
        assert isinstance(r.json(), list)

    async def test_programar_auto(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.post(
            f"/api/ejecutar/{test_auto['id']}/programar",
            headers=auth_headers,
            json={"cron_expr": "0 9 * * 1"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True

    async def test_programar_requiere_auth(self, client: AsyncClient, test_auto):
        r = await client.post(
            f"/api/ejecutar/{test_auto['id']}/programar",
            json={"cron_expr": "0 9 * * 1"},
        )
        assert r.status_code == 401

    async def test_programar_auto_no_existe(self, client: AsyncClient, auth_headers):
        r = await client.post(
            "/api/ejecutar/00000000-0000-0000-0000-000000000000/programar",
            headers=auth_headers,
            json={"cron_expr": "0 9 * * 1"},
        )
        assert r.status_code == 404

    async def test_desprogramar_auto(self, client: AsyncClient, test_user, auth_headers, test_auto):
        # Programar primero
        await client.post(
            f"/api/ejecutar/{test_auto['id']}/programar",
            headers=auth_headers,
            json={"cron_expr": "0 9 * * 1"},
        )
        r = await client.delete(
            f"/api/ejecutar/{test_auto['id']}/programar",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True

    async def test_desprogramar_requiere_auth(self, client: AsyncClient, test_auto):
        r = await client.delete(f"/api/ejecutar/{test_auto['id']}/programar")
        assert r.status_code == 401

    async def test_desprogramar_auto_no_existe(self, client: AsyncClient, auth_headers):
        r = await client.delete(
            "/api/ejecutar/00000000-0000-0000-0000-000000000000/programar",
            headers=auth_headers,
        )
        assert r.status_code == 404


class TestSmtpPresets:
    async def test_smtp_presets_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/ejecutar/connectors/smtp-presets")
        assert r.status_code == 401

    async def test_smtp_presets_devuelve_lista(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/ejecutar/connectors/smtp-presets", headers=auth_headers)
        assert r.status_code == 200
        # Deben existir presets definidos
        assert len(r.json()) > 0

    async def test_smtp_presets_gmail_presente(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/ejecutar/connectors/smtp-presets", headers=auth_headers)
        assert r.status_code == 200
        presets = r.json()
        nombres = [p.get("nombre", "").lower() if isinstance(p, dict) else str(p).lower() for p in presets]
        # Buscar gmail en los presets (puede ser key o valor)
        assert any("gmail" in n for n in nombres) or any("gmail" in str(p).lower() for p in presets)


class TestTestConnectors:
    async def test_test_email_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/ejecutar/test/email", json={
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_user": "test@test.com",
            "smtp_password": "pass",
            "destinatario": "dest@test.com",
        })
        assert r.status_code == 401

    async def test_test_email_campos_requeridos(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/ejecutar/test/email", headers=auth_headers, json={
            "smtp_host": "smtp.gmail.com",
        })
        assert r.status_code == 422

    async def test_test_telegram_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/ejecutar/test/telegram", json={
            "bot_token": "123:abc",
            "chat_id": "456",
        })
        assert r.status_code == 401

    async def test_test_telegram_bot_invalido(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/ejecutar/test/telegram", headers=auth_headers, json={
            "bot_token": "token-invalido-fake",
            "chat_id": "12345",
        })
        # Debe fallar con 400 porque el bot token es inválido
        assert r.status_code in (400, 422)

    async def test_test_webhook_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/ejecutar/test/webhook", json={
            "url": "https://httpbin.org/post",
        })
        assert r.status_code == 401

    async def test_test_webhook_campos_requeridos(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/ejecutar/test/webhook", headers=auth_headers, json={})
        assert r.status_code == 422

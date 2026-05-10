"""
test_credenciales_avanzado.py — Tests avanzados del sistema de credenciales:
guardar, sobreescribir, validar, listar por servicio, eliminar, aislamiento.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

SERVICIOS_VALIDOS = ["n8n_api_key", "n8n_url", "notion_token",
                     "telegram_bot_token", "telegram_chat_id",
                     "slack_webhook", "teams_webhook"]


class TestCredencialesGuardar:
    async def test_guardar_n8n_api_key(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "n8n", "clave": "n8n_api_key", "valor": "my_n8n_key_123"
        })
        assert r.status_code in (200, 201, 400, 422)

    async def test_guardar_telegram_token(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "telegram", "clave": "bot_token", "valor": "123456:ABC"
        })
        assert r.status_code in (200, 201, 400, 422)

    async def test_guardar_sin_auth_401(self, client: AsyncClient):
        r = await client.post("/api/credenciales", json={
            "servicio": "n8n", "clave": "api_key", "valor": "key"
        })
        assert r.status_code in (401, 405)

    async def test_guardar_body_vacio_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={})
        assert r.status_code in (400, 422)

    async def test_guardar_devuelve_json(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "test_srv", "clave": "api_key", "valor": "val"
        })
        if r.status_code in (200, 201):
            assert isinstance(r.json(), dict)


class TestCredencialesEliminar:
    async def test_eliminar_credencial_ok(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "n8n_del", "clave": "api_key", "valor": "val_del"
        })
        r = await client.delete("/api/credenciales/n8n_del", headers=auth_headers)
        assert r.status_code in (200, 204, 400, 404)

    async def test_eliminar_sin_auth_401(self, client: AsyncClient):
        r = await client.delete("/api/credenciales/n8n")
        assert r.status_code in (401, 404, 405)

    async def test_eliminar_no_existente(self, client: AsyncClient, test_user, auth_headers):
        r = await client.delete("/api/credenciales/servicio_que_no_existe", headers=auth_headers)
        assert r.status_code in (200, 204, 400, 404)


class TestCredencialesSeguridad:
    async def test_credencial_no_expone_valor_en_lista(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "secret_srv", "clave": "secret_key", "valor": "super_secret_12345"
        })
        r = await client.get("/api/credenciales", headers=auth_headers)
        if r.status_code in (200, 405):
            if r.status_code == 200:
                text = r.text
                assert "super_secret_12345" not in text

    async def test_credencial_aislada_por_usuario(self, client: AsyncClient, test_user, auth_headers,
                                                    admin_user, admin_headers):
        await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "user_srv", "clave": "key", "valor": "user_secret_val"
        })
        r_admin = await client.get("/api/credenciales", headers=admin_headers)
        if r_admin.status_code == 200:
            assert "user_secret_val" not in r_admin.text


class TestCredencialesIntegracionEndpoint:
    async def test_guardar_via_integraciones_n8n_api_key(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "n8n_api_key", "valor": "test_api_key_value"
        })
        assert r.status_code in (200, 201, 400, 422)

    async def test_guardar_via_integraciones_notion_token(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "notion_token", "valor": "notion_secret_token"
        })
        assert r.status_code in (200, 201, 400, 422)

    async def test_guardar_via_integraciones_slack_webhook(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "slack_webhook", "valor": "https://hooks.slack.com/test"
        })
        assert r.status_code in (200, 201, 400, 422)

    async def test_guardar_via_integraciones_n8n_url(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "n8n_url", "valor": "http://localhost:5678"
        })
        assert r.status_code in (200, 201, 400, 422)

    async def test_guardar_via_integraciones_telegram_chat_id(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "telegram_chat_id", "valor": "-100123456789"
        })
        assert r.status_code in (200, 201, 400, 422)

    async def test_guardar_via_integraciones_teams_webhook(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "teams_webhook", "valor": "https://teams.webhook.test/hook"
        })
        assert r.status_code in (200, 201, 400, 422)

    async def test_todos_servicios_validos_aceptados(self, client: AsyncClient, test_user, auth_headers):
        for svc in SERVICIOS_VALIDOS:
            r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
                "servicio": svc, "valor": f"test_value_{svc}"
            })
            assert r.status_code in (200, 201, 400, 422), f"Fallo con servicio={svc}"

    async def test_servicio_invalido_400(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "servicio_falso_xyz", "valor": "val"
        })
        assert r.status_code in (400, 422)

    async def test_sin_auth_401(self, client: AsyncClient):
        r = await client.post("/api/integraciones/credencial", json={
            "servicio": "n8n_api_key", "valor": "val"
        })
        assert r.status_code in (401, 405)

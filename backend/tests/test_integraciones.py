"""
test_integraciones.py — Tests de integraciones externas: listado, credenciales, desconexión.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestListarIntegraciones:
    async def test_listar_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/integraciones")
        assert r.status_code == 401

    async def test_listar_integraciones_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        assert r.status_code == 200

    async def test_listar_devuelve_integraciones(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        data = r.json()
        assert "integraciones" in data
        assert isinstance(data["integraciones"], list)

    async def test_listar_tiene_integraciones_conocidas(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        integraciones = r.json()["integraciones"]
        ids = [i["id"] for i in integraciones]
        for esperado in ["google", "n8n", "notion", "telegram", "slack"]:
            assert esperado in ids, f"Integración '{esperado}' no encontrada"

    async def test_integracion_tiene_campos_requeridos(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        for integ in r.json()["integraciones"]:
            for campo in ["id", "nombre", "descripcion", "conectado"]:
                assert campo in integ, f"Campo '{campo}' ausente en integración {integ.get('id')}"

    async def test_sin_credenciales_conectado_es_false(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        for integ in r.json()["integraciones"]:
            assert integ["conectado"] is False

    async def test_integracion_google_tiene_oauth_url(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        google = next(i for i in r.json()["integraciones"] if i["id"] == "google")
        assert google["tipo"] == "oauth2"


class TestGuardarCredencialIntegracion:
    async def test_guardar_credencial_n8n_api_key(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "n8n_api_key",
            "valor": "mi-api-key-n8n",
        })
        assert r.status_code == 200
        assert r.json()["ok"] is True

    async def test_guardar_credencial_notion_token(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "notion_token",
            "valor": "secret-notion-token",
        })
        assert r.status_code == 200

    async def test_guardar_credencial_telegram_bot_token(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "telegram_bot_token",
            "valor": "123456:ABC-DEF",
        })
        assert r.status_code == 200

    async def test_guardar_credencial_slack_webhook(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "slack_webhook",
            "valor": "https://hooks.slack.com/services/T/B/X",
        })
        assert r.status_code == 200

    async def test_guardar_credencial_servicio_invalido(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "servicio_desconocido_xyz",
            "valor": "valor",
        })
        assert r.status_code == 400

    async def test_guardar_credencial_requiere_auth(self, client: AsyncClient):
        r = await client.post("/api/integraciones/credencial", json={
            "servicio": "n8n_api_key",
            "valor": "test",
        })
        assert r.status_code == 401

    async def test_credencial_no_expuesta_en_respuesta(self, client: AsyncClient, test_user, auth_headers):
        secreto = "valor-super-secreto-que-no-debe-aparecer"
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "n8n_api_key",
            "valor": secreto,
        })
        assert secreto not in r.text

    async def test_tras_guardar_integracion_marcada_conectada(
        self, client: AsyncClient, test_user, auth_headers
    ):
        await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "notion_token",
            "valor": "token-real",
        })
        r = await client.get("/api/integraciones", headers=auth_headers)
        notion = next(i for i in r.json()["integraciones"] if i["id"] == "notion")
        assert notion["conectado"] is True


class TestDesconectarIntegracion:
    async def test_desconectar_requiere_auth(self, client: AsyncClient):
        r = await client.delete("/api/integraciones/google")
        assert r.status_code == 401

    async def test_desconectar_integracion_ok(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "telegram_bot_token",
            "valor": "token-test",
        })
        r = await client.delete("/api/integraciones/telegram_bot_token", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["ok"] is True

    async def test_desconectar_integracion_no_conectada(self, client: AsyncClient, test_user, auth_headers):
        # Desconectar algo que no está guardado — debe devolver ok igualmente
        r = await client.delete("/api/integraciones/no_conectado", headers=auth_headers)
        assert r.status_code in (200, 404)

    async def test_tras_desconectar_integracion_marca_false(
        self, client: AsyncClient, test_user, auth_headers
    ):
        await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "slack_webhook",
            "valor": "https://hooks.slack.com/services/X",
        })
        await client.delete("/api/integraciones/slack_webhook", headers=auth_headers)
        r = await client.get("/api/integraciones", headers=auth_headers)
        slack = next(i for i in r.json()["integraciones"] if i["id"] == "slack")
        assert slack["conectado"] is False


class TestOAuthGoogle:
    async def test_oauth_google_sin_configurar_da_400(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones/oauth/google", headers=auth_headers, follow_redirects=False)
        # Si GOOGLE_CLIENT_ID no está configurado, devuelve 400
        # Si está configurado, redirige (302)
        assert r.status_code in (302, 400)

    async def test_oauth_callback_error_redirige(self, client: AsyncClient):
        r = await client.get(
            "/api/integraciones/oauth/google/callback?error=access_denied",
            follow_redirects=False,
        )
        # El callback con error devuelve una redirección (302) al frontend
        assert r.status_code in (200, 302, 307, 400)

    async def test_oauth_callback_sin_code(self, client: AsyncClient):
        r = await client.get(
            "/api/integraciones/oauth/google/callback?state=fakestate",
            follow_redirects=False,
        )
        assert r.status_code in (400, 422)


class TestN8nIntegracion:
    async def test_n8n_verificar_requiere_auth(self, client: AsyncClient):
        r = await client.post("/api/integraciones/n8n/verificar", json={"url": "http://localhost:5678"})
        assert r.status_code == 401

    async def test_n8n_verificar_url_invalida(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/n8n/verificar", headers=auth_headers, json={
            "url": "http://localhost:9999",
        })
        # Devuelve ok: False porque n8n no está corriendo, pero no 4xx del API
        assert r.status_code == 200

    async def test_n8n_workflows_sin_api_key(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones/n8n/workflows", headers=auth_headers)
        assert r.status_code == 400

    async def test_n8n_webhook_requiere_auth(self, client: AsyncClient):
        r = await client.post("/api/integraciones/n8n/webhook/test-path", json={"payload": {}})
        assert r.status_code == 401


class TestNotionIntegracion:
    async def test_notion_verificar_requiere_auth(self, client: AsyncClient):
        r = await client.post("/api/integraciones/notion/verificar", json={"token": "fake"})
        assert r.status_code == 401

    async def test_notion_verificar_token_invalido(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/notion/verificar", headers=auth_headers, json={
            "token": "fake-notion-token",
        })
        assert r.status_code == 200  # El endpoint responde aunque el token sea malo

    async def test_notion_pagina_sin_token_guardado(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/notion/pagina", headers=auth_headers, json={
            "parent_id": "fake-parent-id",
            "titulo": "Test página",
        })
        assert r.status_code == 400  # No hay token guardado

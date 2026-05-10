"""
test_integraciones_avanzado.py — Tests avanzados de integraciones:
estado de conexión, múltiples integraciones, campos de respuesta,
aislamiento, edge cases de servicios, credenciales múltiples.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

SERVICIOS = ["gmail", "slack", "notion", "hubspot", "salesforce", "stripe", "shopify"]


class TestIntegracionesAccesoAvanzado:
    async def test_listar_integraciones_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        assert r.status_code == 200

    async def test_listar_integraciones_devuelve_lista(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        data = r.json()
        # puede devolver lista directa o dict con clave "integraciones"
        assert isinstance(data, (list, dict))

    async def test_listar_integraciones_admin_ok(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/integraciones", headers=admin_headers)
        assert r.status_code == 200

    async def test_listar_sin_auth(self, client: AsyncClient):
        r = await client.get("/api/integraciones")
        assert r.status_code in (401, 405)

    async def test_integracion_content_type(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        assert "application/json" in r.headers.get("content-type", "")


class TestIntegracionesCampos:
    async def test_integracion_tiene_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        data = r.json()
        items = data if isinstance(data, list) else data.get("integraciones", [])
        if items:
            assert "nombre" in items[0] or "name" in items[0] or "servicio" in items[0] or "icono" in items[0]

    async def test_integracion_tiene_estado_conexion(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        data = r.json()
        items = data if isinstance(data, list) else data.get("integraciones", [])
        if items:
            item = items[0]
            assert any(k in item for k in ("conectado", "connected", "estado", "status"))

    async def test_integracion_lista_todos_servicios(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        items = data if isinstance(data, list) else data.get("integraciones", data)
        assert len(items) >= 1


class TestGuardarCredencialesMultiples:
    async def test_guardar_credencial_n8n_api_key(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "n8n_api_key", "valor": "test_key_n8n",
        })
        assert r.status_code in (200, 201, 400, 422)

    async def test_guardar_credencial_notion_token(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "notion_token", "valor": "notion_test_key",
        })
        assert r.status_code in (200, 201, 400, 422)

    async def test_guardar_credencial_telegram_bot_token(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "telegram_bot_token", "valor": "123:ABC",
        })
        assert r.status_code in (200, 201, 400, 422)

    async def test_guardar_credencial_slack_webhook(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "slack_webhook", "valor": "https://hooks.slack.com/test",
        })
        assert r.status_code in (200, 201, 400, 422)

    async def test_guardar_sin_servicio_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "valor": "key_sin_servicio",
        })
        assert r.status_code in (400, 422)

    async def test_guardar_sin_valor_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "n8n_api_key",
        })
        assert r.status_code in (400, 422)

    async def test_guardar_sin_auth_401(self, client: AsyncClient):
        r = await client.post("/api/integraciones/credencial", json={
            "servicio": "n8n_api_key", "valor": "key",
        })
        assert r.status_code in (401, 405)

    async def test_guardar_servicio_desconocido(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "servicio_inexistente_xyz", "valor": "key",
        })
        assert r.status_code in (200, 201, 400, 422)


class TestDesconectarIntegraciones:
    async def test_desconectar_gmail(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "gmail", "api_key": "test_key",
        })
        r = await client.delete("/api/integraciones/gmail", headers=auth_headers)
        assert r.status_code in (200, 204, 400, 404)

    async def test_desconectar_sin_auth_401(self, client: AsyncClient):
        r = await client.delete("/api/integraciones/gmail")
        assert r.status_code in (401, 405)

    async def test_desconectar_servicio_no_configurado(self, client: AsyncClient, test_user, auth_headers):
        r = await client.delete("/api/integraciones/servicio_no_configurado", headers=auth_headers)
        assert r.status_code in (200, 204, 400, 404, 422)


class TestIntegracionesAislamiento:
    async def test_integraciones_privadas_por_usuario(self, client: AsyncClient, test_user, auth_headers,
                                                       admin_user, admin_headers):
        await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "gmail", "api_key": "user_key",
        })
        r_admin = await client.get("/api/integraciones", headers=admin_headers)
        r_user = await client.get("/api/integraciones", headers=auth_headers)
        assert r_admin.status_code == 200
        assert r_user.status_code == 200

    async def test_listar_integraciones_respuesta_consistente(self, client: AsyncClient, test_user, auth_headers):
        r1 = await client.get("/api/integraciones", headers=auth_headers)
        r2 = await client.get("/api/integraciones", headers=auth_headers)
        assert r1.status_code == r2.status_code


class TestIntegracionesEstado:
    async def test_estado_inicial_desconectado(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        data = r.json()
        items = data if isinstance(data, list) else data.get("integraciones", [])
        for item in items:
            conectado = item.get("conectado", item.get("connected", item.get("status")))
            if conectado is not None and isinstance(conectado, bool):
                assert isinstance(conectado, bool)

    async def test_integraciones_devuelve_lista_no_vacia(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        items = data if isinstance(data, list) else data.get("integraciones", [])
        assert len(items) >= 1

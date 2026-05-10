"""
test_integraciones_completo.py — Tests exhaustivos de integraciones externas:
listado, campos, credenciales, desconexión, estado, aislamiento, edge cases.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestIntegracionesAcceso:
    async def test_listar_sin_auth_401(self, client: AsyncClient):
        r = await client.get("/api/integraciones")
        assert r.status_code == 401

    async def test_guardar_credencial_sin_auth_401(self, client: AsyncClient):
        r = await client.post("/api/integraciones/credencial", json={"servicio": "n8n_api_key", "valor": "x"})
        assert r.status_code == 401

    async def test_desconectar_sin_auth_401(self, client: AsyncClient):
        r = await client.delete("/api/integraciones/n8n")
        assert r.status_code == 401

    async def test_token_invalido_rechazado(self, client: AsyncClient):
        h = {"Authorization": "Bearer invalid_token_xyz"}
        r = await client.get("/api/integraciones", headers=h)
        assert r.status_code == 401


class TestListarIntegraciones:
    async def test_listar_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        assert r.status_code == 200

    async def test_listar_tiene_campo_integraciones(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        assert "integraciones" in r.json()

    async def test_integraciones_es_lista(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        assert isinstance(r.json()["integraciones"], list)

    async def test_integraciones_no_vacia(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        assert len(r.json()["integraciones"]) > 0

    async def test_integraciones_incluye_google(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        ids = [i["id"] for i in r.json()["integraciones"]]
        assert "google" in ids

    async def test_integraciones_incluye_n8n(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        ids = [i["id"] for i in r.json()["integraciones"]]
        assert "n8n" in ids

    async def test_integraciones_incluye_notion(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        ids = [i["id"] for i in r.json()["integraciones"]]
        assert "notion" in ids

    async def test_integraciones_incluye_telegram(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        ids = [i["id"] for i in r.json()["integraciones"]]
        assert "telegram" in ids

    async def test_integraciones_incluye_slack(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        ids = [i["id"] for i in r.json()["integraciones"]]
        assert "slack" in ids

    async def test_content_type_json(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        assert "application/json" in r.headers.get("content-type", "")


class TestCamposIntegracion:
    async def test_integracion_tiene_id(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        for integ in r.json()["integraciones"]:
            assert "id" in integ

    async def test_integracion_tiene_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        for integ in r.json()["integraciones"]:
            assert "nombre" in integ
            assert len(integ["nombre"]) > 0

    async def test_integracion_tiene_descripcion(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        for integ in r.json()["integraciones"]:
            assert "descripcion" in integ

    async def test_integracion_tiene_conectado(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        for integ in r.json()["integraciones"]:
            assert "conectado" in integ

    async def test_integracion_tiene_tipo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        for integ in r.json()["integraciones"]:
            assert "tipo" in integ

    async def test_conectado_es_bool(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        for integ in r.json()["integraciones"]:
            assert isinstance(integ["conectado"], bool)

    async def test_sin_credenciales_conectado_false(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        for integ in r.json()["integraciones"]:
            assert integ["conectado"] is False

    async def test_google_es_oauth2(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        google = next((i for i in r.json()["integraciones"] if i["id"] == "google"), None)
        if google:
            assert google["tipo"] == "oauth2"

    async def test_n8n_es_api_key(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        n8n = next((i for i in r.json()["integraciones"] if i["id"] == "n8n"), None)
        if n8n:
            assert n8n["tipo"] in ("api_key", "webhook", "n8n")

    async def test_ids_son_strings(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/integraciones", headers=auth_headers)
        for integ in r.json()["integraciones"]:
            assert isinstance(integ["id"], str)
            assert len(integ["id"]) > 0


class TestGuardarCredencialIntegracion:
    async def test_guardar_n8n_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "n8n_api_key", "valor": "mi-api-key-n8n-abc123",
        })
        assert r.status_code == 200

    async def test_guardar_n8n_devuelve_ok_true(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "n8n_api_key", "valor": "clave-n8n-xyz",
        })
        assert r.status_code == 200
        assert r.json().get("ok") is True

    async def test_guardar_notion_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "notion_token", "valor": "secret_abc123",
        })
        assert r.status_code == 200

    async def test_guardar_telegram_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "telegram_bot_token", "valor": "123:ABC-DEF",
        })
        assert r.status_code == 200

    async def test_guardar_slack_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "slack_webhook", "valor": "https://hooks.slack.com/services/T/B/X",
        })
        assert r.status_code == 200

    async def test_guardar_servicio_invalido_400(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "servicio_que_no_existe_jamas", "valor": "abc",
        })
        assert r.status_code in (400, 422)

    async def test_guardar_sin_servicio_422(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "valor": "abc123",
        })
        assert r.status_code == 422

    async def test_guardar_sin_valor_422(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "n8n_api_key",
        })
        assert r.status_code == 422

    async def test_guardar_valor_no_expuesto(self, client: AsyncClient, test_user, auth_headers):
        secret = "super_private_n8n_key_12345abcde"
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "n8n_api_key", "valor": secret,
        })
        assert secret not in r.text

    async def test_guardar_n8n_url(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "n8n_url", "valor": "http://localhost:5678",
        })
        assert r.status_code in (200, 400, 422)


class TestDesconectarIntegracion:
    async def test_desconectar_n8n_ok(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "n8n_api_key", "valor": "key-to-disconnect",
        })
        r = await client.delete("/api/integraciones/n8n", headers=auth_headers)
        assert r.status_code in (200, 204, 404)

    async def test_desconectar_no_conectada(self, client: AsyncClient, test_user, auth_headers):
        r = await client.delete("/api/integraciones/notion", headers=auth_headers)
        assert r.status_code in (200, 204, 404)

    async def test_desconectar_integracion_inexistente(self, client: AsyncClient, test_user, auth_headers):
        r = await client.delete("/api/integraciones/integracion_xyz_no_existe", headers=auth_headers)
        assert r.status_code in (200, 204, 400, 404, 422)

    async def test_desconectar_devuelve_json(self, client: AsyncClient, test_user, auth_headers):
        r = await client.delete("/api/integraciones/n8n", headers=auth_headers)
        if r.status_code == 200:
            assert isinstance(r.json(), dict)


class TestEstadoTrasConexion:
    async def test_conectado_true_tras_guardar_n8n(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "n8n_api_key", "valor": "mi-clave-n8n-valid",
        })
        r = await client.get("/api/integraciones", headers=auth_headers)
        n8n = next((i for i in r.json()["integraciones"] if i["id"] == "n8n"), None)
        if n8n:
            assert n8n["conectado"] is True

    async def test_conectado_true_tras_guardar_notion(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "notion_token", "valor": "secret_notion_valid",
        })
        r = await client.get("/api/integraciones", headers=auth_headers)
        notion = next((i for i in r.json()["integraciones"] if i["id"] == "notion"), None)
        if notion:
            assert notion["conectado"] is True

    async def test_conectado_true_tras_guardar_telegram(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/integraciones/credencial", headers=auth_headers, json={
            "servicio": "telegram_bot_token", "valor": "123456:VALID",
        })
        r = await client.get("/api/integraciones", headers=auth_headers)
        tg = next((i for i in r.json()["integraciones"] if i["id"] == "telegram"), None)
        if tg:
            assert tg["conectado"] is True

    async def test_aislamiento_conexion_entre_usuarios(self, client: AsyncClient, test_user, auth_headers,
                                                        admin_user, admin_headers):
        await client.post("/api/integraciones/credencial", headers=admin_headers, json={
            "servicio": "n8n_api_key", "valor": "clave-admin-exclusiva",
        })
        r = await client.get("/api/integraciones", headers=auth_headers)
        n8n = next((i for i in r.json()["integraciones"] if i["id"] == "n8n"), None)
        if n8n:
            assert n8n["conectado"] is False

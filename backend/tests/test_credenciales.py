"""
test_credenciales.py — Tests de credenciales: guardar, eliminar, seguridad, cifrado.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestCredencialesAcceso:
    async def test_guardar_credencial_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/credenciales", json={"servicio": "n8n", "token": "abc"})
        assert r.status_code == 401

    async def test_eliminar_credencial_sin_auth(self, client: AsyncClient):
        r = await client.delete("/api/credenciales/n8n")
        assert r.status_code == 401


class TestGuardarCredencial:
    async def test_guardar_credencial_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "n8n_key",
            "token": "mi-api-key-secreta-123",
        })
        assert r.status_code == 201

    async def test_guardar_credencial_devuelve_servicio(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "notion_token",
            "token": "secret-notion-xyz",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["servicio"] == "notion_token"

    async def test_guardar_credencial_no_devuelve_token(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "slack_webhook",
            "token": "https://hooks.slack.com/services/XXX/YYY/ZZZ",
        })
        assert r.status_code == 201
        data = r.json()
        # La respuesta NUNCA debe exponer el token
        assert "token" not in data
        assert "https://hooks.slack.com" not in str(data)

    async def test_guardar_credencial_mensaje_confirmacion(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "telegram_bot",
            "token": "1234567890:ABCdef",
        })
        assert r.status_code == 201
        assert "mensaje" in r.json()

    async def test_guardar_credencial_sin_servicio_falla(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "token": "abc123",
        })
        assert r.status_code == 422

    async def test_guardar_credencial_sin_token_falla(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "n8n",
        })
        assert r.status_code == 422

    async def test_guardar_credencial_sobreescribe(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "my_service",
            "token": "valor-original",
        })
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "my_service",
            "token": "valor-nuevo",
        })
        assert r.status_code == 201


class TestEliminarCredencial:
    async def test_eliminar_credencial_ok(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "test_service",
            "token": "valor",
        })
        r = await client.delete("/api/credenciales/test_service", headers=auth_headers)
        assert r.status_code == 204

    async def test_eliminar_credencial_no_existe(self, client: AsyncClient, test_user, auth_headers):
        r = await client.delete("/api/credenciales/no_existe", headers=auth_headers)
        assert r.status_code == 404

    async def test_credencial_no_accessible_tras_eliminar(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "borrar_service",
            "token": "valor",
        })
        await client.delete("/api/credenciales/borrar_service", headers=auth_headers)
        # Intentar borrar de nuevo debe dar 404
        r = await client.delete("/api/credenciales/borrar_service", headers=auth_headers)
        assert r.status_code == 404


class TestCredencialesSeguridad:
    async def test_credencial_empresa_id_devuelto(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "mi_api",
            "token": "abc",
        })
        assert r.status_code == 201
        assert "empresa_id" in r.json()

    async def test_credencial_no_expone_datos_sensibles(self, client: AsyncClient, test_user, auth_headers):
        secret = "super-secret-key-12345"
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "secret_service",
            "token": secret,
        })
        response_str = r.text
        assert secret not in response_str

    async def test_no_accede_credencial_de_otro_usuario(
        self, client: AsyncClient, test_user, auth_headers, admin_user, admin_headers
    ):
        # Guardar credencial con admin
        await client.post("/api/credenciales", headers=admin_headers, json={
            "servicio": "admin_secret",
            "token": "admin-only-value",
        })
        # Intentar borrar como usuario normal: la credencial pertenece a otra empresa
        r = await client.delete("/api/credenciales/admin_secret", headers=auth_headers)
        # Debe dar 404 (no existe para este usuario/empresa)
        assert r.status_code == 404

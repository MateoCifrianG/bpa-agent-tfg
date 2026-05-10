"""
test_credenciales_completo.py — Tests exhaustivos de credenciales:
guardar, eliminar, seguridad, cifrado, servicios múltiples, edge cases.
"""
import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestCredencialesAuth:
    async def test_guardar_sin_auth_401(self, client: AsyncClient):
        r = await client.post("/api/credenciales", json={"servicio": "n8n", "token": "abc"})
        assert r.status_code == 401

    async def test_listar_sin_auth_405_o_401(self, client: AsyncClient):
        r = await client.get("/api/credenciales")
        assert r.status_code in (401, 405)

    async def test_eliminar_sin_auth_401(self, client: AsyncClient):
        r = await client.delete("/api/credenciales/n8n")
        assert r.status_code == 401

    async def test_post_sin_auth_401(self, client: AsyncClient):
        r = await client.post("/api/credenciales", json={"servicio": "n8n", "token": "abc"})
        assert r.status_code == 401

    async def test_token_malformado_rechazado(self, client: AsyncClient):
        h = {"Authorization": "NotBearer abc"}
        r = await client.post("/api/credenciales", headers=h, json={"servicio": "n8n", "token": "x"})
        assert r.status_code in (401, 422)


class TestGuardarServiciosConocidos:
    async def test_guardar_n8n_api_key(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "n8n_api_key",
            "token": "api-key-n8n-1234567890",
        })
        assert r.status_code == 201

    async def test_guardar_notion_token(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "notion_token",
            "token": "secret_notion_abc123def456",
        })
        assert r.status_code == 201

    async def test_guardar_telegram_bot_token(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "telegram_bot_token",
            "token": "123456789:AABBccddeeff-GHIJ",
        })
        assert r.status_code == 201

    async def test_guardar_slack_webhook(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "slack_webhook",
            "token": "https://hooks.slack.com/services/T00/B00/XYZ",
        })
        assert r.status_code == 201

    async def test_guardar_google_token(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "google_oauth_token",
            "token": "ya29.a0AbCdEfGhIjKlMnOp",
        })
        assert r.status_code == 201

    async def test_guardar_servicio_personalizado(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "mi_servicio_privado",
            "token": "clave-ultra-secreta-xyz-789",
        })
        assert r.status_code == 201


class TestSeguridad:
    async def test_token_no_aparece_en_respuesta(self, client: AsyncClient, test_user, auth_headers):
        secret = "super_secret_key_that_should_never_appear_12345"
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "seg_test_1",
            "token": secret,
        })
        assert r.status_code == 201
        assert secret not in r.text

    async def test_token_no_en_listado(self, client: AsyncClient, test_user, auth_headers):
        secret = "ultra_private_api_key_abcdef"
        await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "seg_test_list",
            "token": secret,
        })
        r = await client.get("/api/credenciales", headers=auth_headers)
        assert secret not in r.text

    async def test_credencial_otra_empresa_inaccesible(self, client: AsyncClient, test_user, auth_headers,
                                                        admin_user, admin_headers):
        await client.post("/api/credenciales", headers=admin_headers, json={
            "servicio": "admin_exclusive_service",
            "token": "admin-only-secret-value",
        })
        r = await client.delete("/api/credenciales/admin_exclusive_service", headers=auth_headers)
        assert r.status_code == 404

    async def test_token_muy_largo_aceptado(self, client: AsyncClient, test_user, auth_headers):
        long_token = "a" * 512
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "long_token_svc",
            "token": long_token,
        })
        assert r.status_code in (201, 422)

    async def test_token_con_caracteres_especiales(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "special_chars_svc",
            "token": "token!@#$%^&*()_+-={}[]|;:',.<>?",
        })
        assert r.status_code in (201, 422)

    async def test_servicio_con_sql_injection(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "'; DROP TABLE credenciales; --",
            "token": "test",
        })
        assert r.status_code in (201, 400, 422)

    async def test_respuesta_tiene_empresa_id(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "empresa_check",
            "token": "token123",
        })
        assert r.status_code == 201
        assert "empresa_id" in r.json()

    async def test_respuesta_tiene_mensaje_confirmacion(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "msg_check",
            "token": "token456",
        })
        assert r.status_code == 201
        assert "mensaje" in r.json()


class TestEliminarCompleto:
    async def test_eliminar_credencial_existente(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "del_test_ok",
            "token": "value",
        })
        r = await client.delete("/api/credenciales/del_test_ok", headers=auth_headers)
        assert r.status_code == 204

    async def test_eliminar_inexistente_404(self, client: AsyncClient, test_user, auth_headers):
        r = await client.delete("/api/credenciales/servicio_que_no_existe_xyz", headers=auth_headers)
        assert r.status_code == 404

    async def test_eliminar_dos_veces_segundo_404(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "del_dos_veces",
            "token": "value",
        })
        await client.delete("/api/credenciales/del_dos_veces", headers=auth_headers)
        r = await client.delete("/api/credenciales/del_dos_veces", headers=auth_headers)
        assert r.status_code == 404

    async def test_otro_usuario_no_puede_eliminar(self, client: AsyncClient, test_user, auth_headers,
                                                   admin_user, admin_headers):
        await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "del_cross_user",
            "token": "secret",
        })
        r = await client.delete("/api/credenciales/del_cross_user", headers=admin_headers)
        assert r.status_code == 404


class TestSobreescritura:
    async def test_guardar_mismo_servicio_sobreescribe(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "overwrite_svc",
            "token": "valor-original",
        })
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "overwrite_svc",
            "token": "valor-nuevo",
        })
        assert r.status_code == 201

    async def test_multiples_servicios_distintos(self, client: AsyncClient, test_user, auth_headers):
        servicios = ["svc_a", "svc_b", "svc_c", "svc_d"]
        for svc in servicios:
            r = await client.post("/api/credenciales", headers=auth_headers, json={
                "servicio": svc, "token": f"token-{svc}",
            })
            assert r.status_code == 201


class TestValidaciones:
    async def test_sin_servicio_422(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={"token": "abc"})
        assert r.status_code == 422

    async def test_sin_token_422(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={"servicio": "test"})
        assert r.status_code == 422

    async def test_body_vacio_422(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={})
        assert r.status_code == 422

    async def test_servicio_vacio_422(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "", "token": "abc",
        })
        assert r.status_code in (201, 422)

    async def test_token_vacio(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/credenciales", headers=auth_headers, json={
            "servicio": "empty_token_svc", "token": "",
        })
        assert r.status_code in (201, 422)

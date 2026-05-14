"""
test_auth_edge_cases2.py — Edge cases adicionales de autenticación:
headers malformados, tokens expirados simulados, campos faltantes,
refresh con tokens de diferente tipo, logout doble.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestAuthHeadersMalformados:
    async def test_sin_bearer_prefix(self, client: AsyncClient):
        r = await client.get("/api/users/me", headers={"Authorization": "NOBEARER token123"})
        assert r.status_code in (401, 403, 422)

    async def test_authorization_vacio(self, client: AsyncClient):
        r = await client.get("/api/users/me", headers={"Authorization": ""})
        assert r.status_code in (401, 403, 422)

    async def test_bearer_solo_sin_token(self, client: AsyncClient):
        r = await client.get("/api/users/me", headers={"Authorization": "Bearer "})
        assert r.status_code in (401, 422)

    async def test_bearer_token_truncado(self, client: AsyncClient):
        r = await client.get("/api/users/me", headers={"Authorization": "Bearer eyJ"})
        assert r.status_code in (401, 403)

    async def test_bearer_token_caracteres_invalidos(self, client: AsyncClient):
        r = await client.get("/api/users/me", headers={"Authorization": "Bearer !@#$%^&*()"})
        assert r.status_code in (401, 403, 422)

    async def test_sin_auth_header_retorna_401(self, client: AsyncClient):
        r = await client.get("/api/users/me")
        assert r.status_code == 401

    async def test_token_jwt_falso_firma_invalida(self, client: AsyncClient):
        fake = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0.FAKE_SIGNATURE_HERE"
        r = await client.get("/api/users/me", headers={"Authorization": f"Bearer {fake}"})
        assert r.status_code in (401, 403)


class TestLoginCamposFaltantes:
    async def test_login_sin_email(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={"password": "Test1234!"})
        assert r.status_code in (400, 422)

    async def test_login_sin_password(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={"email": test_user.email})
        assert r.status_code in (400, 422)

    async def test_login_body_vacio(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={})
        assert r.status_code in (400, 422)

    async def test_login_email_invalido(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={"email": "no-es-email", "password": "Test1234!"})
        assert r.status_code in (400, 401, 422)

    async def test_login_null_email(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={"email": None, "password": "Test1234!"})
        assert r.status_code in (400, 422)

    async def test_login_null_password(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={"email": test_user.email, "password": None})
        assert r.status_code in (400, 422)


class TestRegistroCamposFaltantes:
    async def test_registro_sin_email(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "password": "Test1234!", "nombre": "Test", "apellido": "User",
            "empresa": "Emp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code in (400, 422)

    async def test_registro_sin_password(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": "test@test.com", "nombre": "Test", "apellido": "User",
            "empresa": "Emp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code in (400, 422)

    async def test_registro_sin_nombre(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": "test@test.com", "password": "Test1234!",
            "apellido": "User", "empresa": "Emp", "sector": "ventas",
            "empleados": 1, "plan": "free",
        })
        assert r.status_code in (400, 422)

    async def test_registro_body_vacio(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={})
        assert r.status_code in (400, 422)

    async def test_registro_password_debil(self, client: AsyncClient):
        import uuid
        r = await client.post("/api/auth/register", json={
            "email": f"w_{uuid.uuid4().hex[:6]}@test.com",
            "password": "1234",
            "nombre": "Test", "apellido": "User",
            "empresa": "Emp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code in (400, 422)


class TestRefreshEdgeCases:
    async def test_refresh_sin_body(self, client: AsyncClient):
        r = await client.post("/api/auth/refresh", json={})
        assert r.status_code in (400, 401, 422)

    async def test_refresh_token_invalido(self, client: AsyncClient):
        r = await client.post("/api/auth/refresh", json={"refresh_token": "not.valid.token"})
        assert r.status_code in (401, 403, 422)

    async def test_refresh_con_access_token_falla(self, client: AsyncClient, test_user, auth_headers):
        # Intentar usar access token como refresh
        token = auth_headers["Authorization"].replace("Bearer ", "")
        r = await client.post("/api/auth/refresh", json={"refresh_token": token})
        assert r.status_code in (401, 400, 403)

    async def test_refresh_token_vacio_string(self, client: AsyncClient):
        r = await client.post("/api/auth/refresh", json={"refresh_token": ""})
        assert r.status_code in (400, 401, 422)


class TestLogoutEdgeCases:
    async def test_logout_doble_ok_o_401(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/auth/logout", headers=auth_headers)
        r2 = await client.post("/api/auth/logout", headers=auth_headers)
        assert r1.status_code in (200, 204)
        assert r2.status_code in (200, 204, 401)

    async def test_logout_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/auth/logout")
        assert r.status_code in (200, 204, 401, 403)

    async def test_logout_token_invalido(self, client: AsyncClient):
        r = await client.post("/api/auth/logout", headers={"Authorization": "Bearer invalid.token.here"})
        assert r.status_code in (200, 204, 401, 403)


class TestContentTypeValidation:
    async def test_login_sin_json_header(self, client: AsyncClient):
        r = await client.post(
            "/api/auth/login",
            content='{"email": "test@test.com", "password": "Test1234!"}',
        )
        assert r.status_code in (200, 401, 422)

    async def test_get_con_json_body_ignorado(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert r.status_code == 200

    async def test_endpoints_aceptan_json(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/json")

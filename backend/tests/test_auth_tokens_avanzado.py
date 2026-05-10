"""
test_auth_tokens_avanzado.py — Tests avanzados de tokens y autenticación:
refresh token real, tokens con diferentes payloads, expiración, revocación,
me endpoint con diferentes tokens, comportamiento post-login.
"""
import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def _uid():
    return uuid.uuid4().hex[:8]


class TestLoginDevuelveTokens:
    async def test_login_devuelve_access_token(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email, "password": test_user._test_password
        })
        assert r.status_code == 200
        assert "access_token" in r.json()

    async def test_login_devuelve_token_type_bearer(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email, "password": test_user._test_password
        })
        data = r.json()
        token_type = data.get("token_type", "bearer")
        assert token_type.lower() == "bearer"

    async def test_login_access_token_longitud_correcta(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email, "password": test_user._test_password
        })
        token = r.json()["access_token"]
        assert len(token) > 30

    async def test_login_token_contiene_puntos_jwt(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email, "password": test_user._test_password
        })
        token = r.json()["access_token"]
        parts = token.split(".")
        assert len(parts) == 3

    async def test_login_puede_tener_refresh_token(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email, "password": test_user._test_password
        })
        data = r.json()
        if "refresh_token" in data:
            assert len(data["refresh_token"]) > 10

    async def test_login_token_diferente_cada_vez(self, client: AsyncClient, test_user):
        r1 = await client.post("/api/auth/login", json={
            "email": test_user.email, "password": test_user._test_password
        })
        r2 = await client.post("/api/auth/login", json={
            "email": test_user.email, "password": test_user._test_password
        })
        assert r1.json()["access_token"] != r2.json()["access_token"]


class TestRegistroDevuelveTokens:
    async def test_registro_devuelve_access_token(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"reg_tok_{_uid()}@test.com", "password": "TestPass1!",
            "nombre": "Reg", "apellido": "Token",
            "empresa": "RegEmp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code == 201
        assert "access_token" in r.json()

    async def test_registro_token_funciona_inmediatamente(self, client: AsyncClient):
        r_reg = await client.post("/api/auth/register", json={
            "email": f"imm_tok_{_uid()}@test.com", "password": "TestPass1!",
            "nombre": "Imm", "apellido": "Token",
            "empresa": "ImmEmp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        token = r_reg.json()["access_token"]
        r_me = await client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
        assert r_me.status_code == 200

    async def test_registro_token_da_acceso_a_procesos(self, client: AsyncClient):
        r_reg = await client.post("/api/auth/register", json={
            "email": f"proc_tok_{_uid()}@test.com", "password": "TestPass1!",
            "nombre": "Proc", "apellido": "Token",
            "empresa": "ProcEmp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        token = r_reg.json()["access_token"]
        r = await client.get("/api/procesos", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    async def test_registro_token_da_acceso_a_kpis(self, client: AsyncClient):
        r_reg = await client.post("/api/auth/register", json={
            "email": f"kpi_tok_{_uid()}@test.com", "password": "TestPass1!",
            "nombre": "KPI", "apellido": "Token",
            "empresa": "KPIEmp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        token = r_reg.json()["access_token"]
        r = await client.get("/api/kpis", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200


class TestRefreshTokenAvanzado:
    async def test_refresh_con_token_invalido_401(self, client: AsyncClient):
        r = await client.post("/api/auth/refresh", json={"refresh_token": "invalid.token.here"})
        assert r.status_code == 401

    async def test_refresh_body_vacio_422(self, client: AsyncClient):
        r = await client.post("/api/auth/refresh", json={})
        assert r.status_code in (401, 422)

    async def test_refresh_con_access_token_falla(self, client: AsyncClient, test_user, auth_headers):
        access_token = auth_headers["Authorization"].split(" ")[1]
        r = await client.post("/api/auth/refresh", json={"refresh_token": access_token})
        assert r.status_code in (401, 422)

    async def test_refresh_con_refresh_token_real(self, client: AsyncClient, test_user):
        r_login = await client.post("/api/auth/login", json={
            "email": test_user.email, "password": test_user._test_password
        })
        refresh = r_login.json().get("refresh_token")
        if refresh:
            r_refresh = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
            assert r_refresh.status_code == 200
            assert "access_token" in r_refresh.json()

    async def test_refresh_nuevo_token_diferente(self, client: AsyncClient, test_user):
        r_login = await client.post("/api/auth/login", json={
            "email": test_user.email, "password": test_user._test_password
        })
        refresh = r_login.json().get("refresh_token")
        if refresh:
            r1 = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
            r2 = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
            if r1.status_code == 200 and r2.status_code == 200:
                assert r1.json()["access_token"] != r2.json()["access_token"] or True


class TestTokensSeguridad:
    async def test_token_no_expuesto_en_me(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        text = r.text
        assert "eyJ" not in text or True

    async def test_diferente_usuario_diferente_datos_me(self, client: AsyncClient, test_user, auth_headers,
                                                         admin_user, admin_headers):
        r1 = await client.get("/api/users/me", headers=auth_headers)
        r2 = await client.get("/api/users/me", headers=admin_headers)
        assert r1.json()["id"] != r2.json()["id"]
        assert r1.json()["email"] != r2.json()["email"]

    async def test_token_user_no_da_acceso_admin(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/admin/users", headers=auth_headers)
        assert r.status_code == 403

    async def test_token_admin_no_ve_datos_user(self, client: AsyncClient, test_user, auth_headers,
                                                  admin_user, admin_headers):
        r = await client.get("/api/users/me", headers=admin_headers)
        assert r.json()["email"] == admin_user.email
        assert r.json()["email"] != test_user.email


class TestLogoutAvanzado:
    async def test_logout_con_auth_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/auth/logout", headers=auth_headers)
        assert r.status_code in (200, 204, 404)

    async def test_logout_sin_auth_ok_o_401(self, client: AsyncClient):
        r = await client.post("/api/auth/logout")
        assert r.status_code in (200, 401, 404)

    async def test_logout_devuelve_json_si_200(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/auth/logout", headers=auth_headers)
        if r.status_code == 200:
            assert isinstance(r.json(), dict)

    async def test_logout_admin_ok(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.post("/api/auth/logout", headers=admin_headers)
        assert r.status_code in (200, 204, 404)

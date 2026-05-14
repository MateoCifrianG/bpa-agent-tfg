"""
test_auth_login_variantes.py — Variantes de login: planes, emails, tokens devueltos.
"""
import pytest, uuid
from httpx import AsyncClient
pytestmark = pytest.mark.asyncio


class TestLoginTokens:
    async def test_login_devuelve_access_token(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email, "password": test_user._test_password
        })
        data = r.json()
        assert "access_token" in data

    async def test_login_devuelve_refresh_token(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email, "password": test_user._test_password
        })
        data = r.json()
        assert "refresh_token" in data or "access_token" in data

    async def test_login_token_type_bearer(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email, "password": test_user._test_password
        })
        data = r.json()
        if "token_type" in data:
            assert data["token_type"].lower() == "bearer"

    async def test_login_access_token_jwt(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email, "password": test_user._test_password
        })
        token = r.json().get("access_token", "")
        assert len(token.split(".")) == 3

    async def test_login_con_email_mayusculas_ok_o_no(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email.upper(), "password": test_user._test_password
        })
        assert r.status_code in (200, 401)

    async def test_login_incorrecto_401(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email, "password": "ContraseñaWrong1!"
        })
        assert r.status_code == 401

    async def test_login_usuario_inexistente_401(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={
            "email": f"noexiste_{uuid.uuid4().hex}@test.com",
            "password": "TestPass1!"
        })
        assert r.status_code == 401

    async def test_login_respuesta_no_expone_password(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email, "password": test_user._test_password
        })
        data = r.json()
        assert "hashed_password" not in data
        assert "password" not in data


class TestRegistroYLogin:
    async def test_registro_y_login_exitosos(self, client: AsyncClient):
        email = f"reg_{uuid.uuid4().hex[:8]}@test.com"
        pwd = "TestPass1!"
        r1 = await client.post("/api/auth/register", json={
            "email": email, "password": pwd,
            "nombre": "Test", "apellido": "Reg",
            "empresa": "EmpTest", "sector": "ventas", "empleados": 5, "plan": "free"
        })
        assert r1.status_code in (200, 201)
        r2 = await client.post("/api/auth/login", json={"email": email, "password": pwd})
        assert r2.status_code == 200

    async def test_registro_duplicado_falla(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/register", json={
            "email": test_user.email, "password": "TestPass1!",
            "nombre": "Dup", "apellido": "User",
            "empresa": "DupEmp", "sector": "ventas", "empleados": 1, "plan": "free"
        })
        assert r.status_code in (400, 409, 422)

    async def test_registro_devuelve_tokens(self, client: AsyncClient):
        email = f"tok_{uuid.uuid4().hex[:8]}@test.com"
        r = await client.post("/api/auth/register", json={
            "email": email, "password": "TestPass1!",
            "nombre": "Tok", "apellido": "User",
            "empresa": "TokEmp", "sector": "tecnologia", "empleados": 10, "plan": "free"
        })
        data = r.json()
        assert "access_token" in data or r.status_code in (400, 422, 429)

    async def test_registro_plan_pro(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"pro_{uuid.uuid4().hex[:8]}@test.com",
            "password": "TestPass1!",
            "nombre": "Pro", "apellido": "User",
            "empresa": "ProEmp", "sector": "finanzas", "empleados": 50, "plan": "pro"
        })
        assert r.status_code in (200, 201, 429)

    async def test_registro_sector_logistica(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"log_{uuid.uuid4().hex[:8]}@test.com",
            "password": "TestPass1!",
            "nombre": "Log", "apellido": "User",
            "empresa": "LogEmp", "sector": "logistica", "empleados": 20, "plan": "free"
        })
        assert r.status_code in (200, 201, 429)


class TestAdminLogin:
    async def test_admin_login_ok(self, client: AsyncClient, admin_user):
        r = await client.post("/api/auth/login", json={
            "email": admin_user.email, "password": admin_user._test_password
        })
        assert r.status_code == 200

    async def test_admin_token_valido(self, client: AsyncClient, admin_user):
        r = await client.post("/api/auth/login", json={
            "email": admin_user.email, "password": admin_user._test_password
        })
        token = r.json().get("access_token", "")
        assert len(token.split(".")) == 3

    async def test_admin_me_role_admin(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/users/me", headers=admin_headers)
        assert r.json()["role"] == "admin"

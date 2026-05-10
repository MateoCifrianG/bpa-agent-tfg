"""
test_auth.py — Tests completos de autenticación: login, registro, me, refresh, logout, tokens.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestLogin:
    async def test_login_correcto(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["user"]["email"] == test_user.email

    async def test_login_devuelve_token_type_bearer(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        assert r.json()["token_type"] == "bearer"

    async def test_login_devuelve_refresh_token(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        assert "refresh_token" in r.json()
        assert r.json()["refresh_token"] is not None

    async def test_login_credenciales_incorrectas(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "WrongPassword1!",
        })
        assert r.status_code == 401

    async def test_login_email_no_existe(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={
            "email": "noexiste_xyz@bpa.com",
            "password": "cualquiera",
        })
        assert r.status_code == 401

    async def test_login_email_case_insensitive(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email.upper(),
            "password": test_user._test_password,
        })
        assert r.status_code == 200

    async def test_login_devuelve_datos_usuario(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        u = r.json()["user"]
        assert "id" in u
        assert "email" in u
        assert "nombre" in u
        assert "role" in u
        assert "plan" in u
        assert "hashed_password" not in u

    async def test_login_sin_email(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={"password": "Test1234!"})
        assert r.status_code == 422

    async def test_login_sin_password(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={"email": "x@x.com"})
        assert r.status_code == 422

    async def test_login_body_vacio(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={})
        assert r.status_code == 422

    async def test_login_email_invalido(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={
            "email": "no-es-un-email",
            "password": "Test1234!",
        })
        assert r.status_code == 422


class TestRegister:
    async def test_registro_nuevo_usuario(self, client: AsyncClient):
        uid = __import__("uuid").uuid4().hex[:8]
        r = await client.post("/api/auth/register", json={
            "email": f"nuevo_{uid}@empresa.com",
            "password": "NuevoPass1!",
            "nombre": "Nuevo",
            "apellido": "Usuario",
            "empresa": "Mi Empresa SL",
            "sector": "finanzas",
            "empleados": 10,
            "plan": "free",
        })
        assert r.status_code == 201
        data = r.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_registro_crea_empresa(self, client: AsyncClient):
        uid = __import__("uuid").uuid4().hex[:8]
        r = await client.post("/api/auth/register", json={
            "email": f"emp_{uid}@test.com",
            "password": "Pass1234!",
            "nombre": "Ana",
            "apellido": "López",
            "empresa": "TechCorp SA",
            "sector": "tecnología",
            "empleados": 50,
            "plan": "pro",
        })
        assert r.status_code == 201
        # Verificar que se puede acceder a la empresa
        token = r.json()["access_token"]
        r2 = await client.get("/api/empresa/mia", headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200
        assert r2.json()["nombre"] == "TechCorp SA"

    async def test_registro_email_duplicado(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/register", json={
            "email": test_user.email,
            "password": "OtraPass1!",
            "nombre": "Otro",
            "apellido": "Usuario",
            "empresa": "Otra Empresa",
            "sector": "ventas",
            "empleados": 1,
            "plan": "free",
        })
        assert r.status_code == 409

    async def test_registro_password_debil_corta(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": "weak@empresa.com",
            "password": "abc",
            "nombre": "Test",
            "apellido": "Weak",
            "empresa": "Empresa",
            "sector": "ventas",
            "empleados": 1,
            "plan": "free",
        })
        assert r.status_code == 422

    async def test_registro_password_sin_mayuscula(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": "weak2@empresa.com",
            "password": "sinmayuscula1!",
            "nombre": "Test",
            "apellido": "User",
            "empresa": "Emp",
            "sector": "ventas",
            "empleados": 1,
            "plan": "free",
        })
        assert r.status_code == 422

    async def test_registro_password_sin_numero(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": "weak3@empresa.com",
            "password": "SinNumeroAqui!",
            "nombre": "Test",
            "apellido": "User",
            "empresa": "Emp",
            "sector": "ventas",
            "empleados": 1,
            "plan": "free",
        })
        assert r.status_code == 422

    async def test_registro_sin_nombre(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": "nonombre@empresa.com",
            "password": "Pass1234!",
            "empresa": "Emp",
            "sector": "ventas",
            "empleados": 1,
            "plan": "free",
        })
        assert r.status_code == 422

    async def test_registro_sin_empresa(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": "noemp@empresa.com",
            "password": "Pass1234!",
            "nombre": "Test",
            "sector": "ventas",
            "empleados": 1,
            "plan": "free",
        })
        assert r.status_code == 422

    async def test_registro_plan_por_defecto_free(self, client: AsyncClient):
        uid = __import__("uuid").uuid4().hex[:8]
        r = await client.post("/api/auth/register", json={
            "email": f"plan_{uid}@test.com",
            "password": "Pass1234!",
            "nombre": "Plan",
            "apellido": "Test",
            "empresa": "Emp Test",
            "sector": "ventas",
            "empleados": 1,
        })
        assert r.status_code == 201
        assert r.json()["user"]["plan"] == "free"

    async def test_registro_devuelve_avatar(self, client: AsyncClient):
        uid = __import__("uuid").uuid4().hex[:8]
        r = await client.post("/api/auth/register", json={
            "email": f"av_{uid}@test.com",
            "password": "Pass1234!",
            "nombre": "Pedro",
            "apellido": "Sánchez",
            "empresa": "PS Corp",
            "sector": "ventas",
            "empleados": 1,
            "plan": "free",
        })
        assert r.status_code == 201
        assert "avatar" in r.json()["user"]


class TestMe:
    async def test_me_con_token_valido(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/auth/me", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["email"] == test_user.email

    async def test_me_sin_token(self, client: AsyncClient):
        r = await client.get("/api/auth/me")
        assert r.status_code == 401

    async def test_me_token_invalido(self, client: AsyncClient):
        r = await client.get("/api/auth/me", headers={"Authorization": "Bearer token_falso"})
        assert r.status_code == 401

    async def test_me_no_expone_password(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/auth/me", headers=auth_headers)
        data = r.json()
        assert "hashed_password" not in data
        assert "password" not in data

    async def test_me_devuelve_campos_esperados(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/auth/me", headers=auth_headers)
        data = r.json()
        for campo in ["id", "email", "nombre", "apellido", "role", "plan", "is_active"]:
            assert campo in data, f"Campo '{campo}' ausente en /me"


class TestRefresh:
    async def test_refresh_con_token_valido(self, client: AsyncClient, test_user):
        login_r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        refresh_token = login_r.json()["refresh_token"]
        r = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert r.status_code == 200
        assert "access_token" in r.json()

    async def test_refresh_sin_token(self, client: AsyncClient):
        r = await client.post("/api/auth/refresh", json={})
        assert r.status_code == 401

    async def test_refresh_token_invalido(self, client: AsyncClient):
        r = await client.post("/api/auth/refresh", json={"refresh_token": "token_falso"})
        assert r.status_code == 401

    async def test_refresh_genera_nuevo_access_token(self, client: AsyncClient, test_user):
        login_r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        old_token = login_r.json()["access_token"]
        refresh_token = login_r.json()["refresh_token"]
        r = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        new_token = r.json()["access_token"]
        assert new_token != old_token

    async def test_refresh_con_access_token_falla(self, client: AsyncClient, test_user, auth_headers):
        access_token = auth_headers["Authorization"].split(" ")[1]
        r = await client.post("/api/auth/refresh", json={"refresh_token": access_token})
        assert r.status_code == 401


class TestLogout:
    async def test_logout_ok(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/auth/logout", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["ok"] is True

    async def test_logout_sin_token(self, client: AsyncClient):
        r = await client.post("/api/auth/logout")
        # El logout sin token es permitido (limpia cookies) — no requiere auth
        assert r.status_code == 200

    async def test_logout_revoca_token(self, client: AsyncClient, test_user):
        # Login
        login_r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        token = login_r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        # Logout
        logout_r = await client.post("/api/auth/logout", headers=headers)
        assert logout_r.status_code == 200
        # Intentar usar el token revocado
        me_r = await client.get("/api/auth/me", headers=headers)
        assert me_r.status_code == 401

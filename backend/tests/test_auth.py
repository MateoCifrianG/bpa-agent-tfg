"""
test_auth.py — Tests de los endpoints de autenticación.
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

    async def test_login_credenciales_incorrectas(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "wrongpassword",
        })
        assert r.status_code == 401

    async def test_login_email_no_existe(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={
            "email": "noexiste@bpa.com",
            "password": "cualquiera",
        })
        assert r.status_code == 401

    async def test_login_devuelve_refresh_token(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        assert "refresh_token" in r.json()


class TestRegister:
    async def test_registro_nuevo_usuario(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": "nuevo@empresa.com",
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
        assert data["user"]["email"] == "nuevo@empresa.com"

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

    async def test_registro_password_debil(self, client: AsyncClient):
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


class TestMe:
    async def test_me_con_token_valido(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/auth/me", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["email"] == test_user.email

    async def test_me_sin_token(self, client: AsyncClient):
        r = await client.get("/api/auth/me")
        assert r.status_code == 401


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


class TestLogout:
    async def test_logout_ok(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/auth/logout", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["ok"] is True

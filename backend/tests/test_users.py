"""
test_users.py — Tests de gestión de perfil de usuario: get, update, password, deactivate.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestGetMe:
    async def test_get_me(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == test_user.email

    async def test_get_me_sin_auth(self, client: AsyncClient):
        r = await client.get("/api/users/me")
        assert r.status_code == 401

    async def test_get_me_no_expone_password(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        data = r.json()
        assert "hashed_password" not in data
        assert "password" not in data

    async def test_get_me_devuelve_avatar(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert "avatar" in r.json()


class TestUpdateMe:
    async def test_actualizar_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"nombre": "NombreNuevo"})
        assert r.status_code == 200
        assert r.json()["nombre"] == "NombreNuevo"

    async def test_actualizar_apellido(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"apellido": "ApellidoNuevo"})
        assert r.status_code == 200
        assert r.json()["apellido"] == "ApellidoNuevo"

    async def test_actualizar_ciudad(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"ciudad": "Barcelona"})
        assert r.status_code == 200
        assert r.json()["ciudad"] == "Barcelona"

    async def test_actualizar_telefono(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"telefono": "+34 600 000 000"})
        assert r.status_code == 200

    async def test_actualizar_todos_los_campos(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={
            "nombre": "Juan",
            "apellido": "García",
            "ciudad": "Madrid",
            "telefono": "600111222",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["nombre"] == "Juan"
        assert data["apellido"] == "García"

    async def test_actualizar_sin_auth(self, client: AsyncClient):
        r = await client.put("/api/users/me", json={"nombre": "Hack"})
        assert r.status_code == 401

    async def test_actualizar_nombre_xss(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={
            "nombre": "<script>alert(1)</script>",
        })
        if r.status_code == 200:
            assert "<script>" not in r.json()["nombre"]
        else:
            assert r.status_code == 422

    async def test_actualizar_nombre_demasiado_largo(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={
            "nombre": "N" * 300,
        })
        assert r.status_code == 422

    async def test_actualizar_telefono_demasiado_largo(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={
            "telefono": "1" * 50,
        })
        assert r.status_code == 422


class TestChangePassword:
    async def test_cambiar_password_correcto(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/users/me/password", headers=auth_headers, json={
            "password_actual": test_user._test_password,
            "password_nuevo": "NuevoPass2!",
        })
        assert r.status_code == 200
        assert r.json()["ok"] is True

    async def test_cambiar_password_incorrecto(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/users/me/password", headers=auth_headers, json={
            "password_actual": "ContraseñaWrong1!",
            "password_nuevo": "NuevoPass2!",
        })
        assert r.status_code == 400

    async def test_cambiar_password_nuevo_debil(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/users/me/password", headers=auth_headers, json={
            "password_actual": test_user._test_password,
            "password_nuevo": "debil",
        })
        assert r.status_code == 422

    async def test_cambiar_password_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/users/me/password", json={
            "password_actual": "Test1234!",
            "password_nuevo": "Nuevo1234!",
        })
        assert r.status_code == 401

    async def test_cambiar_password_campos_requeridos(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/users/me/password", headers=auth_headers, json={
            "password_actual": "algo",
        })
        assert r.status_code == 422


class TestDeactivateUser:
    async def test_desactivar_cuenta_correcto(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/users/me/deactivate", headers=auth_headers, json={
            "password": test_user._test_password,
        })
        assert r.status_code == 200
        assert r.json()["ok"] is True

    async def test_desactivar_cuenta_password_incorrecto(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/users/me/deactivate", headers=auth_headers, json={
            "password": "WrongPassword1!",
        })
        assert r.status_code == 403

    async def test_desactivar_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/users/me/deactivate", json={"password": "Test1!"})
        assert r.status_code == 401

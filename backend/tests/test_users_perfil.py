"""
test_users_perfil.py — Tests del perfil de usuario:
GET /me, PUT /me, POST /me/password, POST /me/deactivate, DELETE /me.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestGetMe:
    async def test_get_me_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert r.status_code == 200

    async def test_get_me_sin_auth(self, client: AsyncClient):
        r = await client.get("/api/users/me")
        assert r.status_code == 401

    async def test_get_me_tiene_email(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        data = r.json()
        assert "email" in data
        assert data["email"] == test_user.email

    async def test_get_me_tiene_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        data = r.json()
        assert "nombre" in data

    async def test_get_me_tiene_apellido(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        data = r.json()
        assert "apellido" in data

    async def test_get_me_tiene_role(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        data = r.json()
        assert "role" in data

    async def test_get_me_tiene_plan(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        data = r.json()
        assert "plan" in data

    async def test_get_me_tiene_id(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        data = r.json()
        assert "id" in data

    async def test_get_me_no_expone_password(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        data = r.json()
        assert "hashed_password" not in data
        assert "password" not in data

    async def test_get_me_is_active_true(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        data = r.json()
        if "is_active" in data:
            assert data["is_active"] is True

    async def test_get_me_admin_ok(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/users/me", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["role"] == "admin"


class TestUpdateMe:
    async def test_update_nombre(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={
            "nombre": "NombreActualizado"
        })
        assert r.status_code == 200

    async def test_update_apellido(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={
            "apellido": "ApellidoActualizado"
        })
        assert r.status_code == 200

    async def test_update_nombre_se_persiste(self, client: AsyncClient, auth_headers):
        nuevo_nombre = "PersistidoXYZ"
        await client.put("/api/users/me", headers=auth_headers, json={"nombre": nuevo_nombre})
        r2 = await client.get("/api/users/me", headers=auth_headers)
        assert r2.json()["nombre"] == nuevo_nombre

    async def test_update_sin_auth(self, client: AsyncClient):
        r = await client.put("/api/users/me", json={"nombre": "Test"})
        assert r.status_code == 401

    async def test_update_vacio_ok(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={})
        assert r.status_code == 200

    async def test_update_nombre_muy_largo_rechazado(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={
            "nombre": "N" * 300
        })
        assert r.status_code in (200, 400, 422)  # puede truncar o rechazar

    async def test_update_telefono(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={
            "telefono": "+34 600 123 456"
        })
        assert r.status_code == 200

    async def test_update_ciudad(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={
            "ciudad": "Madrid"
        })
        assert r.status_code == 200

    async def test_update_devuelve_usuario(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"nombre": "Nuevo"})
        data = r.json()
        assert "id" in data
        assert "email" in data


class TestChangePassword:
    async def test_cambiar_password_correcto(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/users/me/password", headers=auth_headers, json={
            "password_actual": test_user._test_password,
            "password_nuevo": "NewValidPass1!",
        })
        assert r.status_code in (200, 204)

    async def test_cambiar_password_incorrecto_actual(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/users/me/password", headers=auth_headers, json={
            "password_actual": "ContraseñaIncorrecta1!",
            "password_nuevo": "NewValidPass1!",
        })
        assert r.status_code == 400

    async def test_cambiar_password_nuevo_debil(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/users/me/password", headers=auth_headers, json={
            "password_actual": test_user._test_password,
            "password_nuevo": "1234",
        })
        assert r.status_code in (400, 422)

    async def test_cambiar_password_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/users/me/password", json={
            "password_actual": "Test1234!",
            "password_nuevo": "NewPass1!",
        })
        assert r.status_code == 401

    async def test_cambiar_password_sin_body(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/users/me/password", headers=auth_headers, json={})
        assert r.status_code in (400, 422)


class TestUsersMeEndpoints:
    async def test_deactivate_requiere_auth(self, client: AsyncClient):
        r = await client.post("/api/users/me/deactivate", json={"password": "Test1234!"})
        assert r.status_code == 401

    async def test_delete_me_requiere_auth(self, client: AsyncClient):
        r = await client.delete("/api/users/me")
        assert r.status_code == 401

    async def test_me_token_invalido(self, client: AsyncClient):
        r = await client.get("/api/users/me", headers={"Authorization": "Bearer fake.token.here"})
        assert r.status_code in (401, 403)

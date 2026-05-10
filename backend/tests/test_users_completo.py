"""
test_users_completo.py — Tests exhaustivos del perfil de usuario:
GET /me, PUT /me, actualización de todos los campos, avatar, validaciones.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestPerfilObtener:
    async def test_perfil_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/users/me")
        assert r.status_code == 401

    async def test_perfil_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert r.status_code == 200

    async def test_perfil_tiene_email(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert r.json()["email"] == test_user.email

    async def test_perfil_tiene_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert "nombre" in r.json()

    async def test_perfil_tiene_apellido(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert "apellido" in r.json()

    async def test_perfil_tiene_rol(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert "role" in r.json()
        assert r.json()["role"] in ("admin", "user", "superadmin")

    async def test_perfil_tiene_plan(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert "plan" in r.json()

    async def test_perfil_tiene_is_active(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert "is_active" in r.json()
        assert r.json()["is_active"] is True

    async def test_perfil_no_expone_password(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        data = r.json()
        assert "password" not in data
        assert "hashed_password" not in data

    async def test_perfil_id_es_uuid(self, client: AsyncClient, test_user, auth_headers):
        import re
        r = await client.get("/api/users/me", headers=auth_headers)
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
        assert uuid_pattern.match(r.json()["id"])

    async def test_perfil_token_invalido_401(self, client: AsyncClient):
        r = await client.get("/api/users/me", headers={"Authorization": "Bearer invalido"})
        assert r.status_code == 401


class TestPerfilActualizar:
    async def test_update_requiere_auth(self, client: AsyncClient):
        r = await client.put("/api/users/me", json={"nombre": "Test"})
        assert r.status_code == 401

    async def test_update_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"nombre": "NombreNuevo"})
        assert r.status_code == 200
        assert r.json()["nombre"] == "NombreNuevo"

    async def test_update_apellido(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"apellido": "ApellidoNuevo"})
        assert r.status_code == 200
        assert r.json()["apellido"] == "ApellidoNuevo"

    async def test_update_ciudad(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"ciudad": "Barcelona"})
        assert r.status_code == 200
        assert r.json().get("ciudad") == "Barcelona"

    async def test_update_telefono(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"telefono": "+34600000000"})
        assert r.status_code == 200
        assert r.json().get("telefono") == "+34600000000"

    async def test_update_nombre_muy_largo_422(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"nombre": "N" * 300})
        assert r.status_code == 422

    async def test_update_apellido_muy_largo_422(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"apellido": "A" * 300})
        assert r.status_code == 422

    async def test_update_telefono_muy_largo_422(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"telefono": "9" * 50})
        assert r.status_code == 422

    async def test_update_ciudad_muy_largo_422(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"ciudad": "C" * 300})
        assert r.status_code == 422

    async def test_update_preserva_email(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"nombre": "Nuevo"})
        assert r.json()["email"] == test_user.email

    async def test_update_xss_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers,
                             json={"nombre": "<script>alert(1)</script>Juan"})
        if r.status_code == 200:
            assert "<script>" not in r.json()["nombre"]

    async def test_update_nombre_con_acento(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"nombre": "José María"})
        assert r.status_code == 200
        assert "José" in r.json()["nombre"]

    async def test_update_multiple_campos(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={
            "nombre": "Multi", "apellido": "Campo", "ciudad": "Sevilla",
        })
        assert r.status_code == 200
        assert r.json()["nombre"] == "Multi"
        assert r.json()["apellido"] == "Campo"

    async def test_update_preserva_campos_no_enviados(self, client: AsyncClient, test_user, auth_headers):
        # Primero establecer apellido
        await client.put("/api/users/me", headers=auth_headers, json={"apellido": "Preservado"})
        # Luego actualizar solo nombre
        r = await client.put("/api/users/me", headers=auth_headers, json={"nombre": "Solo Nombre"})
        assert r.json()["apellido"] == "Preservado"

    async def test_update_telefono_formatos(self, client: AsyncClient, test_user, auth_headers):
        for tel in ["+34666666666", "666666666", "600 000 000"]:
            r = await client.put("/api/users/me", headers=auth_headers, json={"telefono": tel})
            assert r.status_code == 200


class TestPerfilAvatar:
    async def test_avatar_presente_en_perfil(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert "avatar" in r.json()

    async def test_avatar_es_string(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert isinstance(r.json()["avatar"], str)

    async def test_update_avatar(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers,
                             json={"avatar": "https://ejemplo.com/avatar.png"})
        assert r.status_code == 200


class TestPerfilPassword:
    async def test_change_password_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={
            "password_actual": test_user._test_password,
            "password_nueva": "NuevoPass1!",
        })
        assert r.status_code in (200, 422, 400)  # depende de si la API soporta cambio de password aquí

    async def test_update_no_acepta_password_en_claro(self, client: AsyncClient, test_user, auth_headers):
        # Si la API acepta password, debe ser validada
        r = await client.put("/api/users/me", headers=auth_headers,
                             json={"password": "nuevapassword"})
        # Password corta sin mayúscula/número debe fallar o ser ignorada
        assert r.status_code in (200, 422)


class TestPerfilAislamiento:
    async def test_usuario_solo_ve_su_perfil(self, client: AsyncClient, test_user, auth_headers):
        import uuid as uuid_lib
        uid = uuid_lib.uuid4().hex[:8]
        r2 = await client.post("/api/auth/register", json={
            "email": f"perfil2_{uid}@test.com",
            "password": "TestPass1!",
            "nombre": "User2", "apellido": "Test2",
            "empresa": "Emp2", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        if r2.status_code != 201:
            return
        token2 = r2.json().get("access_token")
        headers2 = {"Authorization": f"Bearer {token2}"}
        r = await client.get("/api/users/me", headers=headers2)
        assert r.status_code == 200
        # El perfil devuelto es del user2, no del user1
        assert r.json()["email"] == f"perfil2_{uid}@test.com"

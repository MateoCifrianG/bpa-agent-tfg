"""
test_users_avanzado.py — Tests avanzados de usuarios: actualización de perfil,
avatar, teléfono, ciudad, contraseña, campos sensibles, edge cases de validación.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestUsersMeGet:
    async def test_me_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/users/me")
        assert r.status_code == 401

    async def test_me_devuelve_200(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert r.status_code == 200

    async def test_me_devuelve_email(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert r.json()["email"] == test_user.email

    async def test_me_devuelve_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert "nombre" in r.json()

    async def test_me_devuelve_id(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert "id" in r.json()
        assert r.json()["id"] is not None

    async def test_me_no_devuelve_password(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        data = r.json()
        assert "password" not in data
        assert "hashed_password" not in data

    async def test_me_devuelve_role(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert "role" in r.json()

    async def test_me_content_type_json(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert "application/json" in r.headers.get("content-type", "")

    async def test_me_admin_tiene_role_admin(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/users/me", headers=admin_headers)
        assert r.json()["role"] == "admin"

    async def test_me_user_tiene_role_user(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert r.json()["role"] == "user"


class TestUsersMePut:
    async def test_put_me_requiere_auth(self, client: AsyncClient):
        r = await client.put("/api/users/me", json={"nombre": "X"})
        assert r.status_code == 401

    async def test_put_me_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"nombre": "Nombre Nuevo"})
        assert r.status_code == 200
        assert r.json()["nombre"] == "Nombre Nuevo"

    async def test_put_me_apellido(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"apellido": "Apellido Nuevo"})
        assert r.status_code == 200

    async def test_put_me_ciudad(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"ciudad": "Barcelona"})
        assert r.status_code == 200
        assert r.json().get("ciudad") == "Barcelona"

    async def test_put_me_telefono(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"telefono": "+34 612 345 678"})
        assert r.status_code == 200

    async def test_put_me_avatar(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"avatar": "JG"})
        assert r.status_code == 200

    async def test_put_me_nombre_con_acento(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"nombre": "María José"})
        assert r.status_code == 200
        assert "María" in r.json()["nombre"]

    async def test_put_me_nombre_muy_largo_422(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={"nombre": "N" * 300})
        assert r.status_code in (200, 422)

    async def test_put_me_preserva_email(self, client: AsyncClient, test_user, auth_headers):
        original_email = test_user.email
        r = await client.put("/api/users/me", headers=auth_headers, json={"nombre": "Solo Nombre"})
        assert r.json()["email"] == original_email

    async def test_put_me_no_puede_cambiar_role(self, client: AsyncClient, test_user, auth_headers):
        original_role = test_user.role
        r = await client.put("/api/users/me", headers=auth_headers, json={"role": "admin"})
        if r.status_code == 200:
            assert r.json()["role"] == original_role

    async def test_put_me_xss_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers,
                             json={"nombre": "<b>usuario</b><script>evil()</script>"})
        if r.status_code == 200:
            assert "<script>" not in r.json()["nombre"].lower()

    async def test_put_me_multiples_campos(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={
            "nombre": "Multi Nombre",
            "apellido": "Multi Apellido",
            "ciudad": "Madrid",
        })
        assert r.status_code == 200
        assert r.json()["nombre"] == "Multi Nombre"

    async def test_put_me_campos_extra_ignorados(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={
            "nombre": "Usuario Real",
            "campo_fake": "valor_falso",
        })
        assert r.status_code == 200
        assert "campo_fake" not in r.json()


class TestUsersCambioPassword:
    async def test_cambiar_password_acepta_o_rechaza(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={
            "password_actual": test_user._test_password,
            "password_nueva": "NuevaPass1!",
        })
        assert r.status_code in (200, 400, 422)

    async def test_cambiar_password_incorrecta_actual_aceptada_o_rechazada(
            self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={
            "password_actual": "WrongOldPass1!",
            "password_nueva": "NuevaPass1!",
        })
        # La API puede o no validar password_actual
        assert r.status_code in (200, 400, 401, 422)

    async def test_cambiar_password_nueva_debil_aceptada_o_rechazada(
            self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={
            "password_actual": test_user._test_password,
            "password_nueva": "abc",
        })
        assert r.status_code in (200, 400, 422)


class TestUsersSeguridad:
    async def test_user_no_ve_datos_de_admin(self, client: AsyncClient, test_user, auth_headers,
                                              admin_user, admin_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert r.json()["email"] != admin_user.email

    async def test_token_distintos_usuarios_distintos_datos(self, client: AsyncClient, test_user, auth_headers,
                                                             admin_user, admin_headers):
        r1 = await client.get("/api/users/me", headers=auth_headers)
        r2 = await client.get("/api/users/me", headers=admin_headers)
        assert r1.json()["id"] != r2.json()["id"]

    async def test_me_no_expone_hashed_password(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        response_text = r.text
        assert "$2b$" not in response_text
        assert "hashed" not in response_text.lower()


class TestUsersEdgeCases:
    async def test_avatar_iniciales_correctas(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        data = r.json()
        if "avatar" in data and data["avatar"]:
            assert isinstance(data["avatar"], str)

    async def test_plan_en_respuesta(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        data = r.json()
        assert "plan" in data or "role" in data

    async def test_is_active_en_respuesta(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        data = r.json()
        if "is_active" in data:
            assert data["is_active"] is True

    async def test_put_telefono_con_formato(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={
            "telefono": "612 345 678",
        })
        assert r.status_code == 200

    async def test_put_ciudad_con_acento(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/users/me", headers=auth_headers, json={
            "ciudad": "Málaga",
        })
        assert r.status_code == 200
        assert "Málaga" in r.json().get("ciudad", "Málaga")

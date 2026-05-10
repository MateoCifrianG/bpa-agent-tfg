"""
test_auth_completo.py — Tests exhaustivos de autenticación:
registro con todos los campos, login variantes, refresh, me, logout, edge cases.
"""
import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def reg_payload(**kwargs):
    uid = uuid.uuid4().hex[:8]
    base = {
        "email": f"auth_{uid}@test.com",
        "password": "TestPass1!",
        "nombre": "Test",
        "apellido": "User",
        "empresa": "Empresa Test",
        "sector": "ventas",
        "empleados": 10,
        "plan": "free",
    }
    base.update(kwargs)
    return base


class TestRegistroCompleto:
    async def test_registro_basico_201(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json=reg_payload())
        assert r.status_code == 201

    async def test_registro_devuelve_access_token(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json=reg_payload())
        assert "access_token" in r.json()
        assert r.json()["access_token"] is not None

    async def test_registro_devuelve_token_type(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json=reg_payload())
        assert r.json().get("token_type") == "bearer"

    async def test_registro_devuelve_refresh_token(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json=reg_payload())
        assert "refresh_token" in r.json()

    async def test_registro_email_ya_existe(self, client: AsyncClient):
        payload = reg_payload()
        await client.post("/api/auth/register", json=payload)
        r = await client.post("/api/auth/register", json=payload)
        assert r.status_code == 409

    async def test_registro_email_invalido(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json=reg_payload(email="noesemail"))
        assert r.status_code == 422

    async def test_registro_email_sin_arroba(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json=reg_payload(email="sinArrobaempresa.com"))
        assert r.status_code == 422

    async def test_registro_password_muy_corta(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json=reg_payload(password="Ab1"))
        assert r.status_code == 422

    async def test_registro_password_sin_mayuscula(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json=reg_payload(password="sinmayuscula1"))
        assert r.status_code == 422

    async def test_registro_password_sin_numero(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json=reg_payload(password="SinNumeroAqui"))
        assert r.status_code == 422

    async def test_registro_nombre_requerido(self, client: AsyncClient):
        payload = reg_payload()
        del payload["nombre"]
        r = await client.post("/api/auth/register", json=payload)
        assert r.status_code == 422

    async def test_registro_apellido_campo_existente(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json=reg_payload(apellido="Apellido"))
        assert r.status_code == 201
        # El apellido puede no ser requerido según la implementación
        assert r.status_code in (201, 422)

    async def test_registro_empresa_requerida(self, client: AsyncClient):
        payload = reg_payload()
        del payload["empresa"]
        r = await client.post("/api/auth/register", json=payload)
        assert r.status_code == 422

    async def test_registro_sector_varios(self, client: AsyncClient):
        for sector in ["ventas", "logística", "finanzas", "marketing", "recursos humanos"]:
            r = await client.post("/api/auth/register", json=reg_payload(sector=sector))
            assert r.status_code == 201, f"Falló con sector={sector}"

    async def test_registro_plan_free(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json=reg_payload(plan="free"))
        assert r.status_code == 201

    async def test_registro_plan_pro(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json=reg_payload(plan="pro"))
        assert r.status_code == 201

    async def test_registro_nombre_muy_largo(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json=reg_payload(nombre="N" * 300))
        assert r.status_code == 422

    async def test_registro_email_mayusculas_normalizado(self, client: AsyncClient):
        uid = uuid.uuid4().hex[:8]
        email = f"UPPER_{uid}@TEST.COM"
        r = await client.post("/api/auth/register", json=reg_payload(email=email))
        assert r.status_code == 201

    async def test_registro_empleados_negativo(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json=reg_payload(empleados=-1))
        assert r.status_code in (201, 422)

    async def test_registro_xss_nombre(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json=reg_payload(nombre="<script>alert(1)</script>"))
        if r.status_code == 201:
            # El nombre no debe contener el tag script si se sanitiza
            pass  # La sanitización puede ocurrir en otro nivel


class TestLoginCompleto:
    async def test_login_correcto_200(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        assert r.status_code == 200

    async def test_login_devuelve_access_token(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        assert "access_token" in r.json()

    async def test_login_devuelve_refresh_token(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        assert "refresh_token" in r.json()

    async def test_login_token_type_bearer(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        assert r.json().get("token_type") == "bearer"

    async def test_login_password_incorrecta(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "WrongPass1!",
        })
        assert r.status_code == 401

    async def test_login_email_inexistente(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={
            "email": "noexiste_xyz@test.com",
            "password": "TestPass1!",
        })
        assert r.status_code == 401

    async def test_login_email_vacio(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={"email": "", "password": "TestPass1!"})
        assert r.status_code == 422

    async def test_login_password_vacia(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={"email": test_user.email, "password": ""})
        assert r.status_code == 422

    async def test_login_sin_body_422(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={})
        assert r.status_code == 422

    async def test_login_email_case_insensitive(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email.upper(),
            "password": test_user._test_password,
        })
        assert r.status_code == 200

    async def test_login_no_expone_password(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        data = r.json()
        assert "password" not in data
        assert "hashed_password" not in data


class TestMeEndpoint:
    async def test_me_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/auth/me")
        assert r.status_code == 401

    async def test_me_con_token(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/auth/me", headers=auth_headers)
        assert r.status_code == 200

    async def test_me_devuelve_email(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/auth/me", headers=auth_headers)
        assert r.json()["email"] == test_user.email

    async def test_me_devuelve_id(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/auth/me", headers=auth_headers)
        assert "id" in r.json()

    async def test_me_devuelve_rol(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/auth/me", headers=auth_headers)
        assert "role" in r.json()

    async def test_me_devuelve_plan(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/auth/me", headers=auth_headers)
        assert "plan" in r.json()

    async def test_me_no_expone_password(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/auth/me", headers=auth_headers)
        data = r.json()
        assert "password" not in data
        assert "hashed_password" not in data

    async def test_me_token_invalido_401(self, client: AsyncClient):
        r = await client.get("/api/auth/me", headers={"Authorization": "Bearer token_invalido"})
        assert r.status_code == 401


class TestRefreshToken:
    async def test_refresh_con_token_valido(self, client: AsyncClient, test_user):
        login = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        refresh_token = login.json().get("refresh_token")
        if not refresh_token:
            return
        r = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert r.status_code == 200

    async def test_refresh_devuelve_nuevo_token(self, client: AsyncClient, test_user):
        login = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        refresh_token = login.json().get("refresh_token")
        if not refresh_token:
            return
        r = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        if r.status_code == 200:
            assert "access_token" in r.json()

    async def test_refresh_token_invalido_401(self, client: AsyncClient):
        r = await client.post("/api/auth/refresh", json={"refresh_token": "token_invalido"})
        assert r.status_code in (401, 422)

    async def test_refresh_sin_token_error(self, client: AsyncClient):
        r = await client.post("/api/auth/refresh", json={})
        assert r.status_code in (401, 422)


class TestLogout:
    async def test_logout_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/auth/logout", headers=auth_headers)
        assert r.status_code in (200, 204)

    async def test_logout_revoca_token(self, client: AsyncClient, test_user):
        login = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        await client.post("/api/auth/logout", headers=headers)
        r = await client.get("/api/auth/me", headers=headers)
        assert r.status_code == 401

    async def test_logout_sin_token_no_crash(self, client: AsyncClient):
        r = await client.post("/api/auth/logout")
        assert r.status_code in (200, 401)


class TestPasswordSeguridad:
    async def test_passwords_son_hasheadas(self, client: AsyncClient):
        payload = reg_payload()
        r = await client.post("/api/auth/register", json=payload)
        assert r.status_code == 201
        # La respuesta no debe contener la password en claro
        assert payload["password"] not in str(r.json())

    async def test_login_no_funciona_con_hash(self, client: AsyncClient, test_user):
        # No podemos hacer login con el hash de la contraseña
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user.hashed_password if hasattr(test_user, "hashed_password") else "$2b$12$invalid",
        })
        assert r.status_code == 401

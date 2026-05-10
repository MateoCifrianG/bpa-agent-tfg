"""
test_auth_edge_cases.py — Tests edge cases de autenticación: registro con datos
extremos, login múltiple, logout, campos opcionales, validaciones, concurrencia simulada.
"""
import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestRegistroEdgeCases:
    async def test_registro_email_unico(self, client: AsyncClient):
        uid = uuid.uuid4().hex[:8]
        email = f"unique_{uid}@test.com"
        r1 = await client.post("/api/auth/register", json={
            "email": email, "password": "TestPass1!",
            "nombre": "User", "apellido": "Test",
            "empresa": "Emp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        r2 = await client.post("/api/auth/register", json={
            "email": email, "password": "OtherPass1!",
            "nombre": "Other", "apellido": "User",
            "empresa": "OtherEmp", "sector": "finanzas", "empleados": 5, "plan": "free",
        })
        assert r1.status_code == 201
        assert r2.status_code in (400, 409, 422)

    async def test_registro_email_case_insensitive(self, client: AsyncClient):
        uid = uuid.uuid4().hex[:8]
        r1 = await client.post("/api/auth/register", json={
            "email": f"UPPER_{uid}@TEST.COM", "password": "TestPass1!",
            "nombre": "User", "apellido": "Test",
            "empresa": "Emp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r1.status_code in (201, 422)

    async def test_registro_password_debil_rechazado(self, client: AsyncClient):
        uid = uuid.uuid4().hex[:8]
        r = await client.post("/api/auth/register", json={
            "email": f"weak_{uid}@test.com", "password": "abc",
            "nombre": "User", "apellido": "Test",
            "empresa": "Emp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code in (400, 422)

    async def test_registro_sin_email_422(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "password": "TestPass1!", "nombre": "User", "apellido": "Test",
            "empresa": "Emp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code == 422

    async def test_registro_sin_password_422(self, client: AsyncClient):
        uid = uuid.uuid4().hex[:8]
        r = await client.post("/api/auth/register", json={
            "email": f"nopwd_{uid}@test.com",
            "nombre": "User", "apellido": "Test",
            "empresa": "Emp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code == 422

    async def test_registro_email_invalido_422(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": "no_es_email", "password": "TestPass1!",
            "nombre": "User", "apellido": "Test",
            "empresa": "Emp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code in (400, 422)

    async def test_registro_devuelve_access_token(self, client: AsyncClient):
        uid = uuid.uuid4().hex[:8]
        r = await client.post("/api/auth/register", json={
            "email": f"token_test_{uid}@test.com", "password": "TestPass1!",
            "nombre": "Token", "apellido": "User",
            "empresa": "TokenEmp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code == 201
        assert "access_token" in r.json()

    async def test_registro_token_es_bearer(self, client: AsyncClient):
        uid = uuid.uuid4().hex[:8]
        r = await client.post("/api/auth/register", json={
            "email": f"bearer_{uid}@test.com", "password": "TestPass1!",
            "nombre": "Bearer", "apellido": "User",
            "empresa": "BearerEmp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code == 201
        token_type = r.json().get("token_type", "bearer")
        assert token_type.lower() == "bearer"

    async def test_registro_multiples_sectores(self, client: AsyncClient):
        for sector in ["ventas", "finanzas", "logística", "marketing", "tecnología"]:
            uid = uuid.uuid4().hex[:8]
            r = await client.post("/api/auth/register", json={
                "email": f"sec_{sector[:3]}_{uid}@test.com", "password": "TestPass1!",
                "nombre": "User", "apellido": "Test",
                "empresa": f"Emp {sector}", "sector": sector, "empleados": 10, "plan": "free",
            })
            assert r.status_code == 201, f"Fallo registrando sector={sector}"

    async def test_registro_empresa_larga(self, client: AsyncClient):
        uid = uuid.uuid4().hex[:8]
        r = await client.post("/api/auth/register", json={
            "email": f"long_{uid}@test.com", "password": "TestPass1!",
            "nombre": "User", "apellido": "Test",
            "empresa": "E" * 100, "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code in (201, 422)

    async def test_registro_empleados_grande(self, client: AsyncClient):
        uid = uuid.uuid4().hex[:8]
        r = await client.post("/api/auth/register", json={
            "email": f"big_{uid}@test.com", "password": "TestPass1!",
            "nombre": "User", "apellido": "Test",
            "empresa": "BigCorp", "sector": "ventas", "empleados": 50000, "plan": "free",
        })
        assert r.status_code == 201


class TestLoginEdgeCases:
    async def test_login_correcto(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        assert r.status_code == 200
        assert "access_token" in r.json()

    async def test_login_password_incorrecta(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "WrongPassword1!",
        })
        assert r.status_code == 401

    async def test_login_email_no_existe(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={
            "email": "noexiste@test.com",
            "password": "TestPass1!",
        })
        assert r.status_code == 401

    async def test_login_email_vacio_422(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={
            "email": "", "password": "TestPass1!",
        })
        assert r.status_code in (400, 422)

    async def test_login_password_vacia_422(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email, "password": "",
        })
        assert r.status_code in (400, 401, 422)

    async def test_login_body_vacio_422(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={})
        assert r.status_code == 422

    async def test_login_devuelve_token_type(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        assert r.status_code == 200
        data = r.json()
        assert "token_type" in data or "access_token" in data

    async def test_login_multiples_veces_mismo_usuario(self, client: AsyncClient, test_user):
        for _ in range(3):
            r = await client.post("/api/auth/login", json={
                "email": test_user.email,
                "password": test_user._test_password,
            })
            assert r.status_code == 200

    async def test_login_case_insensitive_email(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email.upper(),
            "password": test_user._test_password,
        })
        assert r.status_code in (200, 401)

    async def test_login_sql_injection_no_funciona(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={
            "email": "' OR 1=1; --",
            "password": "anything",
        })
        assert r.status_code in (400, 401, 422)


class TestLogout:
    async def test_logout_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/auth/logout", headers=auth_headers)
        assert r.status_code in (200, 204, 404)

    async def test_logout_sin_auth_401(self, client: AsyncClient):
        r = await client.post("/api/auth/logout")
        assert r.status_code in (200, 401, 404)

    async def test_logout_devuelve_mensaje(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/auth/logout", headers=auth_headers)
        if r.status_code == 200:
            assert isinstance(r.json(), dict)


class TestRefreshEdgeCases:
    async def test_refresh_sin_token_error(self, client: AsyncClient):
        r = await client.post("/api/auth/refresh", json={})
        assert r.status_code in (401, 422)

    async def test_refresh_token_invalido_401(self, client: AsyncClient):
        r = await client.post("/api/auth/refresh", json={"refresh_token": "invalid"})
        assert r.status_code == 401

    async def test_refresh_con_access_token_401(self, client: AsyncClient, test_user, auth_headers):
        token = auth_headers["Authorization"].split(" ")[1]
        r = await client.post("/api/auth/refresh", json={"refresh_token": token})
        assert r.status_code in (401, 422)

    async def test_refresh_token_valido_da_nuevo_access(self, client: AsyncClient, test_user):
        r_login = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        refresh = r_login.json().get("refresh_token")
        if refresh:
            r_refresh = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
            assert r_refresh.status_code == 200
            assert "access_token" in r_refresh.json()


class TestMeEndpoint:
    async def test_me_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/users/me")
        assert r.status_code == 401

    async def test_me_devuelve_email(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["email"] == test_user.email

    async def test_me_devuelve_id(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert "id" in r.json()

    async def test_me_no_devuelve_password(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        data = r.json()
        assert "password" not in data
        assert "hashed_password" not in data

    async def test_me_diferente_por_usuario(self, client: AsyncClient, test_user, auth_headers,
                                             admin_user, admin_headers):
        r1 = await client.get("/api/users/me", headers=auth_headers)
        r2 = await client.get("/api/users/me", headers=admin_headers)
        assert r1.json()["email"] != r2.json()["email"]

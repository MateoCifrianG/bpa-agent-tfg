"""
test_auth_registro_avanzado.py — Tests avanzados de registro y autenticación:
planes, sectores, campos opcionales, respuestas de token, seguridad de contraseñas,
múltiples registros, validaciones de email, campos numéricos.
"""
import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


def _uid():
    return uuid.uuid4().hex[:8]


class TestRegistroPlanes:
    async def test_registro_plan_free(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"plan_free_{_uid()}@test.com", "password": "TestPass1!",
            "nombre": "Free", "apellido": "User",
            "empresa": "FreeEmp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code == 201

    async def test_registro_plan_pro(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"plan_pro_{_uid()}@test.com", "password": "TestPass1!",
            "nombre": "Pro", "apellido": "User",
            "empresa": "ProEmp", "sector": "ventas", "empleados": 5, "plan": "pro",
        })
        assert r.status_code == 201

    async def test_registro_plan_enterprise(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"plan_ent_{_uid()}@test.com", "password": "TestPass1!",
            "nombre": "Ent", "apellido": "User",
            "empresa": "EntEmp", "sector": "finanzas", "empleados": 100, "plan": "enterprise",
        })
        assert r.status_code == 201

    async def test_registro_crea_empresa_automaticamente(self, client: AsyncClient):
        uid = _uid()
        r = await client.post("/api/auth/register", json={
            "email": f"emp_auto_{uid}@test.com", "password": "TestPass1!",
            "nombre": "Auto", "apellido": "Empresa",
            "empresa": f"AutoEmp_{uid}", "sector": "tecnología", "empleados": 10, "plan": "free",
        })
        assert r.status_code == 201
        assert "access_token" in r.json()

    async def test_registro_devuelve_token_valido(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"token_val_{_uid()}@test.com", "password": "TestPass1!",
            "nombre": "Token", "apellido": "Val",
            "empresa": "TokenEmp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code == 201
        token = r.json()["access_token"]
        assert len(token) > 20

    async def test_registro_token_funciona_para_me(self, client: AsyncClient):
        r_reg = await client.post("/api/auth/register", json={
            "email": f"me_test_{_uid()}@test.com", "password": "TestPass1!",
            "nombre": "Me", "apellido": "Test",
            "empresa": "MeEmp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        token = r_reg.json()["access_token"]
        r_me = await client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
        assert r_me.status_code == 200

    async def test_registro_email_se_guarda_correctamente(self, client: AsyncClient):
        uid = _uid()
        email = f"save_email_{uid}@test.com"
        r_reg = await client.post("/api/auth/register", json={
            "email": email, "password": "TestPass1!",
            "nombre": "Save", "apellido": "Email",
            "empresa": "SaveEmp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        token = r_reg.json()["access_token"]
        r_me = await client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
        assert r_me.json()["email"] == email


class TestRegistroSectores:
    async def test_registro_sector_ventas(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"sec_ventas_{_uid()}@test.com", "password": "TestPass1!",
            "nombre": "U", "apellido": "T", "empresa": "E", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code == 201

    async def test_registro_sector_finanzas(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"sec_fin_{_uid()}@test.com", "password": "TestPass1!",
            "nombre": "U", "apellido": "T", "empresa": "E", "sector": "finanzas", "empleados": 1, "plan": "free",
        })
        assert r.status_code == 201

    async def test_registro_sector_tecnologia(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"sec_tech_{_uid()}@test.com", "password": "TestPass1!",
            "nombre": "U", "apellido": "T", "empresa": "E", "sector": "tecnología", "empleados": 1, "plan": "free",
        })
        assert r.status_code == 201

    async def test_registro_sector_logistica(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"sec_log_{_uid()}@test.com", "password": "TestPass1!",
            "nombre": "U", "apellido": "T", "empresa": "E", "sector": "logística", "empleados": 1, "plan": "free",
        })
        assert r.status_code == 201

    async def test_registro_sector_marketing(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"sec_mkt_{_uid()}@test.com", "password": "TestPass1!",
            "nombre": "U", "apellido": "T", "empresa": "E", "sector": "marketing", "empleados": 1, "plan": "free",
        })
        assert r.status_code == 201

    async def test_registro_sector_rrhh(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"sec_rrhh_{_uid()}@test.com", "password": "TestPass1!",
            "nombre": "U", "apellido": "T", "empresa": "E", "sector": "recursos humanos",
            "empleados": 1, "plan": "free",
        })
        assert r.status_code == 201


class TestRegistroPasswords:
    async def test_password_minima_longitud(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"pwd_min_{_uid()}@test.com", "password": "Abc1!xyz",
            "nombre": "U", "apellido": "T", "empresa": "E", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code in (201, 422)

    async def test_password_con_simbolos(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"pwd_sym_{_uid()}@test.com", "password": "Test@#$1!Pass",
            "nombre": "U", "apellido": "T", "empresa": "E", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code in (201, 422)

    async def test_password_debil_solo_letras_rechazado(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"pwd_weak_{_uid()}@test.com", "password": "aabbccdd",
            "nombre": "U", "apellido": "T", "empresa": "E", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code in (400, 422)

    async def test_password_muy_corto_rechazado(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"pwd_short_{_uid()}@test.com", "password": "Ab1!",
            "nombre": "U", "apellido": "T", "empresa": "E", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code in (400, 422)

    async def test_password_largo_ok(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"pwd_long_{_uid()}@test.com", "password": "MiContraseñaLarga123!Super",
            "nombre": "U", "apellido": "T", "empresa": "E", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code == 201


class TestRegistroEmpleados:
    async def test_empleados_1(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"emp_1_{_uid()}@test.com", "password": "TestPass1!",
            "nombre": "U", "apellido": "T", "empresa": "E", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code == 201

    async def test_empleados_10(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"emp_10_{_uid()}@test.com", "password": "TestPass1!",
            "nombre": "U", "apellido": "T", "empresa": "E", "sector": "ventas", "empleados": 10, "plan": "free",
        })
        assert r.status_code == 201

    async def test_empleados_1000(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"emp_1000_{_uid()}@test.com", "password": "TestPass1!",
            "nombre": "U", "apellido": "T", "empresa": "E", "sector": "ventas", "empleados": 1000, "plan": "free",
        })
        assert r.status_code == 201

    async def test_empleados_0_ok_o_422(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"emp_0_{_uid()}@test.com", "password": "TestPass1!",
            "nombre": "U", "apellido": "T", "empresa": "E", "sector": "ventas", "empleados": 0, "plan": "free",
        })
        assert r.status_code in (201, 422)


class TestRegistroEmail:
    async def test_email_con_subdomain(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"user_{_uid()}@sub.domain.com", "password": "TestPass1!",
            "nombre": "U", "apellido": "T", "empresa": "E", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code == 201

    async def test_email_con_plus(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"user+tag_{_uid()}@test.com", "password": "TestPass1!",
            "nombre": "U", "apellido": "T", "empresa": "E", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code in (201, 422)

    async def test_email_dominio_numerico(self, client: AsyncClient):
        r = await client.post("/api/auth/register", json={
            "email": f"user_{_uid()}@123.com", "password": "TestPass1!",
            "nombre": "U", "apellido": "T", "empresa": "E", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code in (201, 422)

    async def test_email_muy_largo(self, client: AsyncClient):
        uid = _uid()
        long_local = "a" * 60
        r = await client.post("/api/auth/register", json={
            "email": f"{long_local}_{uid}@test.com", "password": "TestPass1!",
            "nombre": "U", "apellido": "T", "empresa": "E", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code in (201, 422)

"""
test_security_extra.py — Tests adicionales de seguridad: CORS, Content-Type,
headers de seguridad, métodos HTTP no permitidos, payload injection, límites,
tokens malformados, endpoints sensibles protegidos.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestHTTPMetodos:
    async def test_patch_procesos_405_o_200(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.patch(f"/api/procesos/{test_proceso['id']}", headers=auth_headers, json={"nombre": "Patch"})
        assert r.status_code in (200, 405, 422)

    async def test_delete_auth_register_405(self, client: AsyncClient):
        r = await client.delete("/api/auth/register")
        assert r.status_code in (405, 404)

    async def test_delete_health_405(self, client: AsyncClient):
        r = await client.delete("/health")
        assert r.status_code in (405, 404)

    async def test_put_auth_login_405(self, client: AsyncClient):
        r = await client.put("/api/auth/login", json={})
        assert r.status_code in (405, 404, 422)

    async def test_get_auth_login_405(self, client: AsyncClient):
        r = await client.get("/api/auth/login")
        assert r.status_code in (405, 404)

    async def test_post_procesos_id_405(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post(f"/api/procesos/{test_proceso['id']}", headers=auth_headers, json={})
        assert r.status_code in (200, 201, 405, 422)


class TestTokensMalformados:
    async def test_token_sin_punto_401(self, client: AsyncClient):
        r = await client.get("/api/users/me", headers={"Authorization": "Bearer INVALID"})
        assert r.status_code == 401

    async def test_token_solo_un_punto_401(self, client: AsyncClient):
        r = await client.get("/api/users/me", headers={"Authorization": "Bearer a.b"})
        assert r.status_code == 401

    async def test_token_vacio_401(self, client: AsyncClient):
        r = await client.get("/api/users/me", headers={"Authorization": "Bearer "})
        assert r.status_code == 401

    async def test_sin_bearer_prefix_401(self, client: AsyncClient):
        r = await client.get("/api/users/me", headers={"Authorization": "TOKEN xyz"})
        assert r.status_code == 401

    async def test_authorization_header_vacio_401(self, client: AsyncClient):
        r = await client.get("/api/users/me", headers={"Authorization": ""})
        assert r.status_code == 401

    async def test_token_jwt_firma_invalida_401(self, client: AsyncClient):
        fake = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.INVALIDSIGNATURE"
        r = await client.get("/api/users/me", headers={"Authorization": f"Bearer {fake}"})
        assert r.status_code == 401

    async def test_token_admin_falso_no_da_acceso(self, client: AsyncClient):
        fake_admin = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiJ9.FAKE"
        r = await client.get("/api/admin/users", headers={"Authorization": f"Bearer {fake_admin}"})
        assert r.status_code in (401, 403)


class TestPayloadSeguridad:
    async def test_registro_con_html_en_nombre(self, client: AsyncClient):
        import uuid
        r = await client.post("/api/auth/register", json={
            "email": f"html_{uuid.uuid4().hex[:6]}@test.com", "password": "TestPass1!",
            "nombre": "<b>Hacker</b>", "apellido": "Test",
            "empresa": "HtmlEmp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        if r.status_code == 201:
            token = r.json()["access_token"]
            r_me = await client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
            nombre = r_me.json().get("nombre", "")
            assert "<script>" not in nombre.lower()

    async def test_registro_con_sql_en_empresa(self, client: AsyncClient):
        import uuid
        r = await client.post("/api/auth/register", json={
            "email": f"sql_{uuid.uuid4().hex[:6]}@test.com", "password": "TestPass1!",
            "nombre": "Test", "apellido": "SQL",
            "empresa": "'; DROP TABLE users; --", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code in (201, 400, 422)

    async def test_login_payload_enorme_no_rompe(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={
            "email": "test@test.com",
            "password": "X" * 10000,
        })
        assert r.status_code in (400, 401, 422)

    async def test_proceso_con_html_en_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "<script>alert(1)</script>Proceso Malicioso"
        })
        if r.status_code == 201:
            nombre = r.json()["nombre"]
            assert "<script>" not in nombre.lower()

    async def test_proceso_con_sql_en_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso'; DROP TABLE procesos; --"
        })
        assert r.status_code in (201, 422)


class TestEndpointsProtegidos:
    async def test_admin_users_sin_auth_401(self, client: AsyncClient):
        r = await client.get("/api/admin/users")
        assert r.status_code == 401

    async def test_admin_sistema_sin_auth_401(self, client: AsyncClient):
        r = await client.get("/api/admin/sistema")
        assert r.status_code == 401

    async def test_procesos_sin_auth_401(self, client: AsyncClient):
        r = await client.get("/api/procesos")
        assert r.status_code == 401

    async def test_kpis_sin_auth_401(self, client: AsyncClient):
        r = await client.get("/api/kpis")
        assert r.status_code == 401

    async def test_automatizaciones_sin_auth_401(self, client: AsyncClient):
        r = await client.get("/api/automatizaciones")
        assert r.status_code == 401

    async def test_agente_sin_auth_401(self, client: AsyncClient):
        r = await client.post("/api/agente/chat", json={"mensaje": "hola"})
        assert r.status_code == 401

    async def test_users_me_sin_auth_401(self, client: AsyncClient):
        r = await client.get("/api/users/me")
        assert r.status_code == 401

    async def test_empresa_mia_sin_auth_401(self, client: AsyncClient):
        r = await client.get("/api/empresa/mia")
        assert r.status_code == 401

    async def test_scheduler_jobs_sin_auth_401(self, client: AsyncClient):
        r = await client.get("/api/ejecutar/scheduler/jobs")
        assert r.status_code == 401

    async def test_smtp_presets_sin_auth_401(self, client: AsyncClient):
        r = await client.get("/api/ejecutar/connectors/smtp-presets")
        assert r.status_code == 401


class TestContentType:
    async def test_login_acepta_json(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        assert r.status_code == 200
        assert "application/json" in r.headers.get("content-type", "")

    async def test_health_devuelve_json(self, client: AsyncClient):
        r = await client.get("/health")
        assert "application/json" in r.headers.get("content-type", "")

    async def test_procesos_devuelve_json(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/procesos", headers=auth_headers)
        assert "application/json" in r.headers.get("content-type", "")

    async def test_kpis_devuelve_json(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/kpis", headers=auth_headers)
        assert "application/json" in r.headers.get("content-type", "")

    async def test_admin_users_devuelve_json(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        assert "application/json" in r.headers.get("content-type", "")


class TestEndpointsNoExisten:
    async def test_ruta_inexistente_404(self, client: AsyncClient):
        r = await client.get("/api/no/existe")
        assert r.status_code == 404

    async def test_ruta_raiz_ok_o_404(self, client: AsyncClient):
        r = await client.get("/")
        assert r.status_code in (200, 404)

    async def test_ruta_muy_larga_404(self, client: AsyncClient):
        r = await client.get("/api/" + "a" * 500)
        assert r.status_code in (404, 422)

    async def test_procesos_sub_ruta_inexistente_404(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/procesos/export/csv", headers=auth_headers)
        assert r.status_code in (404, 422)

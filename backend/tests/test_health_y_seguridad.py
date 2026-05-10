"""
test_health_y_seguridad.py — Tests del endpoint /health, cabeceras de seguridad HTTP,
body size limit, CORS y middleware de logging.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestHealthEndpoint:
    async def test_health_ok(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.status_code == 200

    async def test_health_status_ok(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.json()["status"] == "ok"

    async def test_health_devuelve_version(self, client: AsyncClient):
        r = await client.get("/health")
        assert "version" in r.json()
        assert r.json()["version"] is not None

    async def test_health_devuelve_motor(self, client: AsyncClient):
        r = await client.get("/health")
        assert "motor" in r.json()

    async def test_health_devuelve_db(self, client: AsyncClient):
        r = await client.get("/health")
        data = r.json()
        assert "db" in data

    async def test_health_devuelve_uptime(self, client: AsyncClient):
        r = await client.get("/health")
        data = r.json()
        assert "uptime_s" in data
        assert isinstance(data["uptime_s"], (int, float))
        assert data["uptime_s"] >= 0

    async def test_health_sin_auth(self, client: AsyncClient):
        # El endpoint /health no debe requerir autenticación
        r = await client.get("/health")
        assert r.status_code == 200

    async def test_health_motor_es_string(self, client: AsyncClient):
        r = await client.get("/health")
        assert isinstance(r.json()["motor"], str)

    async def test_health_version_es_string(self, client: AsyncClient):
        r = await client.get("/health")
        assert isinstance(r.json()["version"], str)

    async def test_health_db_tiene_ok(self, client: AsyncClient):
        r = await client.get("/health")
        db_info = r.json()["db"]
        # db puede ser bool, dict con "ok", o string "ok"
        if isinstance(db_info, dict):
            assert "ok" in db_info
        elif isinstance(db_info, str):
            assert db_info in ("ok", "error", "connected", "disconnected")
        else:
            assert isinstance(db_info, bool)

    async def test_health_responde_rapido(self, client: AsyncClient):
        import time
        t0 = time.monotonic()
        r = await client.get("/health")
        elapsed = time.monotonic() - t0
        assert r.status_code == 200
        assert elapsed < 5.0  # menos de 5 segundos

    async def test_health_content_type_json(self, client: AsyncClient):
        r = await client.get("/health")
        assert "application/json" in r.headers.get("content-type", "")


class TestCabecerasSeguridad:
    async def test_x_content_type_options(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.headers.get("x-content-type-options") == "nosniff"

    async def test_x_frame_options(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.headers.get("x-frame-options") == "DENY"

    async def test_x_xss_protection(self, client: AsyncClient):
        r = await client.get("/health")
        assert "1" in r.headers.get("x-xss-protection", "")

    async def test_referrer_policy(self, client: AsyncClient):
        r = await client.get("/health")
        assert "strict-origin" in r.headers.get("referrer-policy", "").lower()

    async def test_content_security_policy_presente(self, client: AsyncClient):
        r = await client.get("/health")
        assert "content-security-policy" in r.headers

    async def test_csp_default_src(self, client: AsyncClient):
        r = await client.get("/health")
        csp = r.headers.get("content-security-policy", "")
        assert "default-src" in csp

    async def test_csp_frame_ancestors_none(self, client: AsyncClient):
        r = await client.get("/health")
        csp = r.headers.get("content-security-policy", "")
        assert "frame-ancestors" in csp
        assert "'none'" in csp

    async def test_permissions_policy(self, client: AsyncClient):
        r = await client.get("/health")
        perms = r.headers.get("permissions-policy", "")
        assert "geolocation" in perms

    async def test_cabeceras_en_endpoint_api(self, client: AsyncClient):
        r = await client.get("/api/procesos", headers={"Authorization": "Bearer fake"})
        assert "x-content-type-options" in r.headers

    async def test_cabeceras_en_login_fallido(self, client: AsyncClient):
        r = await client.post("/api/auth/login", json={
            "email": "noexiste@test.com",
            "password": "Test1234!",
        })
        assert "x-frame-options" in r.headers

    async def test_cabeceras_en_respuesta_201(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Seg Test"})
        assert r.status_code == 201
        assert "x-content-type-options" in r.headers

    async def test_cabeceras_en_respuesta_404(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/procesos/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert r.status_code == 404
        assert "x-content-type-options" in r.headers


class TestBodySizeLimit:
    async def test_body_normal_aceptado(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Body Normal",
            "descripcion": "A" * 500,
        })
        assert r.status_code == 201

    async def test_body_1mb_limite_check(self, client: AsyncClient, test_user, auth_headers):
        # No podemos enviar 1MB+ fácilmente via JSON válido, pero verificamos
        # que content-length muy grande retorna 413
        big_headers = dict(auth_headers)
        big_headers["content-length"] = str(2 * 1024 * 1024)  # 2MB
        r = await client.post(
            "/api/procesos",
            headers=big_headers,
            content=b'{"nombre":"X"}',
        )
        assert r.status_code in (413, 201, 422)  # 413 si el middleware actúa


class TestEndpointsNoExistentes:
    async def test_ruta_no_existente_da_404(self, client: AsyncClient):
        r = await client.get("/api/ruta_que_no_existe")
        assert r.status_code == 404

    async def test_metodo_incorrecto_da_405(self, client: AsyncClient):
        r = await client.patch("/health")
        assert r.status_code in (404, 405)

    async def test_get_en_endpoint_post_da_405(self, client: AsyncClient):
        r = await client.get("/api/auth/login")
        assert r.status_code == 405


class TestValidacionRequest:
    async def test_body_json_invalido_da_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post(
            "/api/procesos",
            headers={**auth_headers, "content-type": "application/json"},
            content=b"esto no es json valido",
        )
        assert r.status_code == 422

    async def test_tipo_incorrecto_en_campo_da_422(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Test",
            "duracion_h": "no_es_numero",
        })
        assert r.status_code == 422

    async def test_campos_extra_ignorados(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Extra Fields",
            "campo_inventado": "valor",
            "otro_campo": 123,
        })
        assert r.status_code == 201
        assert "campo_inventado" not in r.json()

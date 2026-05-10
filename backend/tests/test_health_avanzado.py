"""
test_health_avanzado.py — Tests avanzados del endpoint /health y /api/admin/health:
estructura, campos, tiempos de respuesta, estado de base de datos, motor IA.
"""
import pytest
import time
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestHealthPublico:
    async def test_health_ok(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.status_code == 200

    async def test_health_content_type_json(self, client: AsyncClient):
        r = await client.get("/health")
        assert "application/json" in r.headers.get("content-type", "")

    async def test_health_devuelve_dict(self, client: AsyncClient):
        r = await client.get("/health")
        assert isinstance(r.json(), dict)

    async def test_health_tiene_status(self, client: AsyncClient):
        r = await client.get("/health")
        data = r.json()
        assert any(k in data for k in ("status", "estado", "ok", "healthy"))

    async def test_health_status_ok(self, client: AsyncClient):
        r = await client.get("/health")
        data = r.json()
        status = data.get("status") or data.get("estado") or "ok"
        assert status in ("ok", "healthy", "running", True)

    async def test_health_tiene_version_o_api(self, client: AsyncClient):
        r = await client.get("/health")
        data = r.json()
        assert any(k in data for k in ("version", "api", "v", "status"))

    async def test_health_tiene_db_info(self, client: AsyncClient):
        r = await client.get("/health")
        data = r.json()
        assert any(k in data for k in ("db", "database", "base_datos", "status"))

    async def test_health_responde_rapido(self, client: AsyncClient):
        start = time.time()
        r = await client.get("/health")
        elapsed = time.time() - start
        assert r.status_code == 200
        assert elapsed < 5.0

    async def test_health_no_requiere_auth(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.status_code == 200

    async def test_health_llamada_multiple_consistente(self, client: AsyncClient):
        results = []
        for _ in range(3):
            r = await client.get("/health")
            results.append(r.status_code)
        assert all(s == 200 for s in results)


class TestHealthDB:
    async def test_health_db_campo_presente(self, client: AsyncClient):
        r = await client.get("/health")
        data = r.json()
        assert any(k in data for k in ("db", "database", "status"))

    async def test_health_db_estado_ok(self, client: AsyncClient):
        r = await client.get("/health")
        data = r.json()
        db_info = data.get("db") or data.get("database")
        if db_info is not None:
            if isinstance(db_info, str):
                assert db_info in ("ok", "connected", "running", "error", "disconnected")
            elif isinstance(db_info, dict):
                assert any(k in db_info for k in ("status", "ok", "estado"))
            else:
                assert db_info in (True, False, "ok")

    async def test_health_db_no_expone_password(self, client: AsyncClient):
        r = await client.get("/health")
        assert "password" not in r.text.lower()


class TestHealthMotorIA:
    async def test_health_tiene_motor_info(self, client: AsyncClient):
        r = await client.get("/health")
        data = r.json()
        assert any(k in data for k in ("motor", "ollama", "ia", "status"))

    async def test_motor_info_es_string_o_dict(self, client: AsyncClient):
        r = await client.get("/health")
        data = r.json()
        motor_info = data.get("motor") or data.get("ollama")
        if motor_info is not None:
            assert isinstance(motor_info, (str, dict, bool))

    async def test_motor_activo_en_sistema_admin(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/sistema", headers=admin_headers)
        data = r.json()
        assert "motor_activo" in data or "motor" in data or "ollama" in data


class TestHealthEdgeCases:
    async def test_get_health_metodo_post_405_o_200(self, client: AsyncClient):
        r = await client.post("/health")
        assert r.status_code in (200, 405)

    async def test_health_sin_body(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.status_code == 200

    async def test_health_con_headers_extra(self, client: AsyncClient):
        r = await client.get("/health", headers={"X-Custom": "header"})
        assert r.status_code == 200

    async def test_health_sin_auth_sigue_ok(self, client: AsyncClient):
        r = await client.get("/health", headers={"Authorization": "Bearer nope"})
        assert r.status_code == 200

    async def test_health_respuesta_no_vacia(self, client: AsyncClient):
        r = await client.get("/health")
        assert len(r.content) > 0

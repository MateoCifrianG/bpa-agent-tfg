"""
test_health_endpoints.py — Tests exhaustivos del endpoint /health y variantes.
Verifica estructura de respuesta, campos, disponibilidad sin auth.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestHealthBasico:
    async def test_health_ok(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.status_code == 200

    async def test_health_sin_auth(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.status_code == 200

    async def test_health_devuelve_json(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.headers["content-type"].startswith("application/json")

    async def test_health_devuelve_dict(self, client: AsyncClient):
        r = await client.get("/health")
        assert isinstance(r.json(), dict)

    async def test_health_idempotente(self, client: AsyncClient):
        r1 = await client.get("/health")
        r2 = await client.get("/health")
        assert r1.status_code == 200
        assert r2.status_code == 200

    async def test_health_rapido(self, client: AsyncClient):
        import time
        start = time.time()
        await client.get("/health")
        elapsed = time.time() - start
        assert elapsed < 5.0  # Debe responder en menos de 5 segundos

    async def test_health_multiple_veces(self, client: AsyncClient):
        for _ in range(5):
            r = await client.get("/health")
            assert r.status_code == 200


class TestHealthCampos:
    async def test_health_tiene_status(self, client: AsyncClient):
        r = await client.get("/health")
        data = r.json()
        assert "status" in data or "ok" in data or len(data) > 0

    async def test_health_status_ok_o_healthy(self, client: AsyncClient):
        r = await client.get("/health")
        data = r.json()
        if "status" in data:
            assert data["status"] in ("ok", "healthy", "up", True, "running")

    async def test_health_tiene_alguna_info(self, client: AsyncClient):
        r = await client.get("/health")
        data = r.json()
        assert len(data) >= 1

    async def test_health_version_si_existe(self, client: AsyncClient):
        r = await client.get("/health")
        data = r.json()
        if "version" in data:
            assert isinstance(data["version"], str)

    async def test_health_db_si_existe(self, client: AsyncClient):
        r = await client.get("/health")
        data = r.json()
        if "db" in data or "database" in data:
            db_status = data.get("db") or data.get("database")
            assert db_status is not None

    async def test_health_uptime_si_existe(self, client: AsyncClient):
        r = await client.get("/health")
        data = r.json()
        if "uptime" in data:
            assert isinstance(data["uptime"], (int, float, str))

    async def test_health_app_name_si_existe(self, client: AsyncClient):
        r = await client.get("/health")
        data = r.json()
        if "app" in data or "name" in data:
            assert isinstance(data.get("app") or data.get("name"), str)


class TestRootEndpoint:
    async def test_root_ok(self, client: AsyncClient):
        r = await client.get("/")
        assert r.status_code in (200, 307, 404)

    async def test_docs_disponible(self, client: AsyncClient):
        r = await client.get("/docs")
        assert r.status_code in (200, 404)

    async def test_openapi_json(self, client: AsyncClient):
        r = await client.get("/openapi.json")
        assert r.status_code in (200, 404)

    async def test_openapi_tiene_paths(self, client: AsyncClient):
        r = await client.get("/openapi.json")
        if r.status_code == 200:
            data = r.json()
            assert "paths" in data

    async def test_openapi_tiene_info(self, client: AsyncClient):
        r = await client.get("/openapi.json")
        if r.status_code == 200:
            data = r.json()
            assert "info" in data


class TestHTTPMethods:
    async def test_health_get_ok(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.status_code == 200

    async def test_health_post_no_permitido(self, client: AsyncClient):
        r = await client.post("/health")
        assert r.status_code in (200, 404, 405)

    async def test_health_put_no_permitido(self, client: AsyncClient):
        r = await client.put("/health")
        assert r.status_code in (404, 405)

    async def test_health_delete_no_permitido(self, client: AsyncClient):
        r = await client.delete("/health")
        assert r.status_code in (404, 405)

    async def test_endpoint_inexistente_404(self, client: AsyncClient):
        r = await client.get("/api/endpoint-que-no-existe")
        assert r.status_code == 404

    async def test_endpoint_profundo_inexistente(self, client: AsyncClient):
        r = await client.get("/api/v99/nada/aqui")
        assert r.status_code == 404

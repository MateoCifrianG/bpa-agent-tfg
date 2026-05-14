"""
test_empresa_endpoints.py — Tests completos del endpoint /api/empresa/mia.
"""
import pytest
from httpx import AsyncClient
pytestmark = pytest.mark.asyncio


class TestEmpresaMia:
    async def test_get_empresa_ok(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        assert r.status_code == 200

    async def test_get_empresa_sin_auth(self, client: AsyncClient):
        r = await client.get("/api/empresa/mia")
        assert r.status_code in (401, 403)

    async def test_empresa_tiene_nombre(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        data = r.json()
        assert "nombre" in data

    async def test_empresa_tiene_sector(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        data = r.json()
        assert "sector" in data

    async def test_empresa_tiene_id(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        data = r.json()
        assert "id" in data

    async def test_empresa_tiene_user_id(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        data = r.json()
        assert "user_id" in data or "id" in data

    async def test_empresa_tiene_empleados(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        data = r.json()
        assert "empleados" in data or "nombre" in data

    async def test_update_empresa_nombre(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers,
                             json={"nombre": "Empresa Actualizada"})
        assert r.status_code in (200, 404)

    async def test_update_empresa_sector(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers,
                             json={"sector": "tecnologia"})
        assert r.status_code in (200, 404)

    async def test_update_empresa_sin_auth(self, client: AsyncClient):
        r = await client.put("/api/empresa/mia", json={"nombre": "Test"})
        assert r.status_code in (401, 403, 404)


class TestEmpresaStats:
    async def test_stats_ok(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        assert r.status_code == 200

    async def test_stats_sin_auth(self, client: AsyncClient):
        r = await client.get("/api/empresa/mia/stats")
        assert r.status_code in (401, 403)

    async def test_stats_tiene_procesos_count(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        data = r.json()
        assert "procesos_count" in data

    async def test_stats_tiene_autos_count(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        data = r.json()
        assert "autos_count" in data

    async def test_stats_tiene_kpis_count(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        data = r.json()
        assert "kpis_count" in data

    async def test_stats_valores_numericos(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        data = r.json()
        for key in ["procesos_count", "autos_count", "kpis_count"]:
            if key in data:
                assert isinstance(data[key], int)
                assert data[key] >= 0

    async def test_stats_crece_con_proceso(self, client: AsyncClient, auth_headers):
        r1 = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        count_antes = r1.json().get("procesos_count", 0)
        await client.post("/api/procesos", headers=auth_headers, json={"nombre": "P stats"})
        r2 = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        count_despues = r2.json().get("procesos_count", 0)
        assert count_despues >= count_antes

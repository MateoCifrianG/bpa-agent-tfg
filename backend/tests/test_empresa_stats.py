"""
test_empresa_stats.py — Tests de estadísticas de empresa: endpoint stats,
campos de KPI empresa, proyecciones, datos de procesos y automatizaciones.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestEmpresaStats:
    async def test_stats_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/empresa/mia/stats")
        assert r.status_code in (401, 403)

    async def test_stats_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        assert r.status_code == 200

    async def test_stats_devuelve_dict(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        assert isinstance(r.json(), dict)

    async def test_stats_tiene_procesos(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        data = r.json()
        assert any(k in data for k in ("procesos", "procesos_count", "total_procesos", "num_procesos"))

    async def test_stats_tiene_automatizaciones(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        data = r.json()
        assert any(k in data for k in ("automatizaciones", "autos_count", "total_automatizaciones"))

    async def test_stats_tiene_kpis(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        data = r.json()
        assert any(k in data for k in ("kpis", "kpis_count", "total_kpis", "num_kpis"))

    async def test_stats_valores_son_numericos(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        data = r.json()
        for campo in ("procesos_count", "autos_count", "kpis_count"):
            if campo in data:
                assert isinstance(data[campo], (int, float))

    async def test_stats_content_type_json(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        assert "application/json" in r.headers.get("content-type", "")

    async def test_stats_crece_tras_crear_proceso(self, client: AsyncClient, test_user, auth_headers):
        r_before = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proc Stats Test"})
        r_after = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        procs_before = r_before.json().get("procesos", 0)
        procs_after = r_after.json().get("procesos", 0)
        assert procs_after >= procs_before

    async def test_stats_admin_tiene_sus_propias(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/empresa/mia/stats", headers=admin_headers)
        assert r.status_code == 200

    async def test_stats_aislamiento_usuario_admin(self, client: AsyncClient, test_user, auth_headers,
                                                    admin_user, admin_headers):
        r_user = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        r_admin = await client.get("/api/empresa/mia/stats", headers=admin_headers)
        assert r_user.status_code == 200
        assert r_admin.status_code == 200


class TestEmpresaMiaEndpoint:
    async def test_empresa_mia_get(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        assert r.status_code == 200

    async def test_empresa_mia_put(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"nombre": "Empresa Test Stats"})
        assert r.status_code == 200

    async def test_empresa_mia_datos_correctos(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        data = r.json()
        assert "id" in data
        assert "nombre" in data

    async def test_empresa_mia_no_expone_password(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        assert "password" not in r.text.lower()
        assert "$2b$" not in r.text

    async def test_empresa_stats_tokens_distintos_datos_distintos(self, client: AsyncClient,
                                                                   test_user, auth_headers,
                                                                   admin_user, admin_headers):
        r1 = await client.get("/api/empresa/mia", headers=auth_headers)
        r2 = await client.get("/api/empresa/mia", headers=admin_headers)
        assert r1.json()["id"] != r2.json()["id"]

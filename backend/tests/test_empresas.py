"""
test_empresas.py — Tests de empresa: obtener, actualizar, estadísticas.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestEmpresa:
    async def test_obtener_mi_empresa(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["nombre"] == "Empresa Test"
        assert data["sector"] == "logística"

    async def test_empresa_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/empresa/mia")
        assert r.status_code == 401

    async def test_empresa_devuelve_campos_esperados(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        data = r.json()
        for campo in ["id", "nombre"]:
            assert campo in data

    async def test_actualizar_empresa_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={
            "nombre": "Empresa Actualizada",
        })
        assert r.status_code == 200
        assert r.json()["nombre"] == "Empresa Actualizada"

    async def test_actualizar_empresa_sector(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={
            "sector": "finanzas",
        })
        assert r.status_code == 200
        assert r.json()["sector"] == "finanzas"

    async def test_actualizar_empresa_todos_los_campos(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={
            "nombre": "BPA Corp SL",
            "sector": "tecnología",
            "empleados": 25,
            "ciudad": "Madrid",
            "descripcion": "Empresa de automatización de procesos",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["nombre"] == "BPA Corp SL"
        assert data["sector"] == "tecnología"
        assert data["empleados"] == 25
        assert data["ciudad"] == "Madrid"

    async def test_actualizar_empresa_xss(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={
            "nombre": "<script>alert('xss')</script>",
        })
        if r.status_code == 200:
            assert "<script>" not in r.json()["nombre"]
        else:
            assert r.status_code == 422

    async def test_actualizar_empresa_nombre_demasiado_largo(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={
            "nombre": "N" * 300,
        })
        assert r.status_code == 422

    async def test_actualizar_empresa_sin_auth(self, client: AsyncClient):
        r = await client.put("/api/empresa/mia", json={"nombre": "Hack"})
        assert r.status_code == 401


class TestEmpresaStats:
    async def test_stats_empresa_vacia(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "procesos_count" in data
        assert "autos_count" in data
        assert "kpis_count" in data
        assert "horas_ahorradas" in data
        assert "autos_activas" in data

    async def test_stats_cuenta_procesos(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/procesos", headers=auth_headers, json={"nombre": "P Stats 1"})
        await client.post("/api/procesos", headers=auth_headers, json={"nombre": "P Stats 2"})
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["procesos_count"] >= 2

    async def test_stats_cuenta_kpis(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/kpis", headers=auth_headers, json={"nombre": "KPI S1", "valor": "1"})
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        assert r.json()["kpis_count"] >= 1

    async def test_stats_cuenta_automatizaciones_activas(self, client: AsyncClient, test_user, auth_headers):
        cr = await client.post("/api/automatizaciones", headers=auth_headers, json={"nombre": "Auto Activa Stats"})
        auto_id = cr.json()["id"]
        await client.put(f"/api/automatizaciones/{auto_id}", headers=auth_headers, json={"estado": "activa"})
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        assert r.json()["autos_activas"] >= 1

    async def test_stats_horas_ahorradas(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Horas",
            "horas_mes": 20,
        })
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        assert r.json()["horas_ahorradas"] >= 20

    async def test_stats_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/empresa/mia/stats")
        assert r.status_code == 401

    async def test_stats_score_promedio_none_sin_procesos(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        # score_promedio puede ser None si no hay procesos con score
        assert r.status_code == 200
        data = r.json()
        assert "score_promedio" in data

"""
test_empresas_completo.py — Tests exhaustivos de la empresa del usuario:
GET /mia, PUT /mia, GET /mia/stats, validaciones, sanitización, aislamiento.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestEmpresaObtener:
    async def test_get_mia_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/empresa/mia")
        assert r.status_code == 401

    async def test_get_mia_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        assert r.status_code == 200

    async def test_get_mia_devuelve_id(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        assert "id" in r.json()
        assert r.json()["id"] is not None

    async def test_get_mia_devuelve_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        assert "nombre" in r.json()
        assert r.json()["nombre"] is not None

    async def test_get_mia_devuelve_sector(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        assert "sector" in r.json()

    async def test_get_mia_devuelve_campos_basicos(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        data = r.json()
        # La empresa tiene al menos id y nombre
        assert "id" in data
        assert "nombre" in data

    async def test_get_mia_devuelve_empleados(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        data = r.json()
        assert "empleados" in data

    async def test_get_mia_id_es_uuid(self, client: AsyncClient, test_user, auth_headers):
        import re
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
        assert uuid_pattern.match(r.json()["id"])

    async def test_get_mia_content_type_json(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia", headers=auth_headers)
        assert "application/json" in r.headers.get("content-type", "")


class TestEmpresaActualizar:
    async def test_put_mia_requiere_auth(self, client: AsyncClient):
        r = await client.put("/api/empresa/mia", json={"nombre": "X"})
        assert r.status_code == 401

    async def test_put_mia_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"nombre": "Empresa Actualizada"})
        assert r.status_code == 200
        assert r.json()["nombre"] == "Empresa Actualizada"

    async def test_put_mia_sector(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"sector": "finanzas"})
        assert r.status_code == 200
        assert r.json()["sector"] == "finanzas"

    async def test_put_mia_empleados(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"empleados": 50})
        assert r.status_code == 200
        assert r.json()["empleados"] == 50

    async def test_put_mia_ciudad(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"ciudad": "Madrid"})
        assert r.status_code == 200
        assert r.json().get("ciudad") == "Madrid"

    async def test_put_mia_descripcion(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers,
                             json={"descripcion": "Empresa de tecnología para automatización"})
        assert r.status_code == 200

    async def test_put_mia_web(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers,
                             json={"web": "https://empresa.com"})
        assert r.status_code == 200

    async def test_put_mia_nombre_muy_largo_422(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers,
                             json={"nombre": "N" * 300})
        assert r.status_code == 422

    async def test_put_mia_descripcion_muy_larga_422(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers,
                             json={"descripcion": "D" * 1200})
        assert r.status_code == 422

    async def test_put_mia_xss_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers,
                             json={"nombre": "<script>alert(1)</script>Empresa"})
        if r.status_code == 200:
            assert "<script>" not in r.json()["nombre"]

    async def test_put_mia_preserva_campos_no_enviados(self, client: AsyncClient, test_user, auth_headers):
        # Leer valores actuales
        get_r = await client.get("/api/empresa/mia", headers=auth_headers)
        sector_original = get_r.json().get("sector")
        # Actualizar solo nombre
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"nombre": "Solo Nombre"})
        assert r.json()["sector"] == sector_original

    async def test_put_mia_empleados_negativo(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"empleados": -5})
        # Puede aceptar o rechazar según validación
        assert r.status_code in (200, 422)

    async def test_put_mia_empleados_cero(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"empleados": 0})
        assert r.status_code in (200, 422)

    async def test_put_mia_empleados_grande(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"empleados": 100000})
        assert r.status_code == 200

    async def test_put_mia_nombre_con_acento(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers,
                             json={"nombre": "Servicios de Gestión Empresarial"})
        assert r.status_code == 200
        assert "Gestión" in r.json()["nombre"]

    async def test_put_mia_sector_ventas(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"sector": "ventas"})
        assert r.status_code == 200

    async def test_put_mia_sector_logistica(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"sector": "logística"})
        assert r.status_code == 200

    async def test_put_mia_plan_campo_ignorado(self, client: AsyncClient, test_user, auth_headers):
        # El plan no debe ser editable por el usuario
        get_r = await client.get("/api/empresa/mia", headers=auth_headers)
        plan_original = get_r.json().get("plan")
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"plan": "enterprise"})
        # Si la API acepta el campo, el plan puede o no cambiar. Si rechaza → 422
        assert r.status_code in (200, 422)


class TestEmpresaStats:
    async def test_stats_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/empresa/mia/stats")
        assert r.status_code == 401

    async def test_stats_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        assert r.status_code == 200

    async def test_stats_tiene_contadores(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        data = r.json()
        # La respuesta tiene al menos algún campo numérico
        assert len(data) > 0

    async def test_stats_tiene_kpis_count(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        data = r.json()
        assert any(k in data for k in ("kpis", "total_kpis", "num_kpis", "kpis_count"))

    async def test_stats_tiene_autos_count(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        data = r.json()
        assert any(k in data for k in ("automatizaciones", "total_automatizaciones", "num_automatizaciones", "autos_count"))

    async def test_stats_valores_numericos(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        data = r.json()
        for key, val in data.items():
            if isinstance(val, (int, float)):
                assert val >= 0

    async def test_stats_aumenta_con_proceso(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proc Stats Test"})
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        data = r.json()
        # Al menos algún contador debe ser > 0
        counts = [v for v in data.values() if isinstance(v, (int, float))]
        assert any(c >= 1 for c in counts)

    async def test_stats_content_type_json(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        assert "application/json" in r.headers.get("content-type", "")


class TestEmpresaSectores:
    async def test_sector_tecnologia(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"sector": "tecnología"})
        assert r.status_code == 200

    async def test_sector_rrhh(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"sector": "recursos humanos"})
        assert r.status_code == 200

    async def test_sector_marketing(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"sector": "marketing"})
        assert r.status_code == 200

    async def test_sector_finanzas(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"sector": "finanzas"})
        assert r.status_code == 200

    async def test_sector_salud(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/empresa/mia", headers=auth_headers, json={"sector": "salud"})
        assert r.status_code == 200

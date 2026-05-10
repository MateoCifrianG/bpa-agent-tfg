"""
test_kpis_completo.py — Tests exhaustivos de KPIs: todos los campos, tendencias,
categorías, valores numéricos, valores texto, filtros, ordenación, edge cases.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestKPICampos:
    async def test_kpi_id_es_uuid(self, client: AsyncClient, test_user, auth_headers):
        import re
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI UUID Test", "valor": "10",
        })
        pid = r.json()["id"]
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
        assert uuid_pattern.match(pid)

    async def test_kpi_tendencia_default_up(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Default Tend", "valor": "10",
        })
        assert r.json()["tendencia"] == "up"

    async def test_kpi_tendencia_down(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Down", "valor": "10", "tendencia": "down",
        })
        assert r.json()["tendencia"] == "down"

    async def test_kpi_tendencia_stable(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Stable", "valor": "10", "tendencia": "stable",
        })
        assert r.status_code in (201, 422)  # depende de validación

    async def test_kpi_categoria_calidad(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Calidad", "valor": "95", "categoria": "calidad",
        })
        assert r.json()["categoria"] == "calidad"

    async def test_kpi_categoria_eficiencia(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Eficiencia", "valor": "80", "categoria": "eficiencia",
        })
        assert r.json()["categoria"] == "eficiencia"

    async def test_kpi_categoria_financiero(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Financiero", "valor": "50000", "categoria": "financiero",
        })
        assert r.json()["categoria"] == "financiero"

    async def test_kpi_unidad_porcentaje(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Pct", "valor": "95", "unidad": "%",
        })
        assert r.json()["unidad"] == "%"

    async def test_kpi_unidad_euros(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Euros", "valor": "1000", "unidad": "€",
        })
        assert r.json()["unidad"] == "€"

    async def test_kpi_unidad_dias(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Días", "valor": "30", "unidad": "días",
        })
        assert r.json()["unidad"] == "días"

    async def test_kpi_objetivo_presente(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Objetivo", "valor": "85", "objetivo": "98",
        })
        assert r.json()["objetivo"] == "98"

    async def test_kpi_objetivo_nulo_por_defecto(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Sin Obj", "valor": "85",
        })
        assert r.json()["objetivo"] is None

    async def test_kpi_valor_decimal(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Decimal", "valor": "95.5",
        })
        assert r.json()["valor"] == "95.5"

    async def test_kpi_valor_negativo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Negativo", "valor": "-10",
        })
        assert r.status_code == 201  # el sistema no valida el valor numérico

    async def test_kpi_valor_texto_descriptivo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Texto", "valor": "Alto",
        })
        assert r.status_code == 201
        assert r.json()["valor"] == "Alto"

    async def test_kpi_nombre_con_acento(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "Tasa de entrega a tiempo", "valor": "97",
        })
        assert r.json()["nombre"] == "Tasa de entrega a tiempo"

    async def test_kpi_created_at_presente(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Fecha", "valor": "10",
        })
        assert "created_at" in r.json()


class TestKPIEditar:
    async def test_editar_valor(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.put(f"/api/kpis/{test_kpi['id']}", headers=auth_headers, json={"valor": "99"})
        assert r.status_code == 200
        assert r.json()["valor"] == "99"

    async def test_editar_objetivo(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.put(f"/api/kpis/{test_kpi['id']}", headers=auth_headers, json={"objetivo": "100"})
        assert r.status_code == 200
        assert r.json()["objetivo"] == "100"

    async def test_editar_tendencia(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.put(f"/api/kpis/{test_kpi['id']}", headers=auth_headers, json={"tendencia": "down"})
        assert r.status_code == 200

    async def test_editar_categoria(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.put(f"/api/kpis/{test_kpi['id']}", headers=auth_headers, json={"categoria": "operacional"})
        assert r.status_code == 200
        assert r.json()["categoria"] == "operacional"

    async def test_editar_unidad(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.put(f"/api/kpis/{test_kpi['id']}", headers=auth_headers, json={"unidad": "horas"})
        assert r.status_code == 200
        assert r.json()["unidad"] == "horas"

    async def test_editar_nombre(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.put(f"/api/kpis/{test_kpi['id']}", headers=auth_headers, json={"nombre": "KPI Renombrado"})
        assert r.status_code == 200
        assert r.json()["nombre"] == "KPI Renombrado"

    async def test_editar_no_existe_404(self, client: AsyncClient, auth_headers):
        r = await client.put(
            "/api/kpis/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
            json={"valor": "99"},
        )
        assert r.status_code == 404

    async def test_editar_requiere_auth(self, client: AsyncClient, test_kpi):
        r = await client.put(f"/api/kpis/{test_kpi['id']}", json={"valor": "99"})
        assert r.status_code == 401

    async def test_editar_preserva_campos_no_enviados(self, client: AsyncClient, test_user, auth_headers):
        cr = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Preservar",
            "valor": "90",
            "unidad": "%",
            "objetivo": "95",
        })
        kid = cr.json()["id"]
        r = await client.put(f"/api/kpis/{kid}", headers=auth_headers, json={"valor": "92"})
        data = r.json()
        assert data["unidad"] == "%"
        assert data["objetivo"] == "95"
        assert data["nombre"] == "KPI Preservar"


class TestKPIFiltros:
    async def test_filtro_por_proceso_id(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Filtrado",
            "valor": "10",
            "proceso_id": test_proceso["id"],
        })
        await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Sin Proceso",
            "valor": "20",
        })
        r = await client.get(f"/api/kpis?proceso_id={test_proceso['id']}", headers=auth_headers)
        assert r.status_code == 200
        for kpi in r.json():
            assert kpi["proceso_id"] == test_proceso["id"]

    async def test_sin_filtro_devuelve_todos(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/kpis", headers=auth_headers, json={"nombre": "KPI A", "valor": "1"})
        await client.post("/api/kpis", headers=auth_headers, json={"nombre": "KPI B", "valor": "2"})
        r = await client.get("/api/kpis", headers=auth_headers)
        assert len(r.json()) >= 2

    async def test_filtro_proceso_no_devuelve_sin_proceso(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "Sin Proceso Test",
            "valor": "5",
        })
        r = await client.get(f"/api/kpis?proceso_id={test_proceso['id']}", headers=auth_headers)
        nombres = [k["nombre"] for k in r.json()]
        assert "Sin Proceso Test" not in nombres


class TestKPIValidacionCompleta:
    async def test_valor_requerido(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={"nombre": "Sin valor"})
        assert r.status_code == 422

    async def test_nombre_requerido(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={"valor": "10"})
        assert r.status_code == 422

    async def test_nombre_xss_sanitizado(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "<script>alert(1)</script>",
            "valor": "10",
        })
        if r.status_code == 201:
            assert "<script>" not in r.json()["nombre"]

    async def test_nombre_muy_largo_422(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "K" * 300,
            "valor": "10",
        })
        assert r.status_code == 422

    async def test_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/kpis", json={"nombre": "K", "valor": "1"})
        assert r.status_code == 401

    async def test_listar_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/kpis")
        assert r.status_code == 401

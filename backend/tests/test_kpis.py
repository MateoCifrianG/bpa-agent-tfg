"""
test_kpis.py — Tests completos de KPIs: CRUD, validación, vinculación, acceso.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestKPIsCRUD:
    async def test_listar_kpis_vacio(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/kpis", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_crear_kpi_minimo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Mínimo",
            "valor": "42",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["nombre"] == "KPI Mínimo"
        assert data["valor"] == "42"
        assert "id" in data

    async def test_crear_kpi_completo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "Tasa de entrega a tiempo",
            "valor": "95",
            "unidad": "%",
            "objetivo": "98",
            "tendencia": "up",
            "categoria": "calidad",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["unidad"] == "%"
        assert data["objetivo"] == "98"
        assert data["tendencia"] == "up"
        assert data["categoria"] == "calidad"

    async def test_obtener_kpi(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.get(f"/api/kpis/{test_kpi['id']}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == test_kpi["id"]

    async def test_obtener_kpi_no_existe(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/kpis/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert r.status_code == 404

    async def test_editar_kpi(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.put(f"/api/kpis/{test_kpi['id']}", headers=auth_headers, json={
            "valor": "99",
            "objetivo": "100",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["valor"] == "99"
        assert data["objetivo"] == "100"

    async def test_editar_kpi_nombre(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.put(f"/api/kpis/{test_kpi['id']}", headers=auth_headers, json={
            "nombre": "KPI Renombrado",
        })
        assert r.status_code == 200
        assert r.json()["nombre"] == "KPI Renombrado"

    async def test_eliminar_kpi(self, client: AsyncClient, test_user, auth_headers):
        cr = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI a borrar",
            "valor": "10",
        })
        kpi_id = cr.json()["id"]
        r = await client.delete(f"/api/kpis/{kpi_id}", headers=auth_headers)
        assert r.status_code == 204
        r2 = await client.get(f"/api/kpis/{kpi_id}", headers=auth_headers)
        assert r2.status_code == 404

    async def test_listar_kpis_devuelve_todos(self, client: AsyncClient, test_user, auth_headers):
        nombres = ["KPI A", "KPI B", "KPI C"]
        for n in nombres:
            await client.post("/api/kpis", headers=auth_headers, json={"nombre": n, "valor": "1"})
        r = await client.get("/api/kpis", headers=auth_headers)
        assert r.status_code == 200
        nombre_list = [k["nombre"] for k in r.json()]
        for n in nombres:
            assert n in nombre_list


class TestKPIsValidacion:
    async def test_crear_kpi_sin_nombre(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={"valor": "10"})
        assert r.status_code == 422

    async def test_crear_kpi_sin_valor(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={"nombre": "Sin valor"})
        assert r.status_code == 422

    async def test_crear_kpi_nombre_xss(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "<script>alert('xss')</script>",
            "valor": "5",
        })
        # Debe fallar (422) o sanitizar (201 sin script)
        if r.status_code == 201:
            assert "<script>" not in r.json()["nombre"]
        else:
            assert r.status_code == 422

    async def test_crear_kpi_tendencia_invalida(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Tendencia",
            "valor": "5",
            "tendencia": "diagonal",  # inválido
        })
        # Dependiendo de la validación, puede ser 422 o ignorado con default
        assert r.status_code in (201, 422)

    async def test_crear_kpi_nombre_demasiado_largo(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "K" * 300,
            "valor": "5",
        })
        assert r.status_code == 422


class TestKPIsVinculacion:
    async def test_kpi_vinculado_a_proceso(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI vinculado",
            "valor": "42",
            "proceso_id": test_proceso["id"],
        })
        assert r.status_code == 201
        assert r.json()["proceso_id"] == test_proceso["id"]

    async def test_listar_kpis_filtrado_por_proceso(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI en proceso",
            "valor": "10",
            "proceso_id": test_proceso["id"],
        })
        await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI sin proceso",
            "valor": "20",
        })
        r = await client.get(f"/api/kpis?proceso_id={test_proceso['id']}", headers=auth_headers)
        assert r.status_code == 200
        for kpi in r.json():
            assert kpi["proceso_id"] == test_proceso["id"]

    async def test_kpi_proceso_inexistente(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI proceso roto",
            "valor": "1",
            "proceso_id": "00000000-0000-0000-0000-000000000000",
        })
        assert r.status_code in (403, 404, 422)


class TestKPIsAcceso:
    async def test_kpis_requieren_auth(self, client: AsyncClient):
        r = await client.get("/api/kpis")
        assert r.status_code == 401

    async def test_crear_kpi_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/kpis", json={"nombre": "KPI", "valor": "1"})
        assert r.status_code == 401

    async def test_no_accede_kpi_de_otro_usuario(self, client: AsyncClient, auth_headers, admin_headers):
        cr = await client.post("/api/kpis", headers=admin_headers, json={
            "nombre": "KPI Admin",
            "valor": "99",
        })
        kpi_id = cr.json()["id"]
        r = await client.get(f"/api/kpis/{kpi_id}", headers=auth_headers)
        assert r.status_code == 404

    async def test_no_edita_kpi_de_otro_usuario(self, client: AsyncClient, auth_headers, admin_headers):
        cr = await client.post("/api/kpis", headers=admin_headers, json={
            "nombre": "KPI Admin",
            "valor": "99",
        })
        kpi_id = cr.json()["id"]
        r = await client.put(f"/api/kpis/{kpi_id}", headers=auth_headers, json={"valor": "0"})
        assert r.status_code == 404

    async def test_no_elimina_kpi_de_otro_usuario(self, client: AsyncClient, auth_headers, admin_headers):
        cr = await client.post("/api/kpis", headers=admin_headers, json={
            "nombre": "KPI Admin borrar",
            "valor": "1",
        })
        kpi_id = cr.json()["id"]
        r = await client.delete(f"/api/kpis/{kpi_id}", headers=auth_headers)
        assert r.status_code == 404

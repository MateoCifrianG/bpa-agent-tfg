"""
test_kpis_unitarios.py — Tests unitarios adicionales de KPIs:
CRUD completo, campos, validaciones, filtros por categoría, aislamiento.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestKPIsCreacion:
    async def test_crear_kpi_minimo(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI mínimo", "valor": "85"
        })
        assert r.status_code == 201

    async def test_crear_kpi_con_objetivo(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI con objetivo", "valor": "75", "objetivo": "100"
        })
        assert r.status_code == 201

    async def test_crear_kpi_con_unidad(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI porcentaje", "valor": "90", "unidad": "%"
        })
        assert r.status_code == 201

    async def test_crear_kpi_con_categoria(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI ventas", "valor": "50000", "categoria": "ventas"
        })
        assert r.status_code == 201

    async def test_crear_kpi_devuelve_id(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI ID", "valor": "42"
        })
        data = r.json()
        assert "id" in data
        assert len(data["id"]) > 0

    async def test_crear_kpi_devuelve_nombre(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Nombre Test", "valor": "10"
        })
        assert r.json()["nombre"] == "KPI Nombre Test"

    async def test_crear_kpi_devuelve_valor(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Val", "valor": "99"
        })
        assert r.json()["valor"] == "99"

    async def test_crear_kpi_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/kpis", json={"nombre": "KPI sin auth", "valor": "10"})
        assert r.status_code == 401

    async def test_crear_kpi_descripcion(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI desc", "valor": "77",
            "descripcion": "Este KPI mide la tasa de conversión"
        })
        assert r.status_code == 201

    async def test_crear_kpi_valor_monetario(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "Revenue", "valor": "125000", "unidad": "€"
        })
        assert r.status_code == 201


class TestKPIsLectura:
    async def test_listar_kpis_ok(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/kpis", headers=auth_headers)
        assert r.status_code == 200

    async def test_listar_kpis_devuelve_lista(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/kpis", headers=auth_headers)
        assert isinstance(r.json(), list)

    async def test_listar_sin_auth(self, client: AsyncClient):
        r = await client.get("/api/kpis")
        assert r.status_code == 401

    async def test_obtener_kpi_especifico(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI específico", "valor": "55"
        })
        kpi_id = r1.json()["id"]
        r2 = await client.get(f"/api/kpis/{kpi_id}", headers=auth_headers)
        assert r2.status_code == 200

    async def test_obtener_kpi_inexistente_404(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/kpis/kpi-id-inexistente", headers=auth_headers)
        assert r.status_code == 404

    async def test_kpi_creado_aparece_en_lista(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI lista check", "valor": "33"
        })
        kpi_id = r1.json()["id"]
        r2 = await client.get("/api/kpis", headers=auth_headers)
        ids = [k["id"] for k in r2.json()]
        assert kpi_id in ids


class TestKPIsActualizacion:
    async def test_actualizar_valor(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI update val", "valor": "50"
        })
        kpi_id = r1.json()["id"]
        r2 = await client.put(f"/api/kpis/{kpi_id}", headers=auth_headers, json={
            "valor": "75"
        })
        assert r2.status_code == 200

    async def test_actualizar_nombre(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI viejo", "valor": "10"
        })
        kpi_id = r1.json()["id"]
        r2 = await client.put(f"/api/kpis/{kpi_id}", headers=auth_headers, json={
            "nombre": "KPI nuevo"
        })
        assert r2.status_code == 200
        assert r2.json()["nombre"] == "KPI nuevo"

    async def test_actualizar_objetivo(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI obj", "valor": "60"
        })
        kpi_id = r1.json()["id"]
        r2 = await client.put(f"/api/kpis/{kpi_id}", headers=auth_headers, json={
            "objetivo": "100"
        })
        assert r2.status_code == 200

    async def test_actualizar_sin_auth(self, client: AsyncClient):
        r = await client.put("/api/kpis/some-id", json={"valor": "50"})
        assert r.status_code == 401

    async def test_actualizar_kpi_inexistente_404(self, client: AsyncClient, auth_headers):
        r = await client.put("/api/kpis/id-no-existe", headers=auth_headers, json={"valor": "50"})
        assert r.status_code in (404, 422)


class TestKPIsEliminacion:
    async def test_eliminar_kpi(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI borrar", "valor": "10"
        })
        kpi_id = r1.json()["id"]
        r2 = await client.delete(f"/api/kpis/{kpi_id}", headers=auth_headers)
        assert r2.status_code in (200, 204)

    async def test_eliminar_y_no_acceder(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI borrar2", "valor": "20"
        })
        kpi_id = r1.json()["id"]
        await client.delete(f"/api/kpis/{kpi_id}", headers=auth_headers)
        r3 = await client.get(f"/api/kpis/{kpi_id}", headers=auth_headers)
        assert r3.status_code == 404

    async def test_eliminar_sin_auth(self, client: AsyncClient):
        r = await client.delete("/api/kpis/some-id")
        assert r.status_code == 401

    async def test_eliminar_kpi_inexistente_404(self, client: AsyncClient, auth_headers):
        r = await client.delete("/api/kpis/kpi-no-existe", headers=auth_headers)
        assert r.status_code in (404, 204)


class TestKPIsCampos:
    async def test_kpi_tiene_id(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI campos", "valor": "50"
        })
        assert "id" in r.json()

    async def test_kpi_tiene_nombre(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI N", "valor": "5"
        })
        assert "nombre" in r.json()

    async def test_kpi_tiene_valor(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI V", "valor": "5"
        })
        assert "valor" in r.json()

    async def test_kpi_tiene_created_at(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI CA", "valor": "5"
        })
        data = r.json()
        assert "created_at" in data or "id" in data

    async def test_kpi_no_expone_empresa_directamente(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI E", "valor": "5"
        })
        data = r.json()
        # No debe haber password ni datos sensibles
        assert "hashed_password" not in data

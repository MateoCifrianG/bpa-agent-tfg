"""
test_procesos.py — Tests CRUD de procesos y KPIs.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestProcesos:
    async def test_listar_procesos_vacio(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/procesos", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_crear_proceso(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso Test Facturación",
            "descripcion": "Proceso de prueba para facturación de clientes",
            "responsable": "Ana García",
            "frecuencia": "mensual",
            "duracion_h": 20,
        })
        assert r.status_code == 201
        data = r.json()
        assert data["nombre"] == "Proceso Test Facturación"
        return data["id"]

    async def test_crear_proceso_nombre_obligatorio(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "descripcion": "Sin nombre",
        })
        assert r.status_code == 422

    async def test_obtener_proceso(self, client: AsyncClient, test_user, auth_headers):
        # Crear primero
        create_r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso Para Obtener",
        })
        proceso_id = create_r.json()["id"]
        # Obtener
        r = await client.get(f"/api/procesos/{proceso_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == proceso_id

    async def test_editar_proceso(self, client: AsyncClient, test_user, auth_headers):
        create_r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso Original",
        })
        proceso_id = create_r.json()["id"]

        r = await client.put(f"/api/procesos/{proceso_id}", headers=auth_headers, json={
            "nombre": "Proceso Editado",
            "descripcion": "Nueva descripción",
        })
        assert r.status_code == 200
        assert r.json()["nombre"] == "Proceso Editado"

    async def test_eliminar_proceso(self, client: AsyncClient, test_user, auth_headers):
        create_r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso A Eliminar",
        })
        proceso_id = create_r.json()["id"]

        r = await client.delete(f"/api/procesos/{proceso_id}", headers=auth_headers)
        assert r.status_code == 204

        # Verificar que ya no existe
        r2 = await client.get(f"/api/procesos/{proceso_id}", headers=auth_headers)
        assert r2.status_code == 404

    async def test_no_accede_a_proceso_de_otro_usuario(self, client: AsyncClient, auth_headers, admin_headers):
        # Admin crea un proceso
        admin_r = await client.post("/api/procesos", headers=admin_headers, json={"nombre": "Proceso Admin"})
        admin_proceso_id = admin_r.json()["id"]

        # Usuario normal intenta acceder
        r = await client.get(f"/api/procesos/{admin_proceso_id}", headers=auth_headers)
        assert r.status_code == 404


class TestKPIs:
    async def test_listar_kpis_vacio(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/kpis", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_crear_kpi(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "Tasa de entrega a tiempo",
            "valor": "95",
            "unidad": "%",
            "objetivo": "98",
            "categoria": "calidad",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["nombre"] == "Tasa de entrega a tiempo"
        assert data["valor"] == "95"

    async def test_crear_kpi_con_proceso(self, client: AsyncClient, test_user, auth_headers):
        # Crear proceso primero
        proc_r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso para KPI",
        })
        proceso_id = proc_r.json()["id"]

        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI vinculado",
            "valor": "42",
            "proceso_id": proceso_id,
        })
        assert r.status_code == 201
        assert r.json()["proceso_id"] == proceso_id

    async def test_eliminar_kpi(self, client: AsyncClient, test_user, auth_headers):
        create_r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI a eliminar",
            "valor": "10",
        })
        kpi_id = create_r.json()["id"]

        r = await client.delete(f"/api/kpis/{kpi_id}", headers=auth_headers)
        assert r.status_code == 204


class TestHealth:
    async def test_health_ok(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert "version" in r.json()

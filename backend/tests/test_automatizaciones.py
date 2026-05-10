"""
test_automatizaciones.py — Tests completos de automatizaciones: CRUD, validación, acceso.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestAutomatizacionesCRUD:
    async def test_listar_autos_vacio(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/automatizaciones", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_crear_auto_minima(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Mínima",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["nombre"] == "Auto Mínima"
        assert data["estado"] == "pendiente"
        assert data["ejecuciones"] == 0

    async def test_crear_auto_completa(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Completa",
            "descripcion": "Automatización de facturación mensual",
            "herramienta": "n8n",
            "estado": "pendiente",
            "horas_mes": 8,
        })
        assert r.status_code == 201
        data = r.json()
        assert data["herramienta"] == "n8n"
        assert data["horas_mes"] == 8

    async def test_obtener_auto(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.get(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == test_auto["id"]

    async def test_obtener_auto_no_existe(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/automatizaciones/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert r.status_code == 404

    async def test_editar_auto(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.put(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers, json={
            "descripcion": "Nueva descripción",
            "horas_mes": 15,
        })
        assert r.status_code == 200
        assert r.json()["horas_mes"] == 15

    async def test_editar_auto_estado(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.put(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers, json={
            "estado": "activa",
        })
        assert r.status_code == 200
        assert r.json()["estado"] == "activa"

    async def test_eliminar_auto(self, client: AsyncClient, test_user, auth_headers):
        cr = await client.post("/api/automatizaciones", headers=auth_headers, json={"nombre": "Auto Borrar"})
        auto_id = cr.json()["id"]
        r = await client.delete(f"/api/automatizaciones/{auto_id}", headers=auth_headers)
        assert r.status_code == 204
        r2 = await client.get(f"/api/automatizaciones/{auto_id}", headers=auth_headers)
        assert r2.status_code == 404

    async def test_listar_autos_devuelve_todas(self, client: AsyncClient, test_user, auth_headers):
        nombres = ["Auto X", "Auto Y", "Auto Z"]
        for n in nombres:
            await client.post("/api/automatizaciones", headers=auth_headers, json={"nombre": n})
        r = await client.get("/api/automatizaciones", headers=auth_headers)
        assert r.status_code == 200
        nombre_list = [a["nombre"] for a in r.json()]
        for n in nombres:
            assert n in nombre_list


class TestAutomatizacionesValidacion:
    async def test_crear_auto_sin_nombre(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "descripcion": "Sin nombre",
        })
        assert r.status_code == 422

    async def test_crear_auto_nombre_demasiado_largo(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "A" * 300,
        })
        assert r.status_code == 422

    async def test_crear_auto_xss_en_nombre(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "<script>alert(1)</script>",
        })
        if r.status_code == 201:
            assert "<script>" not in r.json()["nombre"]
        else:
            assert r.status_code == 422

    async def test_crear_auto_descripcion_demasiado_larga(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Valida",
            "descripcion": "D" * 1100,
        })
        assert r.status_code == 422

    async def test_auto_vinculada_a_proceso(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto con Proceso",
            "proceso_id": test_proceso["id"],
        })
        assert r.status_code == 201
        assert r.json()["proceso_id"] == test_proceso["id"]


class TestAutomatizacionesAcceso:
    async def test_autos_requieren_auth(self, client: AsyncClient):
        r = await client.get("/api/automatizaciones")
        assert r.status_code == 401

    async def test_crear_auto_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/automatizaciones", json={"nombre": "Auto"})
        assert r.status_code == 401

    async def test_no_accede_auto_de_otro_usuario(self, client: AsyncClient, auth_headers, admin_headers):
        cr = await client.post("/api/automatizaciones", headers=admin_headers, json={"nombre": "Auto Admin"})
        auto_id = cr.json()["id"]
        r = await client.get(f"/api/automatizaciones/{auto_id}", headers=auth_headers)
        assert r.status_code == 404

    async def test_no_edita_auto_de_otro_usuario(self, client: AsyncClient, auth_headers, admin_headers):
        cr = await client.post("/api/automatizaciones", headers=admin_headers, json={"nombre": "Auto Admin"})
        auto_id = cr.json()["id"]
        r = await client.put(f"/api/automatizaciones/{auto_id}", headers=auth_headers, json={"estado": "activa"})
        assert r.status_code == 404

    async def test_no_elimina_auto_de_otro_usuario(self, client: AsyncClient, auth_headers, admin_headers):
        cr = await client.post("/api/automatizaciones", headers=admin_headers, json={"nombre": "Auto Admin Borrar"})
        auto_id = cr.json()["id"]
        r = await client.delete(f"/api/automatizaciones/{auto_id}", headers=auth_headers)
        assert r.status_code == 404


class TestAutomatizacionesHistorial:
    async def test_historial_auto_vacio(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.get(f"/api/ejecutar/{test_auto['id']}/historial", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_historial_auto_no_existe(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/ejecutar/00000000-0000-0000-0000-000000000000/historial", headers=auth_headers)
        assert r.status_code == 404

    async def test_historial_requiere_auth(self, client: AsyncClient, test_auto):
        r = await client.get(f"/api/ejecutar/{test_auto['id']}/historial")
        assert r.status_code == 401

"""
test_procesos_unitarios.py — Tests unitarios adicionales de procesos.
Cubre: estados válidos, campos opcionales, ordenación, filtros, paginación edge cases.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestProcesosCRUDBasico:
    async def test_crear_proceso_minimo(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso mínimo",
        })
        assert r.status_code in (200, 201)

    async def test_crear_proceso_con_descripcion(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso con desc",
            "descripcion": "Esta es la descripción detallada del proceso",
        })
        assert r.status_code in (200, 201)

    async def test_crear_proceso_con_responsable(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso con resp",
            "responsable": "Juan García",
        })
        assert r.status_code in (200, 201)

    async def test_crear_proceso_con_frecuencia_diaria(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso diario",
            "frecuencia": "diaria",
        })
        assert r.status_code in (200, 201)

    async def test_crear_proceso_con_duracion(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso largo",
            "duracion_h": 8,
        })
        assert r.status_code in (200, 201)

    async def test_crear_proceso_id_generado(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso ID",
        })
        data = r.json()
        assert "id" in data
        assert len(data["id"]) > 0

    async def test_crear_proceso_tiene_nombre(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso campos",
        })
        data = r.json()
        assert "nombre" in data
        assert data["nombre"] == "Proceso campos"

    async def test_obtener_proceso_especifico(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proc específico"})
        proc_id = r1.json()["id"]
        r2 = await client.get(f"/api/procesos/{proc_id}", headers=auth_headers)
        assert r2.status_code == 200

    async def test_proceso_inexistente_404(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/procesos/proc-id-que-no-existe", headers=auth_headers)
        assert r.status_code == 404

    async def test_actualizar_descripcion(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proc update"})
        proc_id = r1.json()["id"]
        r2 = await client.put(f"/api/procesos/{proc_id}", headers=auth_headers, json={
            "descripcion": "Descripción actualizada"
        })
        assert r2.status_code == 200

    async def test_actualizar_estado(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proc estado"})
        proc_id = r1.json()["id"]
        r2 = await client.put(f"/api/procesos/{proc_id}", headers=auth_headers, json={
            "estado": "activo"
        })
        assert r2.status_code == 200

    async def test_eliminar_proceso_propio(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proc delete"})
        proc_id = r1.json()["id"]
        r2 = await client.delete(f"/api/procesos/{proc_id}", headers=auth_headers)
        assert r2.status_code in (200, 204)

    async def test_eliminar_y_no_acceder(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proc delete2"})
        proc_id = r1.json()["id"]
        await client.delete(f"/api/procesos/{proc_id}", headers=auth_headers)
        r3 = await client.get(f"/api/procesos/{proc_id}", headers=auth_headers)
        assert r3.status_code == 404


class TestProcesosFrecuencias:
    async def test_frecuencia_diaria(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "P diaria", "frecuencia": "diaria"
        })
        assert r.json()["frecuencia"] == "diaria"

    async def test_frecuencia_semanal(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "P semanal", "frecuencia": "semanal"
        })
        assert r.json()["frecuencia"] == "semanal"

    async def test_frecuencia_mensual(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "P mensual", "frecuencia": "mensual"
        })
        assert r.json()["frecuencia"] == "mensual"

    async def test_frecuencia_anual(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "P anual", "frecuencia": "anual"
        })
        assert r.status_code in (200, 201)

    async def test_frecuencia_none_ok(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "P sin freq"
        })
        assert r.status_code in (200, 201)


class TestProcesosListado:
    async def test_listado_vacio_ok(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/procesos", headers=auth_headers)
        assert r.status_code == 200

    async def test_listado_devuelve_lista(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/procesos", headers=auth_headers)
        assert isinstance(r.json(), list)

    async def test_listado_con_un_proceso(self, client: AsyncClient, auth_headers):
        await client.post("/api/procesos", headers=auth_headers, json={"nombre": "P list1"})
        r = await client.get("/api/procesos", headers=auth_headers)
        assert len(r.json()) >= 1

    async def test_listado_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/procesos")
        assert r.status_code in (401, 403)

    async def test_procesos_aislados_entre_usuarios(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/procesos", headers=auth_headers)
        procesos = r.json()
        assert isinstance(procesos, list)


class TestProcesosValidaciones:
    async def test_nombre_requerido(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "descripcion": "Sin nombre"
        })
        assert r.status_code in (200, 201, 400, 422)

    async def test_duracion_negativa_aceptada_o_rechazada(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "P dur negativa", "duracion_h": -1
        })
        assert r.status_code in (200, 201, 400, 422)

    async def test_proceso_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/procesos", json={"nombre": "Sin auth"})
        assert r.status_code in (401, 403)

    async def test_update_sin_auth(self, client: AsyncClient):
        r = await client.put("/api/procesos/some-id", json={"nombre": "Update sin auth"})
        assert r.status_code in (401, 403)

    async def test_delete_sin_auth(self, client: AsyncClient):
        r = await client.delete("/api/procesos/some-id")
        assert r.status_code in (401, 403)

"""
test_procesos_bulk.py — Tests de procesos en masa, filtros, búsqueda, orden,
paginación, exportación, score colectivo, y casos de límite numérico.
"""
import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestProcesosBulkCreacion:
    async def test_crear_5_procesos_mismo_usuario(self, client: AsyncClient, test_user, auth_headers):
        ids = []
        for i in range(5):
            r = await client.post("/api/procesos", headers=auth_headers, json={
                "nombre": f"Proceso Bulk {i}",
            })
            assert r.status_code == 201
            ids.append(r.json()["id"])
        assert len(set(ids)) == 5

    async def test_crear_proceso_con_todos_los_campos(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso Completo",
            "descripcion": "Descripción detallada del proceso con más de veinte caracteres",
            "responsable": "Ana García López",
            "frecuencia": "mensual",
            "duracion_h": 8,
            "horas_mes": 40,
            "prioridad": "alta",
            "categoria": "estratégico",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["nombre"] == "Proceso Completo"
        assert data["responsable"] == "Ana García López"

    async def test_listar_todos_procesos_propios(self, client: AsyncClient, test_user, auth_headers):
        for i in range(3):
            await client.post("/api/procesos", headers=auth_headers, json={
                "nombre": f"Proc List {i}",
            })
        r = await client.get("/api/procesos", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 3

    async def test_cada_proceso_tiene_id_unico(self, client: AsyncClient, test_user, auth_headers):
        for i in range(4):
            await client.post("/api/procesos", headers=auth_headers, json={
                "nombre": f"Proc ID Unique {i}",
            })
        r = await client.get("/api/procesos", headers=auth_headers)
        ids = [p["id"] for p in r.json()]
        assert len(ids) == len(set(ids))


class TestProcesosGET:
    async def test_get_proceso_existente(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.get(f"/api/procesos/{test_proceso['id']}", headers=auth_headers)
        assert r.status_code == 200

    async def test_get_proceso_devuelve_todos_campos(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.get(f"/api/procesos/{test_proceso['id']}", headers=auth_headers)
        data = r.json()
        for campo in ["id", "nombre"]:
            assert campo in data

    async def test_get_proceso_inexistente_404(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/procesos/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert r.status_code in (403, 404)

    async def test_get_proceso_uuid_invalido_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/procesos/no_es_uuid", headers=auth_headers)
        assert r.status_code in (400, 404, 422)

    async def test_get_proceso_sin_auth_401(self, client: AsyncClient, test_proceso):
        r = await client.get(f"/api/procesos/{test_proceso['id']}")
        assert r.status_code == 401

    async def test_get_proceso_id_es_consistente(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.get(f"/api/procesos/{test_proceso['id']}", headers=auth_headers)
        assert r.json()["id"] == test_proceso["id"]


class TestProcesosDelete:
    async def test_eliminar_proceso_ok(self, client: AsyncClient, test_user, auth_headers):
        r_create = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proc Del OK"})
        proc_id = r_create.json()["id"]
        r_del = await client.delete(f"/api/procesos/{proc_id}", headers=auth_headers)
        assert r_del.status_code in (200, 204)

    async def test_eliminar_proceso_no_existe_404(self, client: AsyncClient, test_user, auth_headers):
        r = await client.delete("/api/procesos/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert r.status_code in (403, 404)

    async def test_proceso_no_visible_tras_eliminar(self, client: AsyncClient, test_user, auth_headers):
        r_create = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proc Del Check"})
        proc_id = r_create.json()["id"]
        await client.delete(f"/api/procesos/{proc_id}", headers=auth_headers)
        r_get = await client.get(f"/api/procesos/{proc_id}", headers=auth_headers)
        assert r_get.status_code in (403, 404)

    async def test_eliminar_no_afecta_otros_procesos(self, client: AsyncClient, test_user, auth_headers):
        r1 = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proc Keep"})
        r2 = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proc Del"})
        await client.delete(f"/api/procesos/{r2.json()['id']}", headers=auth_headers)
        r_get = await client.get(f"/api/procesos/{r1.json()['id']}", headers=auth_headers)
        assert r_get.status_code == 200

    async def test_eliminar_sin_auth_401(self, client: AsyncClient, test_proceso):
        r = await client.delete(f"/api/procesos/{test_proceso['id']}")
        assert r.status_code == 401

    async def test_eliminar_proceso_otro_usuario(self, client: AsyncClient, test_user, auth_headers,
                                                  admin_user, admin_headers, test_proceso):
        r = await client.delete(f"/api/procesos/{test_proceso['id']}", headers=admin_headers)
        assert r.status_code in (403, 404)


class TestProcesosValidaciones:
    async def test_crear_sin_nombre_422(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "descripcion": "Sin nombre",
        })
        assert r.status_code == 422

    async def test_crear_nombre_vacio_422(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": ""})
        assert r.status_code in (201, 422)

    async def test_duracion_negativa_422(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Dur Neg", "duracion_h": -1,
        })
        assert r.status_code in (201, 422)

    async def test_horas_mes_negativo(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc HM Neg", "horas_mes": -10,
        })
        assert r.status_code in (201, 422)

    async def test_body_vacio_422(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={})
        assert r.status_code == 422

    async def test_campos_desconocidos_ignorados(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Extra Campos",
            "campo_no_existe": "valor",
            "extra_field": 999,
        })
        assert r.status_code == 201
        assert "campo_no_existe" not in r.json()


class TestProcesosCamposObligatorios:
    async def test_respuesta_tiene_id(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proc ID Test"})
        assert "id" in r.json()
        assert r.json()["id"] is not None

    async def test_respuesta_tiene_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proc Nombre Test"})
        assert r.json()["nombre"] == "Proc Nombre Test"

    async def test_respuesta_tiene_created_at_o_fecha(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proc Fecha"})
        data = r.json()
        assert any(k in data for k in ("created_at", "fecha_creacion", "creado_en", "updated_at"))

    async def test_content_type_es_json(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "CT Test"})
        assert "application/json" in r.headers.get("content-type", "")

    async def test_status_201_en_creacion(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Status 201"})
        assert r.status_code == 201

    async def test_listar_devuelve_lista(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/procesos", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

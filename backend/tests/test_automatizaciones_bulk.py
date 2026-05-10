"""
test_automatizaciones_bulk.py — Tests de automatizaciones en masa: creación bulk,
herramientas, estados, edición de campos, aislamiento, edge cases de campos.
"""
import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestAutosBulkCreacion:
    async def test_crear_10_autos(self, client: AsyncClient, test_user, auth_headers):
        ids = []
        for i in range(10):
            r = await client.post("/api/automatizaciones", headers=auth_headers, json={
                "nombre": f"Auto Bulk {i}",
            })
            assert r.status_code == 201
            ids.append(r.json()["id"])
        assert len(set(ids)) == 10

    async def test_crear_auto_con_todos_campos(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Completa",
            "descripcion": "Descripción de prueba de la automatización",
            "herramienta": "n8n",
            "horas_mes": 8,
            "estado": "activa",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["nombre"] == "Auto Completa"

    async def test_listar_autos_devuelve_lista(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/automatizaciones", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_listar_autos_crece_tras_crear(self, client: AsyncClient, test_user, auth_headers):
        before = len((await client.get("/api/automatizaciones", headers=auth_headers)).json())
        for i in range(3):
            await client.post("/api/automatizaciones", headers=auth_headers, json={
                "nombre": f"Auto List {i}"
            })
        after = (await client.get("/api/automatizaciones", headers=auth_headers)).json()
        assert len(after) >= before + 3

    async def test_ids_autos_son_unicos(self, client: AsyncClient, test_user, auth_headers):
        for i in range(5):
            await client.post("/api/automatizaciones", headers=auth_headers, json={
                "nombre": f"Auto UUID {i}"
            })
        r = await client.get("/api/automatizaciones", headers=auth_headers)
        ids = [a["id"] for a in r.json()]
        assert len(ids) == len(set(ids))


class TestAutosCamposObligatorios:
    async def test_auto_tiene_id(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={"nombre": "Auto ID Test"})
        assert "id" in r.json()

    async def test_auto_tiene_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={"nombre": "Auto Nombre Test"})
        assert r.json()["nombre"] == "Auto Nombre Test"

    async def test_auto_tiene_estado(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={"nombre": "Auto Estado Test"})
        data = r.json()
        assert "estado" in data

    async def test_auto_status_201(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={"nombre": "Auto 201"})
        assert r.status_code == 201

    async def test_auto_content_type_json(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={"nombre": "Auto CT"})
        assert "application/json" in r.headers.get("content-type", "")

    async def test_auto_tiene_fecha(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={"nombre": "Auto Fecha"})
        data = r.json()
        assert any(k in data for k in ("created_at", "updated_at", "creado_en"))


class TestAutosHerramientas:
    async def test_auto_herramienta_n8n(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto n8n", "herramienta": "n8n"
        })
        assert r.status_code == 201
        if "herramienta" in r.json():
            assert r.json()["herramienta"] == "n8n"

    async def test_auto_herramienta_zapier(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Zapier", "herramienta": "zapier"
        })
        assert r.status_code == 201

    async def test_auto_herramienta_make(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Make", "herramienta": "make"
        })
        assert r.status_code == 201

    async def test_auto_herramienta_python(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Python", "herramienta": "python"
        })
        assert r.status_code == 201

    async def test_auto_sin_herramienta_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={"nombre": "Auto No Tool"})
        assert r.status_code == 201


class TestAutosEstados:
    async def test_auto_estado_default_activa_o_borrador(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={"nombre": "Auto Estado Def"})
        data = r.json()
        if "estado" in data:
            assert data["estado"] in ("activa", "borrador", "inactiva", "draft", "pendiente")

    async def test_auto_estado_activa(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Activa", "estado": "activa"
        })
        assert r.status_code == 201

    async def test_auto_estado_inactiva(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Inactiva", "estado": "inactiva"
        })
        assert r.status_code in (201, 422)

    async def test_auto_horas_mes_5(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Horas 5", "horas_mes": 5
        })
        assert r.status_code == 201

    async def test_auto_horas_mes_0(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Horas 0", "horas_mes": 0
        })
        assert r.status_code in (201, 422)


class TestAutosGET:
    async def test_get_auto_existente(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.get(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers)
        assert r.status_code == 200

    async def test_get_auto_devuelve_id(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.get(f"/api/automatizaciones/{test_auto['id']}", headers=auth_headers)
        assert r.json()["id"] == test_auto["id"]

    async def test_get_auto_inexistente_404(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/automatizaciones/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert r.status_code in (403, 404)

    async def test_get_auto_sin_auth_401(self, client: AsyncClient, test_auto):
        r = await client.get(f"/api/automatizaciones/{test_auto['id']}")
        assert r.status_code == 401

    async def test_get_auto_uuid_invalido(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/automatizaciones/no_uuid", headers=auth_headers)
        assert r.status_code in (400, 404, 422)

    async def test_get_auto_otro_usuario_403(self, client: AsyncClient, test_user, auth_headers,
                                              admin_user, admin_headers, test_auto):
        r = await client.get(f"/api/automatizaciones/{test_auto['id']}", headers=admin_headers)
        assert r.status_code in (403, 404)


class TestAutosEdicion:
    async def test_editar_auto_nombre_ok(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.put(
            f"/api/automatizaciones/{test_auto['id']}",
            headers=auth_headers,
            json={"nombre": "Auto Editada"},
        )
        assert r.status_code == 200
        assert r.json()["nombre"] == "Auto Editada"

    async def test_editar_auto_preserva_id(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.put(
            f"/api/automatizaciones/{test_auto['id']}",
            headers=auth_headers,
            json={"nombre": "Auto ID Preserved"},
        )
        assert r.status_code == 200
        assert r.json()["id"] == test_auto["id"]

    async def test_editar_auto_sin_auth_401(self, client: AsyncClient, test_auto):
        r = await client.put(
            f"/api/automatizaciones/{test_auto['id']}",
            json={"nombre": "Sin Auth"},
        )
        assert r.status_code == 401

    async def test_editar_auto_no_existente_404(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put(
            "/api/automatizaciones/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
            json={"nombre": "No Existe"},
        )
        assert r.status_code in (403, 404)

    async def test_editar_auto_otro_usuario_403(self, client: AsyncClient, test_user, auth_headers,
                                                 admin_user, admin_headers, test_auto):
        r = await client.put(
            f"/api/automatizaciones/{test_auto['id']}",
            headers=admin_headers,
            json={"nombre": "Admin Edit"},
        )
        assert r.status_code in (403, 404)


class TestAutosDelete:
    async def test_eliminar_auto_ok(self, client: AsyncClient, test_user, auth_headers):
        r_create = await client.post("/api/automatizaciones", headers=auth_headers, json={"nombre": "Auto Del OK"})
        auto_id = r_create.json()["id"]
        r_del = await client.delete(f"/api/automatizaciones/{auto_id}", headers=auth_headers)
        assert r_del.status_code in (200, 204)

    async def test_auto_no_visible_tras_eliminar(self, client: AsyncClient, test_user, auth_headers):
        r_create = await client.post("/api/automatizaciones", headers=auth_headers, json={"nombre": "Auto Del Check"})
        auto_id = r_create.json()["id"]
        await client.delete(f"/api/automatizaciones/{auto_id}", headers=auth_headers)
        r_get = await client.get(f"/api/automatizaciones/{auto_id}", headers=auth_headers)
        assert r_get.status_code in (403, 404)

    async def test_eliminar_auto_sin_auth_401(self, client: AsyncClient, test_auto):
        r = await client.delete(f"/api/automatizaciones/{test_auto['id']}")
        assert r.status_code == 401

    async def test_eliminar_auto_no_existente_404(self, client: AsyncClient, test_user, auth_headers):
        r = await client.delete("/api/automatizaciones/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert r.status_code in (403, 404)

    async def test_eliminar_auto_no_afecta_otras(self, client: AsyncClient, test_user, auth_headers):
        r1 = await client.post("/api/automatizaciones", headers=auth_headers, json={"nombre": "Auto Keep"})
        r2 = await client.post("/api/automatizaciones", headers=auth_headers, json={"nombre": "Auto Del"})
        await client.delete(f"/api/automatizaciones/{r2.json()['id']}", headers=auth_headers)
        r_get = await client.get(f"/api/automatizaciones/{r1.json()['id']}", headers=auth_headers)
        assert r_get.status_code == 200


class TestAutosValidaciones:
    async def test_crear_sin_nombre_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "descripcion": "Sin nombre"
        })
        assert r.status_code == 422

    async def test_body_vacio_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={})
        assert r.status_code == 422

    async def test_campos_extra_ignorados(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto Extra", "campo_falso": "x"
        })
        assert r.status_code == 201
        assert "campo_falso" not in r.json()

    async def test_nombre_con_acento_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Automatización de facturación"
        })
        assert r.status_code == 201

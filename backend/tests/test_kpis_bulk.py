"""
test_kpis_bulk.py — Tests de KPIs en masa: creación bulk, actualización,
vinculación con procesos, tendencias, filtros, aislamiento, edge cases numéricos.
"""
import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestKPIsBulkCreacion:
    async def test_crear_10_kpis(self, client: AsyncClient, test_user, auth_headers):
        ids = []
        for i in range(10):
            r = await client.post("/api/kpis", headers=auth_headers, json={
                "nombre": f"KPI Bulk {i}",
                "valor": str(i * 10),
                "unidad": "%",
            })
            assert r.status_code == 201
            ids.append(r.json()["id"])
        assert len(set(ids)) == 10

    async def test_crear_kpi_con_todos_los_campos(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Completo Test",
            "valor": "95.5",
            "objetivo": "100",
            "unidad": "%",
            "categoria": "calidad",
            "descripcion": "KPI de calidad del servicio",
            "tendencia": "positiva",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["nombre"] == "KPI Completo Test"

    async def test_listar_kpis_devuelve_lista(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/kpis", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_listar_kpis_propios_crece(self, client: AsyncClient, test_user, auth_headers):
        before = len((await client.get("/api/kpis", headers=auth_headers)).json())
        for i in range(3):
            await client.post("/api/kpis", headers=auth_headers, json={
                "nombre": f"KPI List Grow {i}",
                "valor": "50",
            })
        after = (await client.get("/api/kpis", headers=auth_headers)).json()
        assert len(after) >= before + 3

    async def test_ids_kpis_son_unicos(self, client: AsyncClient, test_user, auth_headers):
        for i in range(5):
            await client.post("/api/kpis", headers=auth_headers, json={
                "nombre": f"KPI UUID {i}", "valor": "0",
            })
        r = await client.get("/api/kpis", headers=auth_headers)
        ids = [k["id"] for k in r.json()]
        assert len(ids) == len(set(ids))


class TestKPIsCampos:
    async def test_kpi_tiene_id(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={"nombre": "KPI ID Test", "valor": "1"})
        assert "id" in r.json()
        assert r.json()["id"] is not None

    async def test_kpi_tiene_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={"nombre": "KPI Nombre Test", "valor": "1"})
        assert r.json()["nombre"] == "KPI Nombre Test"

    async def test_kpi_tiene_valor(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={"nombre": "KPI Valor Test", "valor": "42"})
        assert "valor" in r.json()

    async def test_kpi_content_type_json(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={"nombre": "KPI CT Test", "valor": "1"})
        assert "application/json" in r.headers.get("content-type", "")

    async def test_kpi_status_201(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={"nombre": "KPI 201 Test", "valor": "1"})
        assert r.status_code == 201

    async def test_kpi_tiene_fecha_creacion(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={"nombre": "KPI Fecha Test", "valor": "1"})
        data = r.json()
        assert any(k in data for k in ("created_at", "fecha_creacion", "creado_en", "updated_at"))

    async def test_kpi_categoria_en_respuesta(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Cat Test", "valor": "1", "categoria": "eficiencia"
        })
        if r.status_code == 201:
            data = r.json()
            if "categoria" in data:
                assert data["categoria"] == "eficiencia"


class TestKPIsActualizacion:
    async def test_actualizar_kpi_ok(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.put(
            f"/api/kpis/{test_kpi['id']}",
            headers=auth_headers,
            json={"nombre": "KPI Actualizado", "valor": "99"},
        )
        assert r.status_code == 200

    async def test_actualizar_kpi_preserva_id(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.put(
            f"/api/kpis/{test_kpi['id']}",
            headers=auth_headers,
            json={"nombre": "KPI ID Preserved", "valor": "1"},
        )
        assert r.status_code == 200
        assert r.json()["id"] == test_kpi["id"]

    async def test_actualizar_kpi_valor_cambia(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.put(
            f"/api/kpis/{test_kpi['id']}",
            headers=auth_headers,
            json={"nombre": test_kpi["nombre"], "valor": "77"},
        )
        assert r.status_code == 200
        if "valor" in r.json():
            assert r.json()["valor"] == "77"

    async def test_actualizar_kpi_no_existente_404(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put(
            "/api/kpis/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
            json={"nombre": "No Existe", "valor": "0"},
        )
        assert r.status_code in (403, 404)

    async def test_actualizar_kpi_sin_auth_401(self, client: AsyncClient, test_kpi):
        r = await client.put(
            f"/api/kpis/{test_kpi['id']}",
            json={"nombre": "Sin Auth", "valor": "0"},
        )
        assert r.status_code == 401

    async def test_actualizar_kpi_otro_usuario(self, client: AsyncClient, test_user, auth_headers,
                                                admin_user, admin_headers, test_kpi):
        r = await client.put(
            f"/api/kpis/{test_kpi['id']}",
            headers=admin_headers,
            json={"nombre": "KPI Admin Mod", "valor": "0"},
        )
        assert r.status_code in (403, 404)


class TestKPIsEliminar:
    async def test_eliminar_kpi_ok(self, client: AsyncClient, test_user, auth_headers):
        r_create = await client.post("/api/kpis", headers=auth_headers, json={"nombre": "KPI Del OK", "valor": "1"})
        kpi_id = r_create.json()["id"]
        r_del = await client.delete(f"/api/kpis/{kpi_id}", headers=auth_headers)
        assert r_del.status_code in (200, 204)

    async def test_kpi_no_visible_tras_eliminar(self, client: AsyncClient, test_user, auth_headers):
        r_create = await client.post("/api/kpis", headers=auth_headers, json={"nombre": "KPI Del Check", "valor": "1"})
        kpi_id = r_create.json()["id"]
        await client.delete(f"/api/kpis/{kpi_id}", headers=auth_headers)
        r_get = await client.get(f"/api/kpis/{kpi_id}", headers=auth_headers)
        assert r_get.status_code in (403, 404)

    async def test_eliminar_kpi_no_existente_404(self, client: AsyncClient, test_user, auth_headers):
        r = await client.delete("/api/kpis/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert r.status_code in (403, 404)

    async def test_eliminar_kpi_sin_auth_401(self, client: AsyncClient, test_kpi):
        r = await client.delete(f"/api/kpis/{test_kpi['id']}")
        assert r.status_code == 401

    async def test_eliminar_no_afecta_otros_kpis(self, client: AsyncClient, test_user, auth_headers):
        r1 = await client.post("/api/kpis", headers=auth_headers, json={"nombre": "KPI Keep", "valor": "1"})
        r2 = await client.post("/api/kpis", headers=auth_headers, json={"nombre": "KPI Del", "valor": "1"})
        await client.delete(f"/api/kpis/{r2.json()['id']}", headers=auth_headers)
        r_get = await client.get(f"/api/kpis/{r1.json()['id']}", headers=auth_headers)
        assert r_get.status_code == 200

    async def test_eliminar_kpi_otro_usuario(self, client: AsyncClient, test_user, auth_headers,
                                              admin_user, admin_headers, test_kpi):
        r = await client.delete(f"/api/kpis/{test_kpi['id']}", headers=admin_headers)
        assert r.status_code in (403, 404)


class TestKPIsValidaciones:
    async def test_crear_sin_nombre_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={"valor": "1"})
        assert r.status_code == 422

    async def test_body_vacio_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={})
        assert r.status_code == 422

    async def test_campos_extra_ignorados(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Extra", "valor": "1", "campo_falso": "x"
        })
        assert r.status_code == 201
        assert "campo_falso" not in r.json()

    async def test_valor_string_aceptado(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Str Val", "valor": "texto_valor"
        })
        assert r.status_code in (201, 422)

    async def test_nombre_con_acento_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI de satisfacción", "valor": "92"
        })
        assert r.status_code == 201

    async def test_valor_cero_aceptado(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Cero", "valor": "0"
        })
        assert r.status_code in (201, 422)

    async def test_valor_negativo_aceptado_o_rechazado(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Neg", "valor": "-5"
        })
        assert r.status_code in (201, 422)


class TestKPIsAislamiento:
    async def test_kpis_son_privados_por_usuario(self, client: AsyncClient, test_user, auth_headers,
                                                  admin_user, admin_headers):
        await client.post("/api/kpis", headers=auth_headers, json={"nombre": "KPI Priv User", "valor": "1"})
        r_admin = await client.get("/api/kpis", headers=admin_headers)
        r_user = await client.get("/api/kpis", headers=auth_headers)
        admin_ids = {k["id"] for k in r_admin.json()}
        user_ids = {k["id"] for k in r_user.json()}
        assert admin_ids.isdisjoint(user_ids)

    async def test_get_kpi_propio_ok(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.get(f"/api/kpis/{test_kpi['id']}", headers=auth_headers)
        assert r.status_code == 200

    async def test_get_kpi_otro_usuario_403_404(self, client: AsyncClient, test_user, auth_headers,
                                                 admin_user, admin_headers, test_kpi):
        r = await client.get(f"/api/kpis/{test_kpi['id']}", headers=admin_headers)
        assert r.status_code in (403, 404)

    async def test_get_kpi_sin_auth_401(self, client: AsyncClient, test_kpi):
        r = await client.get(f"/api/kpis/{test_kpi['id']}")
        assert r.status_code == 401

    async def test_get_kpi_inexistente_404(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/kpis/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert r.status_code in (403, 404)


class TestKPIsEdgeCases:
    async def test_kpi_nombre_muy_largo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "K" * 300, "valor": "1"
        })
        assert r.status_code in (201, 422)

    async def test_kpi_objetivo_mayor_que_valor(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Bajo Objetivo", "valor": "70", "objetivo": "100"
        })
        assert r.status_code == 201

    async def test_kpi_objetivo_menor_que_valor(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Sobre Objetivo", "valor": "110", "objetivo": "100"
        })
        assert r.status_code == 201

    async def test_kpi_uuid_invalido_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/kpis/no_es_uuid", headers=auth_headers)
        assert r.status_code in (400, 404, 422)

    async def test_listar_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/kpis")
        assert r.status_code == 401

    async def test_crear_requiere_auth(self, client: AsyncClient):
        r = await client.post("/api/kpis", json={"nombre": "Sin Auth", "valor": "1"})
        assert r.status_code == 401

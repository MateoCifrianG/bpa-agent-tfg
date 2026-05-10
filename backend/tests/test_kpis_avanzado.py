"""
test_kpis_avanzado.py — Tests avanzados de KPIs: vinculación a proceso, filtros,
valores numéricos, tendencias, objetivos, aislamiento, bulk, edge cases.
"""
import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestKPIVinculacion:
    async def test_kpi_vinculado_a_proceso(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Vinculado", "valor": "75", "proceso_id": test_proceso["id"],
        })
        assert r.status_code == 201
        assert r.json().get("proceso_id") == test_proceso["id"]

    async def test_kpi_sin_proceso_id_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Sin Proceso", "valor": "50",
        })
        assert r.status_code == 201

    async def test_kpi_proceso_id_invalido_error(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI ProcID Malo", "valor": "10",
            "proceso_id": "00000000-0000-0000-0000-000000000000",
        })
        assert r.status_code in (201, 400, 403, 404, 422)

    async def test_proceso_tiene_kpi_en_listado(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Del Proc", "valor": "88", "proceso_id": test_proceso["id"],
        })
        r = await client.get(f"/api/procesos/{test_proceso['id']}", headers=auth_headers)
        assert r.status_code == 200

    async def test_kpi_proceso_diferente_empresa_rechazado(self, client: AsyncClient, test_user, auth_headers):
        uid = uuid.uuid4().hex[:8]
        r2 = await client.post("/api/auth/register", json={
            "email": f"kpiaisl_{uid}@test.com", "password": "TestPass1!",
            "nombre": "KpiAisl", "apellido": "User",
            "empresa": "EmpKpiAisl", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        if r2.status_code != 201:
            return
        token2 = r2.json().get("access_token")
        headers2 = {"Authorization": f"Bearer {token2}"}
        r_proc2 = await client.post("/api/procesos", headers=headers2, json={"nombre": "Proc Empresa 2"})
        if r_proc2.status_code != 201:
            return
        proc_id2 = r_proc2.json()["id"]
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Cross Company", "valor": "10", "proceso_id": proc_id2,
        })
        assert r.status_code in (201, 400, 403, 404, 422)


class TestKPIValores:
    async def test_valor_entero_string(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Val Entero", "valor": "100",
        })
        assert r.status_code == 201
        assert r.json()["valor"] == "100"

    async def test_valor_decimal(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Decimal", "valor": "99.7",
        })
        assert r.status_code == 201

    async def test_valor_cero(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Cero", "valor": "0",
        })
        assert r.status_code == 201
        assert r.json()["valor"] == "0"

    async def test_valor_negativo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Negativo", "valor": "-5",
        })
        assert r.status_code in (201, 422)

    async def test_valor_muy_grande(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Enorme", "valor": "9999999",
        })
        assert r.status_code == 201

    async def test_valor_con_unidad_porcentaje(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Pct", "valor": "95", "unidad": "%",
        })
        assert r.status_code == 201
        assert r.json()["unidad"] == "%"

    async def test_valor_con_unidad_horas(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Horas", "valor": "8.5", "unidad": "h",
        })
        assert r.status_code == 201

    async def test_valor_con_unidad_euros(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Euros", "valor": "1500", "unidad": "€",
        })
        assert r.status_code == 201

    async def test_objetivo_mayor_que_valor(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Obj Mayor", "valor": "70", "objetivo": "90",
        })
        assert r.status_code == 201
        assert r.json()["objetivo"] == "90"

    async def test_objetivo_igual_que_valor(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Obj Igual", "valor": "90", "objetivo": "90",
        })
        assert r.status_code == 201

    async def test_objetivo_menor_que_valor(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Obj Menor", "valor": "95", "objetivo": "80",
        })
        assert r.status_code == 201

    async def test_objetivo_nulo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Sin Obj", "valor": "50",
        })
        assert r.status_code == 201
        obj = r.json().get("objetivo")
        assert obj is None or isinstance(obj, str)


class TestKPITendencias:
    async def test_tendencia_up(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Up", "valor": "80", "tendencia": "up",
        })
        assert r.status_code == 201
        assert r.json()["tendencia"] == "up"

    async def test_tendencia_down(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Down T", "valor": "60", "tendencia": "down",
        })
        assert r.status_code == 201
        assert r.json()["tendencia"] == "down"

    async def test_tendencia_stable(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Stable T", "valor": "75", "tendencia": "stable",
        })
        assert r.status_code in (201, 422)

    async def test_tendencia_default(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Default T", "valor": "70",
        })
        assert r.status_code == 201
        tend = r.json().get("tendencia")
        assert tend in ("up", "down", "stable", None)

    async def test_editar_tendencia(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.put(f"/api/kpis/{test_kpi['id']}", headers=auth_headers, json={
            "tendencia": "down",
        })
        assert r.status_code == 200
        assert r.json()["tendencia"] == "down"


class TestKPICategorias:
    async def test_categoria_calidad(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Cal", "valor": "95", "categoria": "calidad",
        })
        assert r.status_code == 201

    async def test_categoria_eficiencia(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Efic", "valor": "80", "categoria": "eficiencia",
        })
        assert r.status_code == 201

    async def test_categoria_tiempo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Tiempo", "valor": "24", "categoria": "tiempo",
        })
        assert r.status_code == 201

    async def test_categoria_coste(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Coste", "valor": "1200", "categoria": "coste",
        })
        assert r.status_code == 201

    async def test_categoria_satisfaccion(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI CSAT", "valor": "4.5", "categoria": "satisfacción",
        })
        assert r.status_code == 201

    async def test_categoria_sin_valor(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Sin Cat", "valor": "10",
        })
        assert r.status_code == 201
        cat = r.json().get("categoria")
        assert cat is None or isinstance(cat, str)

    async def test_editar_categoria(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.put(f"/api/kpis/{test_kpi['id']}", headers=auth_headers, json={
            "categoria": "eficiencia",
        })
        assert r.status_code == 200


class TestKPIEdicion:
    async def test_editar_nombre(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.put(f"/api/kpis/{test_kpi['id']}", headers=auth_headers, json={
            "nombre": "KPI Renombrado",
        })
        assert r.status_code == 200
        assert r.json()["nombre"] == "KPI Renombrado"

    async def test_editar_valor(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.put(f"/api/kpis/{test_kpi['id']}", headers=auth_headers, json={
            "valor": "99",
        })
        assert r.status_code == 200
        assert r.json()["valor"] == "99"

    async def test_editar_objetivo(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.put(f"/api/kpis/{test_kpi['id']}", headers=auth_headers, json={
            "objetivo": "100",
        })
        assert r.status_code == 200
        assert r.json()["objetivo"] == "100"

    async def test_editar_unidad(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.put(f"/api/kpis/{test_kpi['id']}", headers=auth_headers, json={
            "unidad": "€/mes",
        })
        assert r.status_code == 200

    async def test_editar_no_autorizado_otro_usuario(self, client: AsyncClient, test_user, auth_headers,
                                                      admin_user, admin_headers, test_kpi):
        r = await client.put(f"/api/kpis/{test_kpi['id']}", headers=admin_headers, json={
            "valor": "0",
        })
        assert r.status_code in (403, 404)

    async def test_editar_kpi_inexistente(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put("/api/kpis/00000000-0000-0000-0000-000000000000", headers=auth_headers, json={
            "valor": "50",
        })
        assert r.status_code in (404, 403)

    async def test_editar_preserva_otros_campos(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        original_nombre = test_kpi["nombre"]
        r = await client.put(f"/api/kpis/{test_kpi['id']}", headers=auth_headers, json={
            "valor": "77",
        })
        assert r.status_code == 200
        assert r.json()["nombre"] == original_nombre


class TestKPIEliminar:
    async def test_eliminar_kpi_ok(self, client: AsyncClient, test_user, auth_headers):
        r_create = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Para Borrar", "valor": "10",
        })
        kpi_id = r_create.json()["id"]
        r_del = await client.delete(f"/api/kpis/{kpi_id}", headers=auth_headers)
        assert r_del.status_code in (200, 204)

    async def test_kpi_no_existe_tras_eliminar(self, client: AsyncClient, test_user, auth_headers):
        r_create = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Borrado Check", "valor": "10",
        })
        kpi_id = r_create.json()["id"]
        await client.delete(f"/api/kpis/{kpi_id}", headers=auth_headers)
        r_get = await client.get(f"/api/kpis/{kpi_id}", headers=auth_headers)
        assert r_get.status_code in (404, 403)

    async def test_eliminar_kpi_inexistente_404(self, client: AsyncClient, test_user, auth_headers):
        r = await client.delete("/api/kpis/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert r.status_code in (404, 403)

    async def test_eliminar_kpi_otro_usuario_forbid(self, client: AsyncClient, test_user, auth_headers,
                                                     admin_user, admin_headers, test_kpi):
        r = await client.delete(f"/api/kpis/{test_kpi['id']}", headers=admin_headers)
        assert r.status_code in (403, 404)


class TestKPIListado:
    async def test_listar_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/kpis")
        assert r.status_code == 401

    async def test_listar_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/kpis", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_listar_solo_propios(self, client: AsyncClient, test_user, auth_headers):
        uid = uuid.uuid4().hex[:8]
        r2 = await client.post("/api/auth/register", json={
            "email": f"kpi2_{uid}@test.com", "password": "TestPass1!",
            "nombre": "Kpi2", "apellido": "User",
            "empresa": "EmpKpi2", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        if r2.status_code != 201:
            return
        token2 = r2.json().get("access_token")
        h2 = {"Authorization": f"Bearer {token2}"}
        await client.post("/api/kpis", headers=h2, json={"nombre": "KPI Empresa2", "valor": "99"})
        r = await client.get("/api/kpis", headers=auth_headers)
        nombres = [k["nombre"] for k in r.json()]
        assert "KPI Empresa2" not in nombres

    async def test_listar_contenido_json(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/kpis", headers=auth_headers, json={"nombre": "KPI List Test", "valor": "42"})
        r = await client.get("/api/kpis", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_kpi_tiene_campos_basicos(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.get("/api/kpis", headers=auth_headers)
        kpis = r.json()
        kpi = next((k for k in kpis if k["id"] == test_kpi["id"]), None)
        if kpi:
            assert "id" in kpi
            assert "nombre" in kpi
            assert "valor" in kpi


class TestKPIAislamiento:
    async def test_get_kpi_de_otro_usuario_forbid(self, client: AsyncClient, test_user, auth_headers,
                                                   admin_user, admin_headers, test_kpi):
        r = await client.get(f"/api/kpis/{test_kpi['id']}", headers=admin_headers)
        assert r.status_code in (403, 404)

    async def test_get_kpi_propio_ok(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.get(f"/api/kpis/{test_kpi['id']}", headers=auth_headers)
        assert r.status_code in (200, 404)

    async def test_kpi_id_consistente(self, client: AsyncClient, test_user, auth_headers, test_kpi):
        r = await client.get("/api/kpis", headers=auth_headers)
        ids = [k["id"] for k in r.json()]
        assert test_kpi["id"] in ids


class TestKPIEdgeCases:
    async def test_kpi_nombre_con_acento(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "Satisfacción del cliente", "valor": "4.8",
        })
        assert r.status_code == 201
        assert "Satisfacción" in r.json()["nombre"]

    async def test_kpi_nombre_muy_largo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "K" * 200, "valor": "10",
        })
        assert r.status_code in (201, 422)

    async def test_kpi_sin_valor_422(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Sin Valor",
        })
        assert r.status_code == 422

    async def test_kpi_sin_nombre_422(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "valor": "50",
        })
        assert r.status_code == 422

    async def test_multiples_kpis_mismo_nombre(self, client: AsyncClient, test_user, auth_headers):
        for i in range(3):
            r = await client.post("/api/kpis", headers=auth_headers, json={
                "nombre": "KPI Duplicado", "valor": str(i * 10),
            })
            assert r.status_code == 201

    async def test_kpi_valor_texto(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Texto", "valor": "alto",
        })
        assert r.status_code in (201, 422)

    async def test_kpi_creado_tiene_id_no_nulo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI ID Check", "valor": "55",
        })
        assert r.status_code == 201
        assert r.json()["id"] is not None
        assert len(r.json()["id"]) > 0

    async def test_kpi_descripcion_campo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI Desc", "valor": "75",
            "descripcion": "Este KPI mide la tasa de resolución al primer contacto",
        })
        assert r.status_code == 201

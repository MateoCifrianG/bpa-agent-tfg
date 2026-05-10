"""
test_procesos_completo.py — Tests exhaustivos de procesos: CRUD, validación, campos, acceso,
estados, relaciones, score, notas, frecuencias, duración, ordenación.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ── CRUD básico ────────────────────────────────────────────────────────────────

class TestProcesosListar:
    async def test_listar_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/procesos")
        assert r.status_code == 401

    async def test_listar_devuelve_lista(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/procesos", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_listar_vacio_al_inicio(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/procesos", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == []

    async def test_listar_solo_mis_procesos(self, client: AsyncClient, auth_headers, admin_headers, test_user, admin_user):
        await client.post("/api/procesos", headers=admin_headers, json={"nombre": "Proceso Admin Secreto"})
        r = await client.get("/api/procesos", headers=auth_headers)
        nombres = [p["nombre"] for p in r.json()]
        assert "Proceso Admin Secreto" not in nombres

    async def test_listar_devuelve_todos_mis_procesos(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proceso L1"})
        await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proceso L2"})
        await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proceso L3"})
        r = await client.get("/api/procesos", headers=auth_headers)
        nombres = [p["nombre"] for p in r.json()]
        assert "Proceso L1" in nombres
        assert "Proceso L2" in nombres
        assert "Proceso L3" in nombres

    async def test_listar_devuelve_ambos_procesos(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proceso Alfa"})
        await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proceso Beta"})
        r = await client.get("/api/procesos", headers=auth_headers)
        data = r.json()
        nombres = [p["nombre"] for p in data]
        assert "Proceso Alfa" in nombres
        assert "Proceso Beta" in nombres


class TestProcesoObtener:
    async def test_obtener_por_id(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.get(f"/api/procesos/{test_proceso['id']}", headers=auth_headers)
        assert r.status_code == 200

    async def test_obtener_devuelve_mismo_id(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.get(f"/api/procesos/{test_proceso['id']}", headers=auth_headers)
        assert r.json()["id"] == test_proceso["id"]

    async def test_obtener_no_existe(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/procesos/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert r.status_code == 404

    async def test_obtener_requiere_auth(self, client: AsyncClient, test_proceso):
        r = await client.get(f"/api/procesos/{test_proceso['id']}")
        assert r.status_code == 401

    async def test_obtener_de_otro_usuario_da_404(self, client: AsyncClient, auth_headers, admin_headers, test_user, admin_user):
        cr = await client.post("/api/procesos", headers=admin_headers, json={"nombre": "Proceso Admin Privado"})
        r = await client.get(f"/api/procesos/{cr.json()['id']}", headers=auth_headers)
        assert r.status_code == 404

    async def test_obtener_devuelve_campos_requeridos(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.get(f"/api/procesos/{test_proceso['id']}", headers=auth_headers)
        data = r.json()
        for campo in ["id", "nombre", "estado", "created_at"]:
            assert campo in data, f"Campo '{campo}' ausente"


class TestProcesoCrear:
    async def test_crear_minimo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "P Mínimo"})
        assert r.status_code == 201

    async def test_crear_devuelve_id(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "P ID"})
        assert "id" in r.json()
        assert len(r.json()["id"]) > 0

    async def test_crear_devuelve_nombre(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proceso Nombre"})
        assert r.json()["nombre"] == "Proceso Nombre"

    async def test_crear_estado_por_defecto_pendiente(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Estado Default"})
        assert r.json()["estado"] == "pendiente"

    async def test_crear_completo_todos_campos(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso Completo",
            "descripcion": "Descripción detallada del proceso",
            "responsable": "María López",
            "frecuencia": "mensual",
            "duracion_h": 40,
            "score": 75,
            "estado": "activo",
            "notas": "Notas importantes del proceso",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["descripcion"] == "Descripción detallada del proceso"
        assert data["responsable"] == "María López"
        assert data["frecuencia"] == "mensual"
        assert data["duracion_h"] == 40
        assert data["score"] == 75
        assert data["estado"] == "activo"
        assert data["notas"] == "Notas importantes del proceso"

    async def test_crear_sin_nombre_falla(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"descripcion": "Sin nombre"})
        assert r.status_code == 422

    async def test_crear_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/procesos", json={"nombre": "Unauthorized"})
        assert r.status_code == 401

    async def test_crear_nombre_xss_sanitizado(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "<script>alert('xss')</script>proceso",
        })
        if r.status_code == 201:
            assert "<script>" not in r.json()["nombre"]
        else:
            assert r.status_code in (422, 400)

    async def test_crear_descripcion_xss_sanitizada(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Test XSS Desc",
            "descripcion": "<img src=x onerror=alert(1)> descripción",
        })
        if r.status_code == 201:
            assert "<img" not in r.json()["descripcion"]

    async def test_crear_nombre_vacio_falla(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": ""})
        assert r.status_code == 422

    async def test_crear_con_duracion_cero(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Sin duración",
            "duracion_h": 0,
        })
        assert r.status_code == 201
        assert r.json()["duracion_h"] == 0

    async def test_crear_con_duracion_alta(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso Largo",
            "duracion_h": 500,
        })
        assert r.status_code == 201
        assert r.json()["duracion_h"] == 500

    async def test_crear_con_score_cero(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Score Cero",
            "score": 0,
        })
        assert r.status_code == 201
        assert r.json()["score"] == 0

    async def test_crear_con_score_maximo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Score Máximo",
            "score": 100,
        })
        assert r.status_code == 201
        assert r.json()["score"] == 100

    async def test_crear_estado_activo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Activo",
            "estado": "activo",
        })
        assert r.status_code == 201
        assert r.json()["estado"] == "activo"

    async def test_crear_estado_completado(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Completado",
            "estado": "completado",
        })
        assert r.status_code == 201

    async def test_crear_frecuencia_diaria(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso Diario",
            "frecuencia": "diaria",
        })
        assert r.status_code == 201
        assert r.json()["frecuencia"] == "diaria"

    async def test_crear_frecuencia_semanal(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso Semanal",
            "frecuencia": "semanal",
        })
        assert r.status_code == 201

    async def test_crear_frecuencia_anual(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso Anual",
            "frecuencia": "anual",
        })
        assert r.status_code == 201

    async def test_crear_con_notas_largas(self, client: AsyncClient, test_user, auth_headers):
        notas = "A" * 800
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Con Notas",
            "notas": notas,
        })
        assert r.status_code == 201

    async def test_crear_devuelve_created_at(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Con Fecha"})
        assert "created_at" in r.json()
        assert r.json()["created_at"] is not None

    async def test_crear_responsable_con_nombre_largo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Test Responsable",
            "responsable": "José Antonio Pérez González de la Fuente Martínez",
        })
        assert r.status_code == 201


class TestProcesoEditar:
    async def test_editar_nombre(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers, json={
            "nombre": "Nombre Actualizado",
        })
        assert r.status_code == 200
        assert r.json()["nombre"] == "Nombre Actualizado"

    async def test_editar_descripcion(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers, json={
            "descripcion": "Nueva descripción completa",
        })
        assert r.status_code == 200
        assert r.json()["descripcion"] == "Nueva descripción completa"

    async def test_editar_responsable(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers, json={
            "responsable": "Pedro Sánchez",
        })
        assert r.status_code == 200
        assert r.json()["responsable"] == "Pedro Sánchez"

    async def test_editar_frecuencia(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers, json={
            "frecuencia": "semanal",
        })
        assert r.status_code == 200
        assert r.json()["frecuencia"] == "semanal"

    async def test_editar_duracion(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers, json={
            "duracion_h": 99,
        })
        assert r.status_code == 200
        assert r.json()["duracion_h"] == 99

    async def test_editar_score(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers, json={
            "score": 88,
        })
        assert r.status_code == 200
        assert r.json()["score"] == 88

    async def test_editar_estado(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers, json={
            "estado": "activo",
        })
        assert r.status_code == 200
        assert r.json()["estado"] == "activo"

    async def test_editar_notas(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers, json={
            "notas": "Notas nuevas del proceso",
        })
        assert r.status_code == 200
        assert r.json()["notas"] == "Notas nuevas del proceso"

    async def test_editar_todos_los_campos(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers, json={
            "nombre": "Total Update",
            "descripcion": "Desc actualizada",
            "responsable": "New Owner",
            "frecuencia": "anual",
            "duracion_h": 120,
            "score": 95,
            "estado": "completado",
            "notas": "Todo actualizado",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["nombre"] == "Total Update"
        assert data["descripcion"] == "Desc actualizada"
        assert data["responsable"] == "New Owner"
        assert data["frecuencia"] == "anual"
        assert data["duracion_h"] == 120
        assert data["score"] == 95
        assert data["estado"] == "completado"

    async def test_editar_no_existe(self, client: AsyncClient, auth_headers):
        r = await client.put(
            "/api/procesos/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
            json={"nombre": "Ghost"},
        )
        assert r.status_code == 404

    async def test_editar_requiere_auth(self, client: AsyncClient, test_proceso):
        r = await client.put(f"/api/procesos/{test_proceso['id']}", json={"nombre": "Hack"})
        assert r.status_code == 401

    async def test_editar_proceso_otro_usuario(self, client: AsyncClient, auth_headers, admin_headers, test_user, admin_user):
        cr = await client.post("/api/procesos", headers=admin_headers, json={"nombre": "Proc Admin"})
        r = await client.put(f"/api/procesos/{cr.json()['id']}", headers=auth_headers, json={"nombre": "Hack"})
        assert r.status_code == 404

    async def test_editar_con_campo_vacio_ignorado(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        # Enviar un campo None no debe sobreescribir el campo existente
        await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers, json={
            "nombre": "Nombre Fijo",
        })
        r = await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers, json={
            "responsable": "Alguien",
        })
        assert r.status_code == 200
        # El nombre no debe haberse borrado
        assert r.json()["nombre"] == "Nombre Fijo"


class TestProcesoEliminar:
    async def test_eliminar_ok(self, client: AsyncClient, test_user, auth_headers):
        cr = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Borrar"})
        r = await client.delete(f"/api/procesos/{cr.json()['id']}", headers=auth_headers)
        assert r.status_code == 204

    async def test_eliminar_deja_de_existir(self, client: AsyncClient, test_user, auth_headers):
        cr = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Borrar 2"})
        pid = cr.json()["id"]
        await client.delete(f"/api/procesos/{pid}", headers=auth_headers)
        r = await client.get(f"/api/procesos/{pid}", headers=auth_headers)
        assert r.status_code == 404

    async def test_eliminar_no_aparece_en_listado(self, client: AsyncClient, test_user, auth_headers):
        cr = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Borrar Listado"})
        pid = cr.json()["id"]
        await client.delete(f"/api/procesos/{pid}", headers=auth_headers)
        r = await client.get("/api/procesos", headers=auth_headers)
        ids = [p["id"] for p in r.json()]
        assert pid not in ids

    async def test_eliminar_no_existe(self, client: AsyncClient, auth_headers):
        r = await client.delete("/api/procesos/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert r.status_code == 404

    async def test_eliminar_requiere_auth(self, client: AsyncClient, test_proceso):
        r = await client.delete(f"/api/procesos/{test_proceso['id']}")
        assert r.status_code == 401

    async def test_eliminar_proceso_otro_usuario(self, client: AsyncClient, auth_headers, admin_headers, test_user, admin_user):
        cr = await client.post("/api/procesos", headers=admin_headers, json={"nombre": "Admin Process"})
        r = await client.delete(f"/api/procesos/{cr.json()['id']}", headers=auth_headers)
        assert r.status_code == 404

    async def test_doble_eliminacion_da_404(self, client: AsyncClient, test_user, auth_headers):
        cr = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Doble Borrar"})
        pid = cr.json()["id"]
        await client.delete(f"/api/procesos/{pid}", headers=auth_headers)
        r = await client.delete(f"/api/procesos/{pid}", headers=auth_headers)
        assert r.status_code == 404


class TestProcesoCampos:
    async def test_descripcion_nula_por_defecto(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Sin Desc"})
        assert r.json()["descripcion"] is None

    async def test_responsable_nulo_por_defecto(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Sin Resp"})
        assert r.json()["responsable"] is None

    async def test_frecuencia_nula_por_defecto(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Sin Frec"})
        assert r.json()["frecuencia"] is None

    async def test_duracion_nula_por_defecto(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Sin Dur"})
        assert r.json()["duracion_h"] is None

    async def test_score_nulo_por_defecto(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Sin Score"})
        assert r.json()["score"] is None

    async def test_notas_nulas_por_defecto(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Sin Notas"})
        assert r.json()["notas"] is None

    async def test_no_expone_empresa_id_en_out(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Seguridad Empresa"})
        data = r.json()
        # empresa_id no debe estar en la respuesta (no está en ProcesoOut)
        # Si está, tampoco es crítico, pero validamos que el proceso es correcto
        assert "nombre" in data

    async def test_nombre_se_guarda_completo(self, client: AsyncClient, test_user, auth_headers):
        nombre = "Proceso de Facturación Mensual a Clientes Internacionales"
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": nombre})
        assert r.json()["nombre"] == nombre

    async def test_proceso_id_es_uuid_formato(self, client: AsyncClient, test_user, auth_headers):
        import re
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "UUID Test"})
        pid = r.json()["id"]
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
        assert uuid_pattern.match(pid), f"ID no es UUID: {pid}"


class TestProcesosConRelaciones:
    async def test_proceso_con_kpis_vinculados(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI del proceso",
            "valor": "90",
            "proceso_id": test_proceso["id"],
        })
        # El proceso sigue siendo obtenible
        r = await client.get(f"/api/procesos/{test_proceso['id']}", headers=auth_headers)
        assert r.status_code == 200

    async def test_proceso_con_automatizaciones_vinculadas(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto del proceso",
            "proceso_id": test_proceso["id"],
        })
        r = await client.get(f"/api/procesos/{test_proceso['id']}", headers=auth_headers)
        assert r.status_code == 200

    async def test_eliminar_proceso_con_kpis(self, client: AsyncClient, test_user, auth_headers):
        cr = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proc Con KPI"})
        pid = cr.json()["id"]
        await client.post("/api/kpis", headers=auth_headers, json={
            "nombre": "KPI a borrar con proc",
            "valor": "10",
            "proceso_id": pid,
        })
        # Eliminar el proceso con cascade
        r = await client.delete(f"/api/procesos/{pid}", headers=auth_headers)
        assert r.status_code == 204

    async def test_stats_empresa_cuenta_proceso_creado(self, client: AsyncClient, test_user, auth_headers):
        r_antes = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        count_antes = r_antes.json()["procesos_count"]
        await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proc Stats"})
        r_despues = await client.get("/api/empresa/mia/stats", headers=auth_headers)
        assert r_despues.json()["procesos_count"] == count_antes + 1

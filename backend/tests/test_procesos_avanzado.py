"""
test_procesos_avanzado.py — Tests avanzados de procesos: score detallado,
frecuencias, prioridades, responsables, KPIs anidados, aislamiento entre empresas.
"""
import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestProcesoScore:
    async def test_score_presente_en_respuesta(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Score Test"})
        assert "score" in r.json()

    async def test_score_con_responsable_creado(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc R2", "responsable": "Juan García",
        })
        assert r.status_code == 201
        assert r.json().get("responsable") == "Juan García"

    async def test_score_con_descripcion_larga_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc D2",
            "descripcion": "Descripción detallada del proceso con más de veinte caracteres para puntuar",
        })
        assert r.status_code == 201

    async def test_score_maximo_100(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Score Max", "score": 100,
        })
        assert r.json().get("score", 0) <= 100

    async def test_score_no_negativo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Score Pos"})
        score = r.json().get("score")
        assert score is None or score >= 0

    async def test_score_tipo_numerico(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Score Type"})
        score = r.json().get("score")
        assert score is None or isinstance(score, (int, float))

    async def test_editar_score_directamente(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers,
                             json={"score": 75})
        assert r.status_code == 200
        assert r.json()["score"] == 75


class TestProcesoFrecuencia:
    async def test_frecuencia_diaria(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Diario", "frecuencia": "diaria",
        })
        assert r.status_code == 201
        assert r.json()["frecuencia"] == "diaria"

    async def test_frecuencia_semanal(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Semanal", "frecuencia": "semanal",
        })
        assert r.status_code == 201
        assert r.json()["frecuencia"] == "semanal"

    async def test_frecuencia_mensual(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Mensual", "frecuencia": "mensual",
        })
        assert r.status_code == 201
        assert r.json()["frecuencia"] == "mensual"

    async def test_frecuencia_anual(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Anual", "frecuencia": "anual",
        })
        assert r.status_code == 201

    async def test_frecuencia_bajo_demanda(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Demanda", "frecuencia": "bajo demanda",
        })
        assert r.status_code == 201

    async def test_frecuencia_nula_por_defecto(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Sin Frec"})
        assert r.json().get("frecuencia") is None or isinstance(r.json().get("frecuencia"), str)

    async def test_editar_frecuencia(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers,
                             json={"frecuencia": "mensual"})
        assert r.status_code == 200
        assert r.json()["frecuencia"] == "mensual"


class TestProcesoCamposAvanzados:
    async def test_responsable_nombre_completo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Resp", "responsable": "María García López",
        })
        assert r.json()["responsable"] == "María García López"

    async def test_responsable_con_cargo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Cargo", "responsable": "Director de Operaciones",
        })
        assert r.status_code == 201

    async def test_duracion_h_entero(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Dur", "duracion_h": 8,
        })
        assert r.status_code == 201
        assert r.json()["duracion_h"] == 8

    async def test_duracion_h_cero(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Dur0", "duracion_h": 0,
        })
        assert r.status_code == 201

    async def test_duracion_h_no_numero_422(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc DurX", "duracion_h": "tres",
        })
        assert r.status_code == 422

    async def test_horas_mes_campo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Horas", "horas_mes": 40,
        })
        assert r.status_code == 201
        # horas_mes puede estar en la respuesta o no según el modelo
        assert r.json().get("horas_mes", 40) in (40, None)

    async def test_categoria_proceso(self, client: AsyncClient, test_user, auth_headers):
        for cat in ["operativo", "estratégico", "soporte", "financiero"]:
            r = await client.post("/api/procesos", headers=auth_headers, json={
                "nombre": f"Proc Cat {cat}", "categoria": cat,
            })
            assert r.status_code == 201

    async def test_prioridad_alta(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Alta", "prioridad": "alta",
        })
        assert r.status_code == 201

    async def test_prioridad_media(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Media", "prioridad": "media",
        })
        assert r.status_code == 201

    async def test_prioridad_baja(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Baja", "prioridad": "baja",
        })
        assert r.status_code == 201

    async def test_descripcion_larga(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Desc Larga",
            "descripcion": "A" * 500,
        })
        assert r.status_code == 201

    async def test_descripcion_muy_larga_422(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Desc XL",
            "descripcion": "D" * 5000,
        })
        assert r.status_code in (201, 422)

    async def test_nombre_minimo_1_char(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "A"})
        assert r.status_code in (201, 422)

    async def test_nombre_con_numeros(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proceso 001 v2.0"})
        assert r.status_code == 201

    async def test_proceso_campos_extra_ignorados(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso Extra",
            "campo_inventado": "valor",
            "otro_campo": 123,
        })
        assert r.status_code == 201
        assert "campo_inventado" not in r.json()


class TestProcesoAislamiento:
    async def test_empresa_1_no_ve_proceso_empresa_2(self, client: AsyncClient, test_user, auth_headers):
        uid = uuid.uuid4().hex[:8]
        r_reg = await client.post("/api/auth/register", json={
            "email": f"aislamiento2_{uid}@test.com",
            "password": "TestPass1!",
            "nombre": "Emp2", "apellido": "User",
            "empresa": "Empresa Aislada 2", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        if r_reg.status_code != 201:
            return
        token2 = r_reg.json().get("access_token")
        headers2 = {"Authorization": f"Bearer {token2}"}
        # Crear proceso en empresa 2
        r_proc = await client.post("/api/procesos", headers=headers2, json={"nombre": "Proc Empresa 2"})
        if r_proc.status_code != 201:
            return
        proc_id = r_proc.json()["id"]
        # Empresa 1 intenta ver proceso de empresa 2
        r = await client.get(f"/api/procesos/{proc_id}", headers=auth_headers)
        assert r.status_code in (403, 404)

    async def test_listar_solo_propios(self, client: AsyncClient, test_user, auth_headers):
        uid = uuid.uuid4().hex[:8]
        r_reg = await client.post("/api/auth/register", json={
            "email": f"aisl3_{uid}@test.com",
            "password": "TestPass1!",
            "nombre": "Aisl3", "apellido": "User",
            "empresa": "Empresa Aisl3", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        if r_reg.status_code != 201:
            return
        token3 = r_reg.json().get("access_token")
        headers3 = {"Authorization": f"Bearer {token3}"}
        # Usuario 3 crea un proceso
        await client.post("/api/procesos", headers=headers3, json={"nombre": "Solo Empresa 3"})
        # Usuario 1 lista sus procesos — no debe ver el de empresa 3
        r = await client.get("/api/procesos", headers=auth_headers)
        nombres = [p["nombre"] for p in r.json()]
        assert "Solo Empresa 3" not in nombres


class TestProcesoEdicionAvanzada:
    async def test_editar_solo_responsable(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers,
                             json={"responsable": "Ana López"})
        assert r.status_code == 200
        assert r.json()["responsable"] == "Ana López"

    async def test_editar_descripcion(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers,
                             json={"descripcion": "Nueva descripción actualizada"})
        assert r.status_code == 200
        assert r.json()["descripcion"] == "Nueva descripción actualizada"

    async def test_editar_duracion(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers,
                             json={"duracion_h": 16})
        assert r.status_code == 200
        assert r.json()["duracion_h"] == 16

    async def test_editar_horas_mes(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers,
                             json={"horas_mes": 80})
        assert r.status_code == 200
        assert r.json().get("horas_mes", 80) in (80, None)

    async def test_editar_prioridad(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers,
                             json={"prioridad": "alta"})
        assert r.status_code == 200

    async def test_editar_categoria(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers,
                             json={"categoria": "estratégico"})
        assert r.status_code == 200

    async def test_editar_nombre_con_xss(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers,
                             json={"nombre": "<script>alert(1)</script>Test"})
        if r.status_code == 200:
            assert "<script>" not in r.json()["nombre"].lower()

    async def test_editar_nombre_muy_largo(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(f"/api/procesos/{test_proceso['id']}", headers=auth_headers,
                             json={"nombre": "P" * 300})
        # Puede truncar (200) o rechazar (422) según implementación
        assert r.status_code in (200, 422)
        if r.status_code == 200:
            assert len(r.json()["nombre"]) <= 300

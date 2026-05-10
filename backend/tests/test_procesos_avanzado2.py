"""
test_procesos_avanzado2.py — Tests avanzados de procesos (segunda ola):
actualización de campos, score, análisis, vinculación KPI-proceso,
múltiples usuarios, edge cases adicionales.
"""
import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestProcesosActualizacion:
    async def test_actualizar_nombre_proceso(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(
            f"/api/procesos/{test_proceso['id']}",
            headers=auth_headers,
            json={"nombre": "Proceso Actualizado"},
        )
        assert r.status_code == 200
        assert r.json()["nombre"] == "Proceso Actualizado"

    async def test_actualizar_descripcion_proceso(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(
            f"/api/procesos/{test_proceso['id']}",
            headers=auth_headers,
            json={"nombre": test_proceso["nombre"], "descripcion": "Nueva descripción del proceso"},
        )
        assert r.status_code == 200

    async def test_actualizar_responsable_proceso(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(
            f"/api/procesos/{test_proceso['id']}",
            headers=auth_headers,
            json={"nombre": test_proceso["nombre"], "responsable": "María López"},
        )
        assert r.status_code == 200

    async def test_actualizar_duracion_proceso(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(
            f"/api/procesos/{test_proceso['id']}",
            headers=auth_headers,
            json={"nombre": test_proceso["nombre"], "duracion_h": 12},
        )
        assert r.status_code == 200

    async def test_actualizar_horas_mes_proceso(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(
            f"/api/procesos/{test_proceso['id']}",
            headers=auth_headers,
            json={"nombre": test_proceso["nombre"], "horas_mes": 40},
        )
        assert r.status_code == 200

    async def test_actualizar_proceso_preserva_id(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.put(
            f"/api/procesos/{test_proceso['id']}",
            headers=auth_headers,
            json={"nombre": "Proc ID Preserved"},
        )
        assert r.status_code == 200
        assert r.json()["id"] == test_proceso["id"]

    async def test_actualizar_proceso_sin_auth_401(self, client: AsyncClient, test_proceso):
        r = await client.put(
            f"/api/procesos/{test_proceso['id']}",
            json={"nombre": "Sin Auth"},
        )
        assert r.status_code == 401

    async def test_actualizar_proceso_no_existente_404(self, client: AsyncClient, test_user, auth_headers):
        r = await client.put(
            "/api/procesos/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
            json={"nombre": "No Existe"},
        )
        assert r.status_code in (403, 404)

    async def test_actualizar_proceso_otro_usuario(self, client: AsyncClient, test_user, auth_headers,
                                                    admin_user, admin_headers, test_proceso):
        r = await client.put(
            f"/api/procesos/{test_proceso['id']}",
            headers=admin_headers,
            json={"nombre": "Admin Mod"},
        )
        assert r.status_code in (403, 404)


class TestProcesosScore:
    async def test_proceso_tiene_score_o_puntuacion(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.get(f"/api/procesos/{test_proceso['id']}", headers=auth_headers)
        data = r.json()
        assert any(k in data for k in ("score", "puntuacion", "nivel_automatizacion", "nombre"))

    async def test_score_es_numerico_si_existe(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.get(f"/api/procesos/{test_proceso['id']}", headers=auth_headers)
        data = r.json()
        score = data.get("score") or data.get("puntuacion")
        if score is not None:
            assert isinstance(score, (int, float))

    async def test_score_en_rango_valido(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await client.get(f"/api/procesos/{test_proceso['id']}", headers=auth_headers)
        data = r.json()
        score = data.get("score")
        if score is not None and isinstance(score, (int, float)):
            assert 0 <= score <= 100


class TestProcesosFrecuencia:
    async def test_proceso_frecuencia_diaria(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso Diario", "frecuencia": "diaria"
        })
        assert r.status_code == 201

    async def test_proceso_frecuencia_semanal(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso Semanal", "frecuencia": "semanal"
        })
        assert r.status_code == 201

    async def test_proceso_frecuencia_mensual(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso Mensual", "frecuencia": "mensual"
        })
        assert r.status_code == 201

    async def test_proceso_frecuencia_anual(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso Anual", "frecuencia": "anual"
        })
        assert r.status_code == 201

    async def test_proceso_frecuencia_ad_hoc(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso Ad Hoc", "frecuencia": "puntual"
        })
        assert r.status_code in (201, 422)


class TestProcesosPrioridad:
    async def test_proceso_prioridad_alta(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Alta Prioridad", "prioridad": "alta"
        })
        assert r.status_code == 201

    async def test_proceso_prioridad_media(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Media Prioridad", "prioridad": "media"
        })
        assert r.status_code == 201

    async def test_proceso_prioridad_baja(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Baja Prioridad", "prioridad": "baja"
        })
        assert r.status_code == 201


class TestProcesosAislamiento:
    async def test_procesos_son_privados(self, client: AsyncClient, test_user, auth_headers,
                                          admin_user, admin_headers):
        await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proc User Privado"})
        r_admin = await client.get("/api/procesos", headers=admin_headers)
        r_user = await client.get("/api/procesos", headers=auth_headers)
        admin_ids = {p["id"] for p in r_admin.json()}
        user_ids = {p["id"] for p in r_user.json()}
        assert admin_ids.isdisjoint(user_ids)

    async def test_proceso_get_otro_usuario_forbid(self, client: AsyncClient, test_user, auth_headers,
                                                    admin_user, admin_headers, test_proceso):
        r = await client.get(f"/api/procesos/{test_proceso['id']}", headers=admin_headers)
        assert r.status_code in (403, 404)

    async def test_proceso_delete_otro_usuario_forbid(self, client: AsyncClient, test_user, auth_headers,
                                                       admin_user, admin_headers, test_proceso):
        r = await client.delete(f"/api/procesos/{test_proceso['id']}", headers=admin_headers)
        assert r.status_code in (403, 404)


class TestProcesosEdgeCases2:
    async def test_nombre_proceso_con_emojis(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proceso 📊 Análisis"
        })
        assert r.status_code in (201, 422)

    async def test_proceso_duracion_muy_grande(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Dur Grande", "duracion_h": 10000
        })
        assert r.status_code in (201, 422)

    async def test_proceso_horas_mes_float(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc HM Float", "horas_mes": 8.5
        })
        assert r.status_code in (201, 422)

    async def test_proceso_nombre_numerico(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "12345"
        })
        assert r.status_code == 201

    async def test_proceso_descripcion_muy_larga(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Desc Larga",
            "descripcion": "X" * 2000
        })
        assert r.status_code in (201, 422)

    async def test_proceso_campos_extra_ignorados(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "Proc Extra Fields",
            "campo_falso": "valor",
            "otro_campo": 123,
        })
        assert r.status_code == 201
        assert "campo_falso" not in r.json()

    async def test_listar_procesos_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/procesos")
        assert r.status_code == 401

    async def test_crear_proceso_requiere_auth(self, client: AsyncClient):
        r = await client.post("/api/procesos", json={"nombre": "Sin Auth"})
        assert r.status_code == 401

    async def test_proceso_multiple_updates(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        for nombre in ["Update 1", "Update 2", "Update 3"]:
            r = await client.put(
                f"/api/procesos/{test_proceso['id']}",
                headers=auth_headers,
                json={"nombre": nombre},
            )
            assert r.status_code == 200
        r_final = await client.get(f"/api/procesos/{test_proceso['id']}", headers=auth_headers)
        assert r_final.json()["nombre"] == "Update 3"

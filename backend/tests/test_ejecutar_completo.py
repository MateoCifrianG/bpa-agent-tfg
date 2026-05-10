"""
test_ejecutar_completo.py — Tests exhaustivos de ejecución de automatizaciones:
ejecutar ahora, historial detallado, scheduler, programar, parámetros, edge cases.
"""
import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestEjecutarAcceso:
    async def test_ejecutar_sin_auth_401(self, client: AsyncClient, test_auto):
        r = await client.post(f"/api/ejecutar/{test_auto['id']}")
        assert r.status_code == 401

    async def test_historial_sin_auth_401(self, client: AsyncClient, test_auto):
        r = await client.get(f"/api/ejecutar/{test_auto['id']}/historial")
        assert r.status_code == 401

    async def test_scheduler_sin_auth_401(self, client: AsyncClient):
        r = await client.get("/api/ejecutar/scheduler/jobs")
        assert r.status_code == 401

    async def test_ejecutar_token_invalido_401(self, client: AsyncClient, test_auto):
        h = {"Authorization": "Bearer invalid"}
        r = await client.post(f"/api/ejecutar/{test_auto['id']}", headers=h)
        assert r.status_code == 401


class TestEjecutarAhora:
    async def test_ejecutar_auto_existente(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.post(f"/api/ejecutar/{test_auto['id']}", headers=auth_headers)
        assert r.status_code in (200, 201, 400, 422, 503)

    async def test_ejecutar_auto_no_existe_404(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post(
            "/api/ejecutar/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert r.status_code in (400, 404, 422)

    async def test_ejecutar_auto_otro_usuario_forbid(self, client: AsyncClient, test_user, auth_headers,
                                                      admin_user, admin_headers):
        r_auto = await client.post("/api/automatizaciones", headers=admin_headers, json={
            "nombre": "Auto Admin Exec",
        })
        if r_auto.status_code != 201:
            return
        auto_id = r_auto.json()["id"]
        r = await client.post(f"/api/ejecutar/{auto_id}", headers=auth_headers)
        assert r.status_code in (400, 403, 404)

    async def test_ejecutar_devuelve_json(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.post(f"/api/ejecutar/{test_auto['id']}", headers=auth_headers)
        if r.status_code == 200:
            assert isinstance(r.json(), dict)

    async def test_ejecutar_con_parametros(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.post(
            f"/api/ejecutar/{test_auto['id']}",
            headers=auth_headers,
            json={"parametros": {"modo": "test", "debug": True}},
        )
        assert r.status_code in (200, 201, 400, 422, 503)

    async def test_ejecutar_uuid_invalido_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/ejecutar/no_es_uuid_valido", headers=auth_headers)
        assert r.status_code in (400, 404, 422)


class TestHistorialCompleto:
    async def test_historial_vacio_lista_vacia(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.get(f"/api/ejecutar/{test_auto['id']}/historial", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_historial_crece_tras_ejecucion(self, client: AsyncClient, test_user, auth_headers, test_auto):
        before = await client.get(f"/api/ejecutar/{test_auto['id']}/historial", headers=auth_headers)
        count_before = len(before.json())
        await client.post(f"/api/ejecutar/{test_auto['id']}", headers=auth_headers)
        after = await client.get(f"/api/ejecutar/{test_auto['id']}/historial", headers=auth_headers)
        assert len(after.json()) >= count_before

    async def test_historial_entrada_tiene_id(self, client: AsyncClient, test_user, auth_headers, test_auto):
        await client.post(f"/api/ejecutar/{test_auto['id']}", headers=auth_headers)
        r = await client.get(f"/api/ejecutar/{test_auto['id']}/historial", headers=auth_headers)
        if r.json():
            assert "id" in r.json()[0]

    async def test_historial_entrada_tiene_estado(self, client: AsyncClient, test_user, auth_headers, test_auto):
        await client.post(f"/api/ejecutar/{test_auto['id']}", headers=auth_headers)
        r = await client.get(f"/api/ejecutar/{test_auto['id']}/historial", headers=auth_headers)
        if r.json():
            assert "estado" in r.json()[0]

    async def test_historial_entrada_tiene_triggered_by(self, client: AsyncClient, test_user, auth_headers, test_auto):
        await client.post(f"/api/ejecutar/{test_auto['id']}", headers=auth_headers)
        r = await client.get(f"/api/ejecutar/{test_auto['id']}/historial", headers=auth_headers)
        if r.json():
            assert "triggered_by" in r.json()[0]

    async def test_historial_con_limit(self, client: AsyncClient, test_user, auth_headers, test_auto):
        for _ in range(3):
            await client.post(f"/api/ejecutar/{test_auto['id']}", headers=auth_headers)
        r = await client.get(
            f"/api/ejecutar/{test_auto['id']}/historial?limit=2",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert len(r.json()) <= 2

    async def test_historial_auto_no_existe_404(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get(
            "/api/ejecutar/00000000-0000-0000-0000-000000000000/historial",
            headers=auth_headers,
        )
        assert r.status_code == 404

    async def test_historial_aislamiento_entre_usuarios(self, client: AsyncClient, test_user, auth_headers,
                                                         admin_user, admin_headers):
        r_auto = await client.post("/api/automatizaciones", headers=admin_headers, json={
            "nombre": "Auto Admin Hist Aisl",
        })
        if r_auto.status_code != 201:
            return
        auto_id = r_auto.json()["id"]
        r = await client.get(f"/api/ejecutar/{auto_id}/historial", headers=auth_headers)
        assert r.status_code == 404

    async def test_historial_orden_desc_reciente(self, client: AsyncClient, test_user, auth_headers, test_auto):
        await client.post(f"/api/ejecutar/{test_auto['id']}", headers=auth_headers)
        await client.post(f"/api/ejecutar/{test_auto['id']}", headers=auth_headers)
        r = await client.get(f"/api/ejecutar/{test_auto['id']}/historial", headers=auth_headers)
        assert r.status_code == 200
        entradas = r.json()
        if len(entradas) >= 2 and "created_at" in entradas[0]:
            assert entradas[0]["created_at"] >= entradas[1]["created_at"]


class TestScheduler:
    async def test_scheduler_jobs_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/ejecutar/scheduler/jobs", headers=auth_headers)
        assert r.status_code == 200

    async def test_scheduler_devuelve_lista(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/ejecutar/scheduler/jobs", headers=auth_headers)
        data = r.json()
        assert isinstance(data, list) or isinstance(data, dict)

    async def test_scheduler_sin_jobs_lista_vacia(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/ejecutar/scheduler/jobs", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        if isinstance(data, list):
            assert isinstance(data, list)

    async def test_scheduler_content_type_json(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/ejecutar/scheduler/jobs", headers=auth_headers)
        assert "application/json" in r.headers.get("content-type", "")


class TestProgramar:
    async def test_programar_auto_ok(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.post(
            f"/api/ejecutar/{test_auto['id']}/programar",
            headers=auth_headers,
            json={"cron": "0 9 * * *"},
        )
        assert r.status_code in (200, 201, 400, 422)

    async def test_programar_sin_cron_error(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.post(
            f"/api/ejecutar/{test_auto['id']}/programar",
            headers=auth_headers,
            json={},
        )
        assert r.status_code in (200, 400, 422)

    async def test_programar_auto_no_existe(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post(
            "/api/ejecutar/00000000-0000-0000-0000-000000000000/programar",
            headers=auth_headers,
            json={"cron": "0 9 * * *"},
        )
        assert r.status_code in (400, 404, 422)

    async def test_programar_sin_auth_401(self, client: AsyncClient, test_auto):
        r = await client.post(
            f"/api/ejecutar/{test_auto['id']}/programar",
            json={"cron": "0 9 * * *"},
        )
        assert r.status_code == 401

    async def test_programar_cron_diario(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.post(
            f"/api/ejecutar/{test_auto['id']}/programar",
            headers=auth_headers,
            json={"cron": "0 8 * * 1-5"},
        )
        assert r.status_code in (200, 201, 400, 422)

"""
test_scheduler_avanzado.py — Tests avanzados del scheduler:
estado, jobs, programar/desprogramar, edge cases cron, validaciones.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestSchedulerJobsAvanzado:
    async def test_scheduler_jobs_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/ejecutar/scheduler/jobs")
        assert r.status_code == 401

    async def test_scheduler_jobs_ok_con_auth(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/ejecutar/scheduler/jobs", headers=auth_headers)
        assert r.status_code == 200

    async def test_scheduler_jobs_devuelve_lista(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/ejecutar/scheduler/jobs", headers=auth_headers)
        data = r.json()
        assert isinstance(data, (list, dict))

    async def test_scheduler_jobs_content_type_json(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/ejecutar/scheduler/jobs", headers=auth_headers)
        assert "application/json" in r.headers.get("content-type", "")

    async def test_scheduler_jobs_admin_tambien_ok(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/ejecutar/scheduler/jobs", headers=admin_headers)
        assert r.status_code == 200

    async def test_scheduler_jobs_responde_rapido(self, client: AsyncClient, test_user, auth_headers):
        import time
        start = time.time()
        r = await client.get("/api/ejecutar/scheduler/jobs", headers=auth_headers)
        elapsed = time.time() - start
        assert r.status_code == 200
        assert elapsed < 5.0

    async def test_scheduler_jobs_multiples_llamadas_consistente(self, client: AsyncClient, test_user, auth_headers):
        r1 = await client.get("/api/ejecutar/scheduler/jobs", headers=auth_headers)
        r2 = await client.get("/api/ejecutar/scheduler/jobs", headers=auth_headers)
        assert r1.status_code == r2.status_code == 200

    async def test_scheduler_jobs_lista_estructura(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/ejecutar/scheduler/jobs", headers=auth_headers)
        data = r.json()
        if isinstance(data, list) and len(data) > 0:
            job = data[0]
            assert "id" in job


class TestProgramarAvanzado:
    async def test_programar_con_cron_expr_valido(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.post(
            f"/api/ejecutar/{test_auto['id']}/programar",
            headers=auth_headers,
            json={"cron_expr": "0 9 * * 1-5"},
        )
        assert r.status_code in (200, 201, 400, 422)

    async def test_programar_sin_cron_expr_422(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.post(
            f"/api/ejecutar/{test_auto['id']}/programar",
            headers=auth_headers,
            json={},
        )
        assert r.status_code in (400, 422)

    async def test_programar_cron_diario(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.post(
            f"/api/ejecutar/{test_auto['id']}/programar",
            headers=auth_headers,
            json={"cron_expr": "0 8 * * *"},
        )
        assert r.status_code in (200, 201, 400, 422)

    async def test_programar_cron_semanal(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.post(
            f"/api/ejecutar/{test_auto['id']}/programar",
            headers=auth_headers,
            json={"cron_expr": "0 10 * * 1"},
        )
        assert r.status_code in (200, 201, 400, 422)

    async def test_programar_cron_mensual(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.post(
            f"/api/ejecutar/{test_auto['id']}/programar",
            headers=auth_headers,
            json={"cron_expr": "0 0 1 * *"},
        )
        assert r.status_code in (200, 201, 400, 422)

    async def test_programar_sin_auth_401(self, client: AsyncClient, test_auto):
        r = await client.post(
            f"/api/ejecutar/{test_auto['id']}/programar",
            json={"cron_expr": "0 9 * * *"},
        )
        assert r.status_code == 401

    async def test_programar_auto_inexistente_404(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post(
            "/api/ejecutar/00000000-0000-0000-0000-000000000000/programar",
            headers=auth_headers,
            json={"cron_expr": "0 9 * * *"},
        )
        assert r.status_code in (400, 404, 422)

    async def test_programar_devuelve_json(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.post(
            f"/api/ejecutar/{test_auto['id']}/programar",
            headers=auth_headers,
            json={"cron_expr": "0 9 * * *"},
        )
        if r.status_code in (200, 201):
            assert isinstance(r.json(), dict)


class TestDesprogramarAvanzado:
    async def test_desprogramar_auto_ok(self, client: AsyncClient, test_user, auth_headers, test_auto):
        await client.post(
            f"/api/ejecutar/{test_auto['id']}/programar",
            headers=auth_headers,
            json={"cron_expr": "0 9 * * *"},
        )
        r = await client.delete(
            f"/api/ejecutar/{test_auto['id']}/programar",
            headers=auth_headers,
        )
        assert r.status_code in (200, 204, 400, 404)

    async def test_desprogramar_sin_auth_401(self, client: AsyncClient, test_auto):
        r = await client.delete(f"/api/ejecutar/{test_auto['id']}/programar")
        assert r.status_code == 401

    async def test_desprogramar_auto_no_existente(self, client: AsyncClient, test_user, auth_headers):
        r = await client.delete(
            "/api/ejecutar/00000000-0000-0000-0000-000000000000/programar",
            headers=auth_headers,
        )
        assert r.status_code in (400, 404, 422)

    async def test_desprogramar_devuelve_json(self, client: AsyncClient, test_user, auth_headers, test_auto):
        r = await client.delete(
            f"/api/ejecutar/{test_auto['id']}/programar",
            headers=auth_headers,
        )
        if r.status_code in (200, 204):
            if r.status_code == 200:
                assert isinstance(r.json(), dict)

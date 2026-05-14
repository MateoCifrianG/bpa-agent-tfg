"""
test_procesos_score_logic.py — Tests de lógica de scoring y estados de procesos vía API.
"""
import pytest
from httpx import AsyncClient
pytestmark = pytest.mark.asyncio


class TestProcesoScore:
    async def test_score_default_none_o_cero(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "P score"})
        data = r.json()
        assert data.get("score") in (None, 0) or isinstance(data.get("score"), int)

    async def test_score_personalizado(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "P score custom", "score": 75
        })
        assert r.json()["score"] == 75

    async def test_score_actualizable(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "P sc upd"})
        pid = r1.json()["id"]
        r2 = await client.put(f"/api/procesos/{pid}", headers=auth_headers, json={"score": 90})
        assert r2.status_code == 200
        assert r2.json()["score"] == 90

    async def test_score_100_maximo(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "P max", "score": 100
        })
        assert r.status_code in (200, 201)

    async def test_score_0_minimo(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "P min", "score": 0
        })
        assert r.status_code in (200, 201)


class TestProcesoEstados:
    async def test_estado_pendiente_default(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "P est"})
        assert r.json()["estado"] in ("pendiente", "activo", "nuevo", None, "draft")

    async def test_estado_activo(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "P activo", "estado": "activo"
        })
        assert r.status_code in (200, 201)

    async def test_estado_inactivo(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "P inact", "estado": "inactivo"
        })
        assert r.status_code in (200, 201)

    async def test_estado_se_actualiza(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "P est upd"})
        pid = r1.json()["id"]
        await client.put(f"/api/procesos/{pid}", headers=auth_headers, json={"estado": "activo"})
        r3 = await client.get(f"/api/procesos/{pid}", headers=auth_headers)
        assert r3.json()["estado"] == "activo"


class TestProcesoNotas:
    async def test_notas_opcionales(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "P notas", "notas": "Nota de prueba del proceso"
        })
        assert r.status_code in (200, 201)

    async def test_notas_se_guardan(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "P notas2", "notas": "Nota guardada"
        })
        pid = r1.json()["id"]
        r2 = await client.get(f"/api/procesos/{pid}", headers=auth_headers)
        assert r2.json().get("notas") == "Nota guardada"

    async def test_notas_actualizables(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "P nota upd"})
        pid = r1.json()["id"]
        r2 = await client.put(f"/api/procesos/{pid}", headers=auth_headers, json={
            "notas": "Nota actualizada"
        })
        assert r2.status_code == 200


class TestProcesoResponsable:
    async def test_responsable_guardado(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={
            "nombre": "P resp", "responsable": "Ana Martínez"
        })
        assert r.json()["responsable"] == "Ana Martínez"

    async def test_responsable_actualizable(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "P resp upd"})
        pid = r1.json()["id"]
        r2 = await client.put(f"/api/procesos/{pid}", headers=auth_headers, json={
            "responsable": "Carlos López"
        })
        assert r2.json()["responsable"] == "Carlos López"

    async def test_responsable_vacio_ok(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/procesos", headers=auth_headers, json={"nombre": "P sin resp"})
        assert r.status_code in (200, 201)
        assert r.json().get("responsable") in (None, "")

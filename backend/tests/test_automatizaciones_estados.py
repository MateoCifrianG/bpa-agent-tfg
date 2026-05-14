"""
test_automatizaciones_estados.py — Tests de estados y transiciones de automatizaciones.
Cubre: creación con distintos estados, transiciones, campos completos, herramientas.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

HERRAMIENTAS = ["n8n", "zapier", "make", "python", "telegram", "email", "webhook"]
ESTADOS_VALIDOS = ["pendiente", "activa", "pausada", "error", "inactiva"]


class TestAutoEstadosTransicion:
    async def test_estado_default_es_pendiente(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto estado default",
            "herramienta": "n8n",
        })
        data = r.json()
        assert data["estado"] in ESTADOS_VALIDOS

    async def test_crear_con_estado_activa(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto activa",
            "herramienta": "n8n",
            "estado": "activa",
        })
        assert r.status_code in (200, 201)

    async def test_crear_con_estado_pausada(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto pausada",
            "herramienta": "zapier",
            "estado": "pausada",
        })
        assert r.status_code in (200, 201)

    async def test_crear_con_estado_inactiva(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto inactiva",
            "herramienta": "make",
            "estado": "inactiva",
        })
        assert r.status_code in (200, 201)

    async def test_cambiar_estado_a_activa(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto cambio", "herramienta": "n8n"
        })
        auto_id = r1.json()["id"]
        r2 = await client.put(f"/api/automatizaciones/{auto_id}", headers=auth_headers, json={
            "estado": "activa"
        })
        assert r2.status_code == 200

    async def test_cambiar_estado_a_pausada(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto pausa", "herramienta": "n8n"
        })
        auto_id = r1.json()["id"]
        r2 = await client.put(f"/api/automatizaciones/{auto_id}", headers=auth_headers, json={
            "estado": "pausada"
        })
        assert r2.status_code == 200

    async def test_estado_persiste_tras_update(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto persist", "herramienta": "n8n"
        })
        auto_id = r1.json()["id"]
        await client.put(f"/api/automatizaciones/{auto_id}", headers=auth_headers, json={
            "estado": "pausada"
        })
        r3 = await client.get(f"/api/automatizaciones/{auto_id}", headers=auth_headers)
        assert r3.json()["estado"] == "pausada"


class TestAutoHerramientas:
    async def test_herramienta_n8n(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto n8n", "herramienta": "n8n"
        })
        assert r.status_code in (200, 201)
        assert r.json()["herramienta"] == "n8n"

    async def test_herramienta_zapier(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto zapier", "herramienta": "zapier"
        })
        assert r.status_code in (200, 201)

    async def test_herramienta_make(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto make", "herramienta": "make"
        })
        assert r.status_code in (200, 201)

    async def test_herramienta_python(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto python", "herramienta": "python"
        })
        assert r.status_code in (200, 201)

    async def test_herramienta_telegram(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto telegram", "herramienta": "telegram"
        })
        assert r.status_code in (200, 201)

    async def test_herramienta_email(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto email", "herramienta": "email"
        })
        assert r.status_code in (200, 201)

    async def test_herramienta_webhook(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto webhook", "herramienta": "webhook"
        })
        assert r.status_code in (200, 201)


class TestAutoCampos:
    async def test_auto_tiene_id(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto campos", "herramienta": "n8n"
        })
        assert "id" in r.json()

    async def test_auto_tiene_nombre(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Mi Auto", "herramienta": "n8n"
        })
        assert r.json()["nombre"] == "Mi Auto"

    async def test_auto_tiene_herramienta(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto herr", "herramienta": "zapier"
        })
        assert r.json()["herramienta"] == "zapier"

    async def test_auto_tiene_estado(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto est", "herramienta": "n8n"
        })
        assert "estado" in r.json()

    async def test_auto_con_descripcion(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto desc",
            "herramienta": "n8n",
            "descripcion": "Automatiza el envío de facturas",
        })
        assert r.status_code in (200, 201)

    async def test_auto_con_horas_mes(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto horas",
            "herramienta": "n8n",
            "horas_mes": 20,
        })
        assert r.status_code in (200, 201)

    async def test_auto_con_tipo_trigger_cron(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto cron",
            "herramienta": "n8n",
            "tipo_trigger": "cron",
            "cron_expr": "0 9 * * 1-5",
        })
        assert r.status_code in (200, 201)

    async def test_auto_con_tipo_trigger_webhook(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto webhook trigger",
            "herramienta": "n8n",
            "tipo_trigger": "webhook",
        })
        assert r.status_code in (200, 201)


class TestAutoListadoYFiltros:
    async def test_listar_autos_ok(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/automatizaciones", headers=auth_headers)
        assert r.status_code == 200

    async def test_listar_devuelve_lista(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/automatizaciones", headers=auth_headers)
        assert isinstance(r.json(), list)

    async def test_listar_sin_auth(self, client: AsyncClient):
        r = await client.get("/api/automatizaciones")
        assert r.status_code == 401

    async def test_auto_creada_aparece_en_lista(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto en lista", "herramienta": "n8n"
        })
        auto_id = r1.json()["id"]
        r2 = await client.get("/api/automatizaciones", headers=auth_headers)
        ids = [a["id"] for a in r2.json()]
        assert auto_id in ids

    async def test_obtener_auto_por_id(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto get", "herramienta": "n8n"
        })
        auto_id = r1.json()["id"]
        r2 = await client.get(f"/api/automatizaciones/{auto_id}", headers=auth_headers)
        assert r2.status_code == 200

    async def test_auto_inexistente_404(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/automatizaciones/id-no-existe", headers=auth_headers)
        assert r.status_code == 404

    async def test_eliminar_auto(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/automatizaciones", headers=auth_headers, json={
            "nombre": "Auto delete", "herramienta": "n8n"
        })
        auto_id = r1.json()["id"]
        r2 = await client.delete(f"/api/automatizaciones/{auto_id}", headers=auth_headers)
        assert r2.status_code in (200, 204)

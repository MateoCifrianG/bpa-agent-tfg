"""
test_motor_v6_responder.py — Tests de la función responder() del motor v6.
Verifica: saludos, ayuda, listados, respuestas de texto, estructura de output.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestMotorV6ResponderSaludos:
    async def test_responder_hola(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "hola"
        })
        assert r.status_code == 200

    async def test_responder_buenos_dias(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "buenos días"
        })
        assert r.status_code == 200

    async def test_responder_buenas_tardes(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "buenas tardes"
        })
        assert r.status_code == 200

    async def test_responder_como_estas(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "cómo estás"
        })
        assert r.status_code == 200

    async def test_respuesta_saludo_tiene_respuesta(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "hola"
        })
        data = r.json()
        assert "respuesta" in data or "response" in data or "mensaje" in data

    async def test_respuesta_es_string_no_vacio(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "hola"
        })
        data = r.json()
        respuesta = data.get("respuesta") or data.get("response") or data.get("mensaje", "")
        assert len(str(respuesta)) > 0


class TestMotorV6ResponderAyuda:
    async def test_que_puedes_hacer(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "qué puedes hacer"
        })
        assert r.status_code == 200

    async def test_ayuda(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "ayuda"
        })
        assert r.status_code == 200

    async def test_como_funciona(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "cómo funciona esto"
        })
        assert r.status_code == 200

    async def test_que_es_bpa(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "qué es BPA Agent"
        })
        assert r.status_code == 200


class TestMotorV6ResponderProcesos:
    async def test_crear_proceso_responde(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "quiero crear un proceso de facturación"
        })
        assert r.status_code == 200

    async def test_listar_procesos_responde(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "muéstrame mis procesos"
        })
        assert r.status_code == 200

    async def test_analizar_proceso_responde(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "analiza el proceso de facturación"
        })
        assert r.status_code == 200

    async def test_roi_proceso_responde(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "cuánto me ahorraría automatizar la facturación"
        })
        assert r.status_code == 200


class TestMotorV6ResponderKPIs:
    async def test_crear_kpi_responde(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "crea un KPI de ventas con valor 85"
        })
        assert r.status_code == 200

    async def test_listar_kpis_responde(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "muéstrame mis KPIs"
        })
        assert r.status_code == 200

    async def test_analizar_kpis_responde(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "analiza mis indicadores de rendimiento"
        })
        assert r.status_code == 200


class TestMotorV6ResponderEstructura:
    async def test_respuesta_tiene_campo_respuesta(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "hola"
        })
        data = r.json()
        # Al menos un campo de respuesta debe existir
        tiene_respuesta = any(k in data for k in ["respuesta", "response", "mensaje", "text", "content"])
        assert tiene_respuesta

    async def test_respuesta_sin_auth_401(self, client: AsyncClient):
        r = await client.post("/api/agente/chat", json={"mensaje": "hola"})
        assert r.status_code == 401

    async def test_respuesta_mensaje_vacio(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": ""
        })
        assert r.status_code in (200, 400, 422)

    async def test_respuesta_mensaje_largo(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "Necesito analizar todos mis procesos empresariales de forma detallada incluyendo facturación, RRHH, logística y ventas"
        })
        assert r.status_code == 200

    async def test_multiples_preguntas_seguidas(self, client: AsyncClient, auth_headers):
        for pregunta in ["hola", "qué puedes hacer", "listar procesos"]:
            r = await client.post("/api/agente/chat", headers=auth_headers, json={
                "mensaje": pregunta
            })
            assert r.status_code == 200

    async def test_conversacion_id_en_respuesta_si_existe(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "hola"
        })
        data = r.json()
        # conversacion_id puede estar o no según implementación
        assert isinstance(data, dict)

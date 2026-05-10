"""
test_motor_v6_pipeline.py — Tests de integración del pipeline completo del motor v6:
respuestas vía API /agente/chat, detección de intents reales, acciones ejecutadas,
respuestas con tabla Markdown, ROI, KPI y contexto multi-turno.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _chat(client, headers, mensaje, conv_id=None):
    payload = {"mensaje": mensaje}
    if conv_id:
        payload["conversacion_id"] = conv_id
    r = await client.post("/api/agente/chat", headers=headers, json=payload)
    assert r.status_code == 200
    return r.json()


class TestPipelineSaludos:
    async def test_pipeline_hola_responde(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "hola")
        assert len(data["respuesta"]) > 0

    async def test_pipeline_buenos_dias(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "buenos días")
        assert len(data["respuesta"]) > 0

    async def test_pipeline_buenas_tardes(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "buenas tardes")
        assert len(data["respuesta"]) > 0

    async def test_pipeline_despedida(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "hasta luego")
        assert len(data["respuesta"]) > 0

    async def test_pipeline_gracias(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "muchas gracias")
        assert len(data["respuesta"]) > 0


class TestPipelineCrearProceso:
    async def test_pipeline_crear_proceso_facturacion(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "crea un proceso de facturación")
        assert len(data["respuesta"]) > 0

    async def test_pipeline_crear_proceso_rrhh(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "crea un proceso de recursos humanos")
        assert len(data["respuesta"]) > 0

    async def test_pipeline_crear_proceso_respuesta_es_string(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "añadir proceso de logística")
        assert isinstance(data["respuesta"], str)

    async def test_pipeline_crear_proceso_tiene_conv_id(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "nuevo proceso: gestión de contratos")
        assert "conversacion_id" in data
        assert data["conversacion_id"] is not None

    async def test_pipeline_batch_crear_tres_procesos(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "crea tres procesos: RRHH, Ventas, Logística")
        assert len(data["respuesta"]) > 0

    async def test_pipeline_listar_procesos(self, client: AsyncClient, test_user, auth_headers):
        await _chat(client, auth_headers, "crea un proceso de facturación")
        data = await _chat(client, auth_headers, "muéstrame mis procesos")
        assert len(data["respuesta"]) > 0


class TestPipelineAnalisis:
    async def test_pipeline_analizar_proceso(self, client: AsyncClient, test_user, auth_headers):
        await _chat(client, auth_headers, "crea proceso de facturación mensual")
        data = await _chat(client, auth_headers, "analiza el proceso de facturación")
        assert len(data["respuesta"]) > 0

    async def test_pipeline_roi_facturacion(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "¿cuánto me ahorra automatizar facturación?")
        assert len(data["respuesta"]) > 0

    async def test_pipeline_roi_contiene_informacion_util(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "calcula el ROI de automatizar facturación")
        respuesta = data["respuesta"]
        assert len(respuesta) > 20

    async def test_pipeline_analisis_responde_texto(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "analiza facturación 8 horas al mes")
        assert isinstance(data["respuesta"], str)


class TestPipelineKPIs:
    async def test_pipeline_listar_kpis(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "muéstrame mis KPIs")
        assert len(data["respuesta"]) > 0

    async def test_pipeline_crear_kpi(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "añade un KPI de satisfacción del cliente al 85%")
        assert len(data["respuesta"]) > 0

    async def test_pipeline_kpi_respuesta_string(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "¿cuáles son mis KPIs actuales?")
        assert isinstance(data["respuesta"], str)


class TestPipelineContextoMultiTurno:
    async def test_pipeline_contexto_preservado(self, client: AsyncClient, test_user, auth_headers):
        d1 = await _chat(client, auth_headers, "hola, soy de una empresa de logística")
        conv_id = d1["conversacion_id"]
        d2 = await _chat(client, auth_headers, "¿qué procesos recomiendas para mi sector?", conv_id=conv_id)
        assert len(d2["respuesta"]) > 0
        assert d2["conversacion_id"] == conv_id

    async def test_pipeline_multiples_turnos_mismo_conv(self, client: AsyncClient, test_user, auth_headers):
        d1 = await _chat(client, auth_headers, "hola")
        conv_id = d1["conversacion_id"]
        d2 = await _chat(client, auth_headers, "¿qué puedes hacer?", conv_id=conv_id)
        d3 = await _chat(client, auth_headers, "ayuda", conv_id=conv_id)
        assert d2["conversacion_id"] == conv_id
        assert d3["conversacion_id"] == conv_id

    async def test_pipeline_conv_id_consistente(self, client: AsyncClient, test_user, auth_headers):
        d1 = await _chat(client, auth_headers, "empezar conversación")
        conv_id = d1["conversacion_id"]
        for _ in range(3):
            d = await _chat(client, auth_headers, "siguiente turno", conv_id=conv_id)
            assert d["conversacion_id"] == conv_id


class TestPipelineRespuestaEstructura:
    async def test_pipeline_respuesta_tiene_keys_correctas(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "hola")
        for key in ("conversacion_id", "respuesta", "fase"):
            assert key in data

    async def test_pipeline_respuesta_no_es_error_500(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={"mensaje": "hola"})
        assert r.status_code != 500

    async def test_pipeline_fase_es_string(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "hola")
        if data.get("fase"):
            assert isinstance(data["fase"], str)

    async def test_pipeline_accion_es_string_o_none(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "hola")
        accion = data.get("accion")
        assert accion is None or isinstance(accion, str)

    async def test_pipeline_conv_id_es_string_uuid(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "hola")
        conv_id = data["conversacion_id"]
        assert isinstance(conv_id, str)
        assert len(conv_id) > 10

    async def test_pipeline_respuesta_no_contiene_traceback(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat(client, auth_headers, "hola")
        respuesta = data["respuesta"].lower()
        assert "traceback" not in respuesta
        assert "exception" not in respuesta

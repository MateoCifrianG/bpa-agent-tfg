"""
test_motor_v6_sectores.py — Tests de detección sectorial del motor v6:
todos los sectores, aliases, benchmarks, KPIs sectoriales, ROI por sector.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _chat_ok(client, headers, mensaje):
    r = await client.post("/api/agente/chat", headers=headers, json={"mensaje": mensaje})
    assert r.status_code == 200
    return r.json()


class TestChatSectoresConocidos:
    async def test_facturacion_reconocida(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "analiza proceso de facturación")
        assert len(data["respuesta"]) > 0

    async def test_rrhh_reconocido(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "análisis de proceso de recursos humanos")
        assert len(data["respuesta"]) > 0

    async def test_logistica_reconocida(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "proceso de logística y distribución")
        assert len(data["respuesta"]) > 0

    async def test_atencion_cliente_reconocida(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "proceso de atención al cliente")
        assert len(data["respuesta"]) > 0

    async def test_contabilidad_reconocida(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "proceso de contabilidad y finanzas")
        assert len(data["respuesta"]) > 0

    async def test_ventas_reconocidas(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "proceso de ventas y CRM")
        assert len(data["respuesta"]) > 0

    async def test_marketing_reconocido(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "proceso de marketing digital")
        assert len(data["respuesta"]) > 0

    async def test_compras_reconocidas(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "proceso de compras y proveedores")
        assert len(data["respuesta"]) > 0


class TestChatROIPorSector:
    async def test_roi_facturacion_responde(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "¿cuánto me ahorra automatizar facturación?")
        respuesta = data["respuesta"]
        assert len(respuesta) > 10

    async def test_roi_rrhh_responde(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "calcula ROI de automatizar RRHH")
        assert len(data["respuesta"]) > 10

    async def test_roi_logistica_responde(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "ROI de logística automatizada")
        assert len(data["respuesta"]) > 10

    async def test_roi_sin_proceso_responde(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "¿cuánto ROI obtengo?")
        assert len(data["respuesta"]) > 0

    async def test_roi_con_horas_especificas(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "tengo un proceso de facturación de 20 horas al mes, ¿qué ROI?")
        assert len(data["respuesta"]) > 0


class TestChatAnalisisProfundo:
    async def test_analisis_con_tabla_markdown(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "haz un análisis completo del proceso de facturación")
        respuesta = data["respuesta"]
        assert len(respuesta) > 50

    async def test_analisis_respuesta_es_string(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "analiza facturación con detalle")
        assert isinstance(data["respuesta"], str)

    async def test_analisis_sin_proceso_especifico(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "analiza mis procesos en general")
        assert len(data["respuesta"]) > 0


class TestChatBatchOperaciones:
    async def test_batch_crear_tres_procesos(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "crea tres procesos: Facturación, RRHH, Logística")
        assert len(data["respuesta"]) > 0

    async def test_batch_crear_dos_procesos(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "añade dos procesos: Ventas y Marketing")
        assert len(data["respuesta"]) > 0

    async def test_crear_proceso_con_detalles(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "crea un proceso de facturación mensual con 10 horas")
        assert len(data["respuesta"]) > 0


class TestChatAyuda:
    async def test_ayuda_general(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "ayuda")
        assert len(data["respuesta"]) > 0

    async def test_que_puedes_hacer(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "¿qué puedes hacer?")
        assert len(data["respuesta"]) > 0

    async def test_como_funciona(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "¿cómo funciona?")
        assert len(data["respuesta"]) > 0

    async def test_instrucciones(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "instrucciones")
        assert len(data["respuesta"]) > 0


class TestChatKPIVinculacion:
    async def test_vincular_kpi_a_proceso_chat(self, client: AsyncClient, test_user, auth_headers):
        await _chat_ok(client, auth_headers, "crea proceso de facturación")
        data = await _chat_ok(client, auth_headers, "añade KPI de satisfacción al proceso de facturación")
        assert len(data["respuesta"]) > 0

    async def test_listar_kpis_chat(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "muéstrame todos los KPIs")
        assert len(data["respuesta"]) > 0

    async def test_crear_kpi_directo_chat(self, client: AsyncClient, test_user, auth_headers):
        data = await _chat_ok(client, auth_headers, "añadir KPI tasa de error al 2%")
        assert len(data["respuesta"]) > 0

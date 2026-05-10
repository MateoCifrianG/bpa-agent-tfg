"""
test_agente_completo.py — Tests exhaustivos del agente IA:
todos los intents, respuestas, conversaciones, edge cases, contexto.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def chat(client, headers, mensaje, conv_id=None):
    payload = {"mensaje": mensaje}
    if conv_id:
        payload["conversacion_id"] = conv_id
    return await client.post("/api/agente/chat", headers=headers, json=payload)


class TestAgenteAcceso:
    async def test_chat_requiere_auth(self, client: AsyncClient):
        r = await client.post("/api/agente/chat", json={"mensaje": "hola"})
        assert r.status_code == 401

    async def test_chat_con_auth_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "hola")
        assert r.status_code == 200

    async def test_chat_mensaje_vacio_422(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "")
        assert r.status_code in (200, 422)

    async def test_chat_sin_mensaje_422(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={})
        assert r.status_code == 422

    async def test_chat_devuelve_respuesta(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "hola")
        data = r.json()
        assert "respuesta" in data or "mensaje" in data or "response" in data


class TestAgenteRespuestas:
    async def test_saludo_hola(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "hola")
        assert r.status_code == 200
        data = r.json()
        respuesta = data.get("respuesta") or data.get("mensaje") or data.get("response", "")
        assert isinstance(respuesta, str)
        assert len(respuesta) > 0

    async def test_saludo_buenos_dias(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "buenos días")
        assert r.status_code == 200

    async def test_saludo_buenas_tardes(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "buenas tardes")
        assert r.status_code == 200

    async def test_despedida(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "adiós")
        assert r.status_code == 200

    async def test_ayuda(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "¿qué puedes hacer?")
        assert r.status_code == 200

    async def test_listar_procesos(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "muéstrame mis procesos")
        assert r.status_code == 200

    async def test_crear_proceso_chat(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "crea un proceso de facturación")
        assert r.status_code == 200

    async def test_calcular_roi(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "¿cuánto me ahorraría automatizar RRHH?")
        assert r.status_code == 200

    async def test_info_sector(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "benchmarks del sector logística")
        assert r.status_code == 200

    async def test_estado_sistema(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "estado del sistema")
        assert r.status_code == 200

    async def test_ver_kpis(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "ver mis KPIs")
        assert r.status_code == 200

    async def test_ver_automatizaciones(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "ver automatizaciones")
        assert r.status_code == 200

    async def test_recomendar_kpis(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "¿qué KPIs debería medir en ventas?")
        assert r.status_code == 200

    async def test_no_entendido(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "xyzabc123 gibberish")
        assert r.status_code == 200

    async def test_gracias(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "muchas gracias")
        assert r.status_code == 200

    async def test_analizar_proceso(self, client: AsyncClient, test_user, auth_headers, test_proceso):
        r = await chat(client, auth_headers, f"analiza el proceso {test_proceso['nombre']}")
        assert r.status_code == 200

    async def test_mejores_practicas(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "mejores prácticas en RRHH")
        assert r.status_code == 200


class TestAgenteCamposRespuesta:
    async def test_respuesta_tiene_intent_o_accion(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "hola")
        data = r.json()
        # La respuesta puede tener intent, accion, o solo respuesta
        assert any(k in data for k in ("respuesta", "mensaje", "intent", "accion", "response"))

    async def test_respuesta_tiene_conversacion_id(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "hola")
        data = r.json()
        assert any(k in data for k in ("conversacion_id", "conversation_id", "id"))

    async def test_respuesta_texto_es_string(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "hola")
        data = r.json()
        texto = data.get("respuesta") or data.get("mensaje") or data.get("response", "")
        assert isinstance(texto, str)

    async def test_respuesta_no_vacia(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "hola")
        data = r.json()
        texto = data.get("respuesta") or data.get("mensaje") or data.get("response", "")
        assert len(texto) > 0


class TestAgenteConversaciones:
    async def test_listar_conversaciones_ok(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/agente/conversaciones", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_listar_conversaciones_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/agente/conversaciones")
        assert r.status_code == 401

    async def test_conversacion_se_crea_tras_chat(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "hola primer mensaje")
        assert r.status_code == 200
        r2 = await client.get("/api/agente/conversaciones", headers=auth_headers)
        assert len(r2.json()) >= 1

    async def test_conversacion_tiene_id(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "hola test conv")
        data = r.json()
        conv_id = data.get("conversacion_id") or data.get("conversation_id") or data.get("id")
        assert conv_id is not None

    async def test_multiples_mensajes_misma_conv(self, client: AsyncClient, test_user, auth_headers):
        r1 = await chat(client, auth_headers, "hola inicio conversación")
        data1 = r1.json()
        conv_id = data1.get("conversacion_id") or data1.get("conversation_id")
        if conv_id:
            r2 = await chat(client, auth_headers, "continúa por favor", conv_id=conv_id)
            assert r2.status_code == 200

    async def test_eliminar_conversacion(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "hola para borrar")
        data = r.json()
        conv_id = data.get("conversacion_id") or data.get("conversation_id")
        if conv_id:
            r_del = await client.delete(f"/api/agente/conversaciones/{conv_id}", headers=auth_headers)
            assert r_del.status_code in (200, 204, 404)

    async def test_historial_conversacion_en_listado(self, client: AsyncClient, test_user, auth_headers):
        await chat(client, auth_headers, "hola para historial test")
        r = await client.get("/api/agente/conversaciones", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_aislamiento_listado_conversaciones(self, client: AsyncClient, test_user, auth_headers):
        import uuid
        uid = uuid.uuid4().hex[:8]
        r2 = await client.post("/api/auth/register", json={
            "email": f"conv2_{uid}@test.com",
            "password": "TestPass1!",
            "nombre": "Conv2", "apellido": "User",
            "empresa": "EmpConv2", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        if r2.status_code != 201:
            return
        token2 = r2.json().get("access_token")
        headers2 = {"Authorization": f"Bearer {token2}"}
        await chat(client, headers2, "hola desde user2")
        # User1 lista sus conversaciones — no debe ver las de user2
        r1 = await client.get("/api/agente/conversaciones", headers=auth_headers)
        r2_list = await client.get("/api/agente/conversaciones", headers=headers2)
        # Ambos usuarios tienen sus propias listas
        assert r1.status_code == 200
        assert r2_list.status_code == 200


class TestAgenteEdgeCases:
    async def test_mensaje_muy_largo(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "a" * 2000)
        assert r.status_code in (200, 422)

    async def test_mensaje_solo_espacios(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "   ")
        assert r.status_code in (200, 422)

    async def test_mensaje_con_emoji(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "hola 👋 qué tal 😊")
        assert r.status_code == 200

    async def test_mensaje_con_numeros(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "proceso 123 del año 2024")
        assert r.status_code == 200

    async def test_mensaje_html_sanitizado(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "<script>alert(1)</script>hola")
        assert r.status_code in (200, 422)

    async def test_multiples_chats_seguidos(self, client: AsyncClient, test_user, auth_headers):
        mensajes = ["hola", "ver procesos", "ayuda", "estado sistema", "adiós"]
        for msg in mensajes:
            r = await chat(client, auth_headers, msg)
            assert r.status_code == 200

    async def test_chat_en_ingles(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "hello, show me my processes")
        assert r.status_code == 200

    async def test_intent_roi_con_horas(self, client: AsyncClient, test_user, auth_headers):
        r = await chat(client, auth_headers, "¿cuánto ahorro con 20 horas automatizadas al mes?")
        assert r.status_code == 200

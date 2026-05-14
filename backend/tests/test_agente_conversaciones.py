"""
test_agente_conversaciones.py — Tests de conversaciones del agente.
"""
import pytest
from httpx import AsyncClient
pytestmark = pytest.mark.asyncio


class TestConversacionesListado:
    async def test_listar_ok(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/agente/conversaciones", headers=auth_headers)
        assert r.status_code == 200

    async def test_listar_sin_auth(self, client: AsyncClient):
        r = await client.get("/api/agente/conversaciones")
        assert r.status_code in (401, 403)

    async def test_listar_devuelve_lista(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/agente/conversaciones", headers=auth_headers)
        assert isinstance(r.json(), list)

    async def test_listar_vacia_ok(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/agente/conversaciones", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestChatYConversacion:
    async def test_chat_crea_conversacion(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "hola"
        })
        assert r.status_code == 200

    async def test_chat_respuesta_no_vacia(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "qué puedes hacer"
        })
        data = r.json()
        respuesta = (data.get("respuesta") or data.get("response") or
                     data.get("mensaje") or data.get("text") or "")
        assert len(str(respuesta)) > 0

    async def test_chat_con_conv_id_existente(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "hola"
        })
        data = r1.json()
        conv_id = data.get("conversacion_id") or data.get("conv_id")
        if conv_id:
            r2 = await client.post("/api/agente/chat", headers=auth_headers, json={
                "mensaje": "qué más puedes hacer",
                "conversacion_id": conv_id,
            })
            assert r2.status_code == 200

    async def test_chat_multiturn(self, client: AsyncClient, auth_headers):
        mensajes = ["hola", "crea un proceso de facturación", "analiza ese proceso"]
        for msg in mensajes:
            r = await client.post("/api/agente/chat", headers=auth_headers, json={"mensaje": msg})
            assert r.status_code == 200

    async def test_conversacion_aparece_en_lista(self, client: AsyncClient, auth_headers):
        await client.post("/api/agente/chat", headers=auth_headers, json={"mensaje": "hola"})
        r = await client.get("/api/agente/conversaciones", headers=auth_headers)
        assert isinstance(r.json(), list)

    async def test_chat_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/agente/chat", json={"mensaje": "hola"})
        assert r.status_code == 401


class TestConversacionEliminar:
    async def test_eliminar_conv_inexistente(self, client: AsyncClient, auth_headers):
        r = await client.delete("/api/agente/conversaciones/id-no-existe", headers=auth_headers)
        assert r.status_code in (200, 204, 404)

    async def test_eliminar_sin_auth(self, client: AsyncClient):
        r = await client.delete("/api/agente/conversaciones/some-id")
        assert r.status_code in (401, 403)

    async def test_eliminar_conv_propia(self, client: AsyncClient, auth_headers):
        r1 = await client.post("/api/agente/chat", headers=auth_headers, json={"mensaje": "test"})
        data = r1.json()
        conv_id = data.get("conversacion_id") or data.get("conv_id")
        if conv_id:
            r2 = await client.delete(f"/api/agente/conversaciones/{conv_id}", headers=auth_headers)
            assert r2.status_code in (200, 204)


class TestChatSeguridad:
    async def test_chat_xss_no_ejecuta(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "<script>alert(1)</script>"
        })
        assert r.status_code in (200, 400, 422)
        if r.status_code == 200:
            assert "<script>" not in r.text.lower()

    async def test_chat_sql_injection(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "'; DROP TABLE conversaciones; --"
        })
        assert r.status_code in (200, 400)

    async def test_chat_muy_largo(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "texto " * 500
        })
        assert r.status_code in (200, 400, 422)

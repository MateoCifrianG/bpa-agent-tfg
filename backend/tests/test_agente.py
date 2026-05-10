"""
test_agente.py — Tests del endpoint de chat y conversaciones del agente BPA.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestChatAcceso:
    async def test_chat_sin_auth(self, client: AsyncClient):
        r = await client.post("/api/agente/chat", json={"mensaje": "Hola"})
        assert r.status_code == 401

    async def test_conversaciones_sin_auth(self, client: AsyncClient):
        r = await client.get("/api/agente/conversaciones")
        assert r.status_code == 401

    async def test_delete_conversacion_sin_auth(self, client: AsyncClient):
        r = await client.delete("/api/agente/conversaciones/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 401


class TestChatBasico:
    async def test_chat_responde(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "Hola",
        })
        assert r.status_code == 200
        data = r.json()
        assert "respuesta" in data
        assert "conversacion_id" in data

    async def test_chat_respuesta_no_vacia(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "¿Qué puedes hacer?",
        })
        assert r.status_code == 200
        assert len(r.json()["respuesta"]) > 0

    async def test_chat_devuelve_conversacion_id(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "Hola agente",
        })
        assert r.status_code == 200
        assert r.json()["conversacion_id"] is not None

    async def test_chat_mensaje_vacio_falla(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "   ",
        })
        assert r.status_code == 422

    async def test_chat_mensaje_muy_largo_truncado(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "A" * 3000,
        })
        # Acepta pero trunca, o rechaza con 422
        assert r.status_code in (200, 422)

    async def test_chat_continua_conversacion(self, client: AsyncClient, test_user, auth_headers):
        r1 = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "Hola",
        })
        conv_id = r1.json()["conversacion_id"]
        r2 = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "¿Qué sabes de mis procesos?",
            "conversacion_id": conv_id,
        })
        assert r2.status_code == 200
        assert r2.json()["conversacion_id"] == conv_id

    async def test_chat_conversacion_id_inexistente_crea_nueva(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "Hola",
            "conversacion_id": "00000000-0000-0000-0000-000000000000",
        })
        assert r.status_code == 200
        # Crea nueva conversación porque la ID no existe
        assert r.json()["conversacion_id"] != "00000000-0000-0000-0000-000000000000"

    async def test_chat_fase_presente_en_respuesta(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "Hola",
        })
        assert r.status_code == 200
        assert "fase" in r.json()


class TestChatIntenciones:
    async def test_chat_listar_procesos(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "muéstrame mis procesos",
        })
        assert r.status_code == 200
        assert len(r.json()["respuesta"]) > 0

    async def test_chat_crear_proceso(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "crea un proceso de facturación",
        })
        assert r.status_code == 200
        assert len(r.json()["respuesta"]) > 0

    async def test_chat_roi_analisis(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "¿cuánto me ahorraría automatizar el proceso de nóminas?",
        })
        assert r.status_code == 200

    async def test_chat_saludo(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "buenos días",
        })
        assert r.status_code == 200

    async def test_chat_ayuda(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/agente/chat", headers=auth_headers, json={
            "mensaje": "ayuda",
        })
        assert r.status_code == 200


class TestConversaciones:
    async def test_listar_conversaciones_vacio(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/agente/conversaciones", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_listar_conversaciones_tras_chat(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/agente/chat", headers=auth_headers, json={"mensaje": "hola"})
        r = await client.get("/api/agente/conversaciones", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    async def test_conversacion_tiene_campos_requeridos(self, client: AsyncClient, test_user, auth_headers):
        await client.post("/api/agente/chat", headers=auth_headers, json={"mensaje": "hola"})
        r = await client.get("/api/agente/conversaciones", headers=auth_headers)
        assert r.status_code == 200
        conv = r.json()[0]
        for campo in ["id", "empresa_id"]:
            assert campo in conv

    async def test_eliminar_conversacion(self, client: AsyncClient, test_user, auth_headers):
        cr = await client.post("/api/agente/chat", headers=auth_headers, json={"mensaje": "hola"})
        conv_id = cr.json()["conversacion_id"]
        r = await client.delete(f"/api/agente/conversaciones/{conv_id}", headers=auth_headers)
        assert r.status_code == 204

    async def test_eliminar_conversacion_no_existe(self, client: AsyncClient, test_user, auth_headers):
        r = await client.delete(
            "/api/agente/conversaciones/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert r.status_code == 404

    async def test_no_accede_conversacion_de_otro_usuario(
        self, client: AsyncClient, auth_headers, admin_headers, test_user, admin_user
    ):
        cr = await client.post("/api/agente/chat", headers=admin_headers, json={"mensaje": "hola admin"})
        conv_id = cr.json()["conversacion_id"]
        r = await client.delete(f"/api/agente/conversaciones/{conv_id}", headers=auth_headers)
        assert r.status_code == 404

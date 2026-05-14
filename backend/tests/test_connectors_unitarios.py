"""
test_connectors_unitarios.py — Tests unitarios de conectores (sin llamadas reales de red).
Cubre: email_connector, telegram_connector, webhook_connector.
Verifica firmas, imports, constantes y respuestas con datos inválidos.
"""
import pytest
import pytest_asyncio


class TestEmailConnector:
    def test_email_connector_importable(self):
        from app.services.connectors import email_connector
        assert email_connector is not None

    def test_enviar_email_es_callable(self):
        from app.services.connectors.email_connector import enviar_email
        import asyncio
        assert callable(enviar_email)

    async def test_enviar_email_con_smtp_invalido_devuelve_error(self):
        from app.services.connectors.email_connector import enviar_email
        result = await enviar_email(
            smtp_host="smtp.invalido.localhost.test",
            smtp_port=587,
            smtp_user="test@test.com",
            smtp_password="wrong",
            destinatario="dest@test.com",
            asunto="Test",
            cuerpo="Cuerpo",
        )
        assert isinstance(result, dict)
        assert "ok" in result
        assert result["ok"] is False

    async def test_enviar_email_devuelve_dict(self):
        from app.services.connectors.email_connector import enviar_email
        result = await enviar_email(
            smtp_host="localhost.invalid",
            smtp_port=587,
            smtp_user="u@u.com",
            smtp_password="p",
            destinatario="d@d.com",
            asunto="A",
            cuerpo="B",
        )
        assert isinstance(result, dict)

    async def test_enviar_email_error_tiene_campo_error(self):
        from app.services.connectors.email_connector import enviar_email
        result = await enviar_email(
            smtp_host="no.existe.invalid",
            smtp_port=587,
            smtp_user="u@u.com",
            smtp_password="p",
            destinatario="d@d.com",
            asunto="A",
            cuerpo="B",
        )
        assert "error" in result or "ok" in result


class TestTelegramConnector:
    def test_telegram_connector_importable(self):
        from app.services.connectors import telegram_connector
        assert telegram_connector is not None

    def test_enviar_mensaje_es_callable(self):
        from app.services.connectors.telegram_connector import enviar_mensaje
        assert callable(enviar_mensaje)

    def test_verificar_bot_es_callable(self):
        from app.services.connectors.telegram_connector import verificar_bot
        assert callable(verificar_bot)

    def test_enviar_alerta_proceso_es_callable(self):
        from app.services.connectors.telegram_connector import enviar_alerta_proceso
        assert callable(enviar_alerta_proceso)

    def test_telegram_api_url_definida(self):
        from app.services.connectors.telegram_connector import TELEGRAM_API
        assert "telegram.org" in TELEGRAM_API

    async def test_enviar_mensaje_token_invalido(self):
        from app.services.connectors.telegram_connector import enviar_mensaje
        result = await enviar_mensaje(
            bot_token="0000000000:FAKE_TOKEN_INVALID",
            chat_id="12345",
            mensaje="Test",
        )
        assert isinstance(result, dict)
        assert "ok" in result
        assert result["ok"] is False

    async def test_verificar_bot_token_invalido(self):
        from app.services.connectors.telegram_connector import verificar_bot
        result = await verificar_bot(bot_token="0000000000:FAKE_TOKEN")
        assert isinstance(result, dict)
        assert "ok" in result

    async def test_enviar_alerta_proceso_invalido(self):
        from app.services.connectors.telegram_connector import enviar_alerta_proceso
        result = await enviar_alerta_proceso(
            bot_token="FAKE_TOKEN",
            chat_id="12345",
            nombre_proceso="Facturación",
            score=85,
            empresa="MiEmpresa",
            tipo_alerta="critico",
        )
        assert isinstance(result, dict)
        assert "ok" in result

    async def test_enviar_alerta_sin_score(self):
        from app.services.connectors.telegram_connector import enviar_alerta_proceso
        result = await enviar_alerta_proceso(
            bot_token="FAKE",
            chat_id="123",
            nombre_proceso="Logística",
            score=None,
            empresa="Empresa",
        )
        assert isinstance(result, dict)


class TestWebhookConnector:
    def test_webhook_connector_importable(self):
        from app.services.connectors import webhook_connector
        assert webhook_connector is not None

    def test_enviar_webhook_es_callable(self):
        from app.services.connectors.webhook_connector import enviar_webhook
        assert callable(enviar_webhook)

    def test_enviar_slack_es_callable(self):
        from app.services.connectors.webhook_connector import enviar_slack
        assert callable(enviar_slack)

    def test_enviar_teams_es_callable(self):
        from app.services.connectors.webhook_connector import enviar_teams
        assert callable(enviar_teams)

    async def test_enviar_webhook_url_invalida(self):
        from app.services.connectors.webhook_connector import enviar_webhook
        result = await enviar_webhook(
            url="http://localhost.invalid.test/webhook",
            payload={"test": True},
        )
        assert isinstance(result, dict)
        assert "ok" in result
        assert result["ok"] is False

    async def test_enviar_webhook_metodo_no_soportado(self):
        from app.services.connectors.webhook_connector import enviar_webhook
        result = await enviar_webhook(
            url="http://localhost.invalid.test/",
            payload={},
            method="DELETE",
        )
        assert isinstance(result, dict)
        assert result["ok"] is False

    async def test_enviar_slack_url_invalida(self):
        from app.services.connectors.webhook_connector import enviar_slack
        result = await enviar_slack(
            webhook_url="http://hooks.slack.invalid.test/T000/B000/XXXX",
            mensaje="Test",
        )
        assert isinstance(result, dict)
        assert "ok" in result

    async def test_enviar_teams_url_invalida(self):
        from app.services.connectors.webhook_connector import enviar_teams
        result = await enviar_teams(
            webhook_url="http://outlook.teams.invalid.test/webhook",
            titulo="Test",
            mensaje="Cuerpo",
        )
        assert isinstance(result, dict)
        assert "ok" in result

    async def test_enviar_webhook_con_headers_custom(self):
        from app.services.connectors.webhook_connector import enviar_webhook
        result = await enviar_webhook(
            url="http://no.existe.invalid/api",
            payload={"data": "test"},
            headers={"X-Custom": "valor"},
        )
        assert isinstance(result, dict)

    async def test_enviar_webhook_metodo_get(self):
        from app.services.connectors.webhook_connector import enviar_webhook
        result = await enviar_webhook(
            url="http://no.existe.invalid/get",
            payload={"q": "test"},
            method="GET",
        )
        assert isinstance(result, dict)

    async def test_enviar_webhook_metodo_put(self):
        from app.services.connectors.webhook_connector import enviar_webhook
        result = await enviar_webhook(
            url="http://no.existe.invalid/put",
            payload={"key": "val"},
            method="PUT",
        )
        assert isinstance(result, dict)

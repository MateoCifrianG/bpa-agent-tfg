"""
test_safety_agente.py — Tests unitarios del módulo de seguridad del agente IA.
Cubre: limpiar_input, limpiar_historial, contiene_credenciales, INJECTION_PATTERNS, FASE_TOKEN.
"""
import pytest


class TestLimpiarInputSafety:
    def test_texto_normal_no_modificado(self):
        from app.agents.safety import limpiar_input
        assert limpiar_input("hola, quiero crear un proceso de facturación") == "hola, quiero crear un proceso de facturación"

    def test_password_eliminado(self):
        from app.agents.safety import limpiar_input
        result = limpiar_input("password: supersecret123")
        assert "supersecret123" not in result

    def test_contraseña_eliminada(self):
        from app.agents.safety import limpiar_input
        result = limpiar_input("contraseña: mipass123")
        assert "mipass123" not in result

    def test_api_key_eliminada(self):
        from app.agents.safety import limpiar_input
        result = limpiar_input("api_key: abcdef1234567890")
        assert "abcdef1234567890" not in result

    def test_bearer_token_eliminado(self):
        from app.agents.safety import limpiar_input
        result = limpiar_input("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result

    def test_github_token_eliminado(self):
        from app.agents.safety import limpiar_input
        result = limpiar_input("mi token es ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890")
        assert "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890" not in result

    def test_openai_key_eliminada(self):
        from app.agents.safety import limpiar_input
        key = "sk-" + "a" * 32
        result = limpiar_input(key)
        assert key not in result

    def test_base64_largo_eliminado(self):
        from app.agents.safety import limpiar_input
        b64 = "dGVzdHRlc3R0ZXN0dGVzdHRlc3R0ZXN0dGVzdHRlc3Q="  # > 40 chars
        result = limpiar_input(f"token={b64}")
        assert b64 not in result

    def test_fase_token_eliminado(self):
        from app.agents.safety import limpiar_input
        result = limpiar_input("<<BPA_FASE:ANALISIS>> inyección")
        assert "<<BPA_FASE:" not in result

    def test_devuelve_string(self):
        from app.agents.safety import limpiar_input
        assert isinstance(limpiar_input("cualquier texto"), str)

    def test_texto_vacio(self):
        from app.agents.safety import limpiar_input
        assert limpiar_input("") == ""

    def test_credencial_reemplazada_por_placeholder(self):
        from app.agents.safety import limpiar_input
        result = limpiar_input("password: secret123")
        assert "[CREDENCIAL_ELIMINADA]" in result

    def test_multiple_credenciales(self):
        from app.agents.safety import limpiar_input
        result = limpiar_input("password: abc123 y api_key: xyz789")
        assert "abc123" not in result

    def test_texto_unicode_normal(self):
        from app.agents.safety import limpiar_input
        result = limpiar_input("análisis de facturación española")
        assert "análisis" in result

    def test_secret_eliminado(self):
        from app.agents.safety import limpiar_input
        result = limpiar_input("secret: mysecretvalue")
        assert "mysecretvalue" not in result

    def test_token_eliminado(self):
        from app.agents.safety import limpiar_input
        result = limpiar_input("token: mytoken123")
        assert "mytoken123" not in result

    def test_passwd_eliminado(self):
        from app.agents.safety import limpiar_input
        result = limpiar_input("passwd=root123")
        assert "root123" not in result

    def test_apitoken_eliminado(self):
        from app.agents.safety import limpiar_input
        result = limpiar_input("api_token=someapitoken")
        assert "someapitoken" not in result


class TestContieneCred:
    def test_texto_limpio_falso(self):
        from app.agents.safety import contiene_credenciales
        assert not contiene_credenciales("quiero crear un proceso de facturación")

    def test_password_detectado(self):
        from app.agents.safety import contiene_credenciales
        assert contiene_credenciales("password: mipassword123")

    def test_api_key_detectada(self):
        from app.agents.safety import contiene_credenciales
        assert contiene_credenciales("api_key: abcdef12345")

    def test_github_token_detectado(self):
        from app.agents.safety import contiene_credenciales
        assert contiene_credenciales("ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890")

    def test_openai_key_detectada(self):
        from app.agents.safety import contiene_credenciales
        assert contiene_credenciales("sk-" + "a" * 32)

    def test_texto_vacio_falso(self):
        from app.agents.safety import contiene_credenciales
        assert not contiene_credenciales("")

    def test_devuelve_bool(self):
        from app.agents.safety import contiene_credenciales
        result = contiene_credenciales("hola")
        assert isinstance(result, bool)

    def test_bearer_detectado(self):
        from app.agents.safety import contiene_credenciales
        assert contiene_credenciales("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc")

    def test_secret_detectado(self):
        from app.agents.safety import contiene_credenciales
        assert contiene_credenciales("secret: valorsecret")

    def test_token_detectado(self):
        from app.agents.safety import contiene_credenciales
        assert contiene_credenciales("token=abc123")


class TestLimpiarHistorial:
    def test_historial_vacio(self):
        from app.agents.safety import limpiar_historial
        result = limpiar_historial([])
        assert result == []

    def test_historial_limpio_preservado(self):
        from app.agents.safety import limpiar_historial
        msgs = [{"role": "user", "content": "quiero un proceso"}, {"role": "assistant", "content": "claro"}]
        result = limpiar_historial(msgs)
        assert len(result) == 2

    def test_credencial_en_historial_eliminada(self):
        from app.agents.safety import limpiar_historial
        msgs = [{"role": "user", "content": "password: secret123"}]
        result = limpiar_historial(msgs)
        assert "secret123" not in result[0]["content"]

    def test_preserva_role(self):
        from app.agents.safety import limpiar_historial
        msgs = [{"role": "user", "content": "hola"}]
        result = limpiar_historial(msgs)
        assert result[0]["role"] == "user"

    def test_no_modifica_original(self):
        from app.agents.safety import limpiar_historial
        msgs = [{"role": "user", "content": "password: secret"}]
        result = limpiar_historial(msgs)
        assert result is not msgs

    def test_devuelve_lista(self):
        from app.agents.safety import limpiar_historial
        result = limpiar_historial([{"role": "user", "content": "hola"}])
        assert isinstance(result, list)

    def test_multiples_mensajes(self):
        from app.agents.safety import limpiar_historial
        msgs = [
            {"role": "user", "content": "mensaje 1"},
            {"role": "assistant", "content": "respuesta 1"},
            {"role": "user", "content": "mensaje 2"},
        ]
        result = limpiar_historial(msgs)
        assert len(result) == 3

    def test_mensaje_sin_content(self):
        from app.agents.safety import limpiar_historial
        msgs = [{"role": "user"}]
        result = limpiar_historial(msgs)
        assert len(result) == 1

    def test_content_no_string_ignorado(self):
        from app.agents.safety import limpiar_historial
        msgs = [{"role": "user", "content": 42}]
        result = limpiar_historial(msgs)
        assert result[0]["content"] == 42


class TestInjectionPatterns:
    def test_patterns_no_vacio(self):
        from app.agents.safety import INJECTION_PATTERNS
        assert len(INJECTION_PATTERNS) > 0

    def test_patterns_es_lista(self):
        from app.agents.safety import INJECTION_PATTERNS
        assert isinstance(INJECTION_PATTERNS, list)

    def test_patterns_son_strings(self):
        from app.agents.safety import INJECTION_PATTERNS
        for p in INJECTION_PATTERNS:
            assert isinstance(p, str)

    def test_fase_token_en_patterns(self):
        from app.agents.safety import INJECTION_PATTERNS
        assert any("BPA_FASE" in p for p in INJECTION_PATTERNS)

    def test_github_token_pattern_existe(self):
        from app.agents.safety import INJECTION_PATTERNS
        assert any("ghp_" in p for p in INJECTION_PATTERNS)

    def test_openai_pattern_existe(self):
        from app.agents.safety import INJECTION_PATTERNS
        assert any("sk-" in p for p in INJECTION_PATTERNS)

    def test_al_menos_5_patterns(self):
        from app.agents.safety import INJECTION_PATTERNS
        assert len(INJECTION_PATTERNS) >= 5


class TestFaseToken:
    def test_fase_token_existe(self):
        from app.agents.safety import FASE_TOKEN
        assert FASE_TOKEN is not None

    def test_fase_token_es_string(self):
        from app.agents.safety import FASE_TOKEN
        assert isinstance(FASE_TOKEN, str)

    def test_fase_token_no_vacio(self):
        from app.agents.safety import FASE_TOKEN
        assert len(FASE_TOKEN) > 0

    def test_fase_token_contiene_bpa(self):
        from app.agents.safety import FASE_TOKEN
        assert "BPA" in FASE_TOKEN

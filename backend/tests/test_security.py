"""
test_security.py — Tests para sanitización, blacklist JWT y validación de passwords.
"""
import time
import pytest
from app.security.sanitize import limpiar_input, limpiar_nombre, limpiar_email, validar_password
from app.security.token_blacklist import TokenBlacklist


# ── Sanitize ──────────────────────────────────────────────────────────────────

class TestLimpiarInput:
    def test_elimina_script_tag(self):
        result = limpiar_input('<script>alert("xss")</script>hola')
        assert "<script>" not in result
        assert "hola" in result

    def test_elimina_html_tags(self):
        result = limpiar_input("<b>negrita</b> y <i>cursiva</i>")
        assert "<b>" not in result
        assert "negrita" in result

    def test_elimina_null_bytes(self):
        result = limpiar_input("hola\x00mundo")
        assert "\x00" not in result
        assert "holamundo" in result

    def test_trunca_a_max_len(self):
        long_text = "a" * 5000
        result = limpiar_input(long_text, max_len=100)
        assert len(result) == 100

    def test_normaliza_html_entities(self):
        result = limpiar_input("&amp; &lt; &gt;")
        assert "&amp;" not in result

    def test_texto_normal_sin_cambios(self):
        texto = "Crea un proceso de facturación"
        result = limpiar_input(texto)
        assert "facturación" in result

    def test_input_no_string_devuelve_vacio(self):
        assert limpiar_input(None) == ""
        assert limpiar_input(123) == ""


class TestLimpiarNombre:
    def test_elimina_saltos_de_linea(self):
        result = limpiar_nombre("Proceso\nde facturación")
        assert "\n" not in result

    def test_colapsa_espacios(self):
        result = limpiar_nombre("Mi   Empresa   SL")
        assert "   " not in result

    def test_trunca_a_255(self):
        result = limpiar_nombre("a" * 300)
        assert len(result) <= 255

    def test_strip_espacios(self):
        assert limpiar_nombre("  Mi Empresa  ") == "Mi Empresa"


class TestLimpiarEmail:
    def test_lowercase(self):
        assert limpiar_email("Test@BPA.COM") == "test@bpa.com"

    def test_strip(self):
        assert limpiar_email("  user@example.com  ") == "user@example.com"

    def test_trunca_a_254(self):
        long = "a" * 250 + "@b.com"
        assert len(limpiar_email(long)) <= 254


class TestValidarPassword:
    def test_password_valida(self):
        assert validar_password("Strong1pass") == []

    def test_demasiado_corta(self):
        errors = validar_password("Ab1")
        assert any("8" in e for e in errors)

    def test_sin_mayuscula(self):
        errors = validar_password("nomayu1scula")
        assert any("mayúscula" in e for e in errors)

    def test_sin_minuscula(self):
        errors = validar_password("NOMINUSCULA1")
        assert any("minúscula" in e for e in errors)

    def test_sin_numero(self):
        errors = validar_password("SinNumeroPass")
        assert any("número" in e for e in errors)

    def test_multiples_errores(self):
        errors = validar_password("abc")
        assert len(errors) >= 2


# ── Token Blacklist ───────────────────────────────────────────────────────────

class TestTokenBlacklist:
    def test_token_no_revocado_inicialmente(self):
        bl = TokenBlacklist()
        assert bl.is_revoked("non-existent-jti") is False

    def test_revocar_y_verificar(self):
        bl = TokenBlacklist()
        bl.revoke("jti-abc", time.time() + 3600)
        assert bl.is_revoked("jti-abc") is True

    def test_token_expirado_no_esta_revocado(self):
        bl = TokenBlacklist()
        bl.revoke("jti-expired", time.time() - 1)  # ya expiró
        assert bl.is_revoked("jti-expired") is False

    def test_tokens_distintos_independientes(self):
        bl = TokenBlacklist()
        bl.revoke("jti-1", time.time() + 3600)
        assert bl.is_revoked("jti-1") is True
        assert bl.is_revoked("jti-2") is False

    def test_size(self):
        bl = TokenBlacklist()
        bl.revoke("jti-x", time.time() + 3600)
        bl.revoke("jti-y", time.time() + 3600)
        assert bl.size() == 2

    def test_cleanup_expira_tokens(self):
        bl = TokenBlacklist()
        bl.revoke("jti-a", time.time() - 10)  # expirado
        bl.revoke("jti-b", time.time() + 3600)  # válido
        # is_revoked hace cleanup
        bl.is_revoked("jti-a")
        bl.is_revoked("jti-b")
        assert bl.size() == 1

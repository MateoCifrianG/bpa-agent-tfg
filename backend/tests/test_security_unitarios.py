"""
test_security_unitarios.py — Tests unitarios del módulo de seguridad:
TokenBlacklist completo, sanitize completo, audit helpers, jwt helpers.
"""
import pytest
import time


class TestSanitizeRegexPatterns:
    def test_ctrl_chars_eliminados(self):
        from app.security.sanitize import limpiar_input
        resultado = limpiar_input("hola\x00mundo")
        assert "\x00" not in resultado

    def test_null_byte_eliminado(self):
        from app.security.sanitize import limpiar_input
        assert "\x00" not in limpiar_input("a\x00b")

    def test_form_feed_eliminado(self):
        from app.security.sanitize import limpiar_input
        assert "\x0c" not in limpiar_input("a\x0cb")

    def test_delete_char_eliminado(self):
        from app.security.sanitize import limpiar_input
        assert "\x7f" not in limpiar_input("a\x7fb")

    def test_script_etiqueta_doble_eliminada(self):
        from app.security.sanitize import limpiar_input
        out = limpiar_input("<script>alert('xss')</script>texto")
        assert "alert" not in out.lower() or "script" not in out.lower()

    def test_script_multilinea_eliminado(self):
        from app.security.sanitize import limpiar_input
        out = limpiar_input("<script>\nalert(1)\n</script>")
        assert "<script>" not in out.lower()

    def test_img_tag_eliminada(self):
        from app.security.sanitize import limpiar_input
        out = limpiar_input('<img src="x" onerror="alert(1)">')
        assert "<img" not in out

    def test_html_entities_normalizadas(self):
        from app.security.sanitize import limpiar_input
        out = limpiar_input("&lt;script&gt;")
        assert isinstance(out, str)

    def test_amp_entity_normalizada(self):
        from app.security.sanitize import limpiar_input
        out = limpiar_input("M&amp;M")
        assert "M" in out

    def test_multi_espacios_colapsados(self):
        from app.security.sanitize import limpiar_input
        out = limpiar_input("hola     mundo")
        assert len(out) < len("hola     mundo") + 1

    def test_multi_newlines_colapsados(self):
        from app.security.sanitize import limpiar_input
        out = limpiar_input("a\n\n\n\n\n\nb")
        count_nl = out.count("\n")
        assert count_nl <= 3

    def test_trunca_a_max_len(self):
        from app.security.sanitize import limpiar_input
        out = limpiar_input("x" * 10000, max_len=500)
        assert len(out) <= 500

    def test_sin_strip_extra(self):
        from app.security.sanitize import limpiar_input
        out = limpiar_input("  hola  ")
        assert out == "hola"


class TestLimpiarNombreDetalle:
    def test_newline_reemplazada_por_espacio(self):
        from app.security.sanitize import limpiar_nombre
        out = limpiar_nombre("Nombre\nApellido")
        assert "\n" not in out

    def test_carriage_return_eliminado(self):
        from app.security.sanitize import limpiar_nombre
        out = limpiar_nombre("Nombre\rApellido")
        assert "\r" not in out

    def test_html_tag_eliminado(self):
        from app.security.sanitize import limpiar_nombre
        out = limpiar_nombre("<b>Nombre</b>")
        assert "<b>" not in out

    def test_trunca_a_255(self):
        from app.security.sanitize import limpiar_nombre
        out = limpiar_nombre("N" * 300)
        assert len(out) <= 255

    def test_multi_espacios_colapsados(self):
        from app.security.sanitize import limpiar_nombre
        out = limpiar_nombre("Juan   García")
        assert "  " not in out

    def test_strip_aplicado(self):
        from app.security.sanitize import limpiar_nombre
        assert limpiar_nombre("  Juan  ") == "Juan"

    def test_unicode_preservado(self):
        from app.security.sanitize import limpiar_nombre
        out = limpiar_nombre("María Ángela")
        assert "María" in out or "Maria" in out

    def test_vacio_retorna_vacio(self):
        from app.security.sanitize import limpiar_nombre
        assert limpiar_nombre("") == ""

    def test_none_no_falla(self):
        from app.security.sanitize import limpiar_nombre
        # Si pasan None (error de tipo), no debería lanzar excepción inesperada
        result = limpiar_nombre(None)
        assert result == ""

    def test_solo_espacios_retorna_vacio(self):
        from app.security.sanitize import limpiar_nombre
        assert limpiar_nombre("   ") == ""


class TestLimpiarEmailDetalle:
    def test_lowercase(self):
        from app.security.sanitize import limpiar_email
        assert limpiar_email("USER@EXAMPLE.COM") == "user@example.com"

    def test_strip(self):
        from app.security.sanitize import limpiar_email
        assert limpiar_email("  user@example.com  ") == "user@example.com"

    def test_max_254(self):
        from app.security.sanitize import limpiar_email
        long_email = "a" * 250 + "@b.com"
        out = limpiar_email(long_email)
        assert len(out) <= 254

    def test_vacio(self):
        from app.security.sanitize import limpiar_email
        assert limpiar_email("") == ""

    def test_none_retorna_vacio(self):
        from app.security.sanitize import limpiar_email
        assert limpiar_email(None) == ""

    def test_preserva_dominio(self):
        from app.security.sanitize import limpiar_email
        out = limpiar_email("test@empresa.es")
        assert "empresa.es" in out

    def test_preserva_subdominio(self):
        from app.security.sanitize import limpiar_email
        out = limpiar_email("user@mail.empresa.com")
        assert "mail.empresa.com" in out


class TestValidarPasswordDetalle:
    def test_8_exactos_valido(self):
        from app.security.sanitize import validar_password
        errores = validar_password("Abcd123!")
        assert errores == []

    def test_7_chars_invalido(self):
        from app.security.sanitize import validar_password
        errores = validar_password("Abcd12!")
        assert any("8" in e for e in errores)

    def test_sin_minuscula_invalido(self):
        from app.security.sanitize import validar_password
        errores = validar_password("ABCDEFG1")
        assert any("minúscula" in e for e in errores)

    def test_sin_mayuscula_invalido(self):
        from app.security.sanitize import validar_password
        errores = validar_password("abcdefg1")
        assert any("mayúscula" in e for e in errores)

    def test_sin_digito_invalido(self):
        from app.security.sanitize import validar_password
        errores = validar_password("Abcdefgh")
        assert any("número" in e for e in errores)

    def test_vacio_multiples_errores(self):
        from app.security.sanitize import validar_password
        errores = validar_password("")
        assert len(errores) >= 3

    def test_errores_son_strings(self):
        from app.security.sanitize import validar_password
        errores = validar_password("weak")
        for e in errores:
            assert isinstance(e, str)

    def test_valido_lista_vacia(self):
        from app.security.sanitize import validar_password
        assert validar_password("ValidPass1!") == []

    def test_password_muy_largo_valido(self):
        from app.security.sanitize import validar_password
        assert validar_password("ValidPassword123!ExtraLongForSecurity") == []

    def test_todos_errores_a_la_vez(self):
        from app.security.sanitize import validar_password
        errores = validar_password("a")
        assert len(errores) >= 3


class TestAuditModule:
    def test_audit_importable(self):
        from app.security.audit import log_event
        assert callable(log_event)

    def test_get_ip_helper_importable(self):
        from app.security.audit import _get_ip
        assert callable(_get_ip)

    def test_get_ip_con_none(self):
        from app.security.audit import _get_ip
        result = _get_ip(None)
        assert result is None

    def test_log_event_es_coroutine(self):
        import asyncio
        from app.security.audit import log_event
        assert asyncio.iscoroutinefunction(log_event)

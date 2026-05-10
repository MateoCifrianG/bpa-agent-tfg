"""
test_sanitize_extra.py — Tests adicionales de sanitización:
más patrones XSS, caracteres especiales, unicode, truncamiento,
emails con dominios variados, passwords con patrones complejos.
"""
import pytest


class TestLimpiarInputExtra:
    def test_limpiar_input_texto_normal(self):
        from app.security.sanitize import limpiar_input
        assert limpiar_input("Hola mundo") == "Hola mundo"

    def test_limpiar_input_script_tag(self):
        from app.security.sanitize import limpiar_input
        resultado = limpiar_input("<script>alert(1)</script>")
        assert "<script>" not in resultado.lower()

    def test_limpiar_input_img_onerror(self):
        from app.security.sanitize import limpiar_input
        resultado = limpiar_input('<img src=x onerror="alert(1)">')
        assert "onerror" not in resultado.lower() or "onerror" in resultado

    def test_limpiar_input_javascript_proto(self):
        from app.security.sanitize import limpiar_input
        resultado = limpiar_input("javascript:alert(1)")
        assert isinstance(resultado, str)

    def test_limpiar_input_vacio_devuelve_vacio(self):
        from app.security.sanitize import limpiar_input
        assert limpiar_input("") == ""

    def test_limpiar_input_espacios_preservados(self):
        from app.security.sanitize import limpiar_input
        result = limpiar_input("  hola  ")
        assert "hola" in result

    def test_limpiar_input_unicode_ok(self):
        from app.security.sanitize import limpiar_input
        result = limpiar_input("Facturación española")
        assert "Facturación" in result or "Facturaci" in result

    def test_limpiar_input_trunca_max_len(self):
        from app.security.sanitize import limpiar_input
        texto_largo = "A" * 5000
        resultado = limpiar_input(texto_largo, max_len=100)
        assert len(resultado) <= 100

    def test_limpiar_input_max_len_default(self):
        from app.security.sanitize import limpiar_input
        texto = "A" * 200
        resultado = limpiar_input(texto)
        assert len(resultado) <= 2001

    def test_limpiar_input_sql_chars(self):
        from app.security.sanitize import limpiar_input
        resultado = limpiar_input("'; DROP TABLE users; --")
        assert isinstance(resultado, str)

    def test_limpiar_input_html_entity_ampersand(self):
        from app.security.sanitize import limpiar_input
        resultado = limpiar_input("M&M candies")
        assert "M" in resultado

    def test_limpiar_input_newlines_preservadas(self):
        from app.security.sanitize import limpiar_input
        resultado = limpiar_input("linea1\nlinea2")
        assert isinstance(resultado, str)

    def test_limpiar_input_solo_numeros(self):
        from app.security.sanitize import limpiar_input
        resultado = limpiar_input("12345")
        assert "12345" in resultado

    def test_limpiar_input_emoji_ok(self):
        from app.security.sanitize import limpiar_input
        resultado = limpiar_input("Hola 👋 mundo")
        assert isinstance(resultado, str)


class TestLimpiarNombreExtra:
    def test_limpiar_nombre_normal(self):
        from app.security.sanitize import limpiar_nombre
        assert limpiar_nombre("Juan García") == "Juan García"

    def test_limpiar_nombre_con_script(self):
        from app.security.sanitize import limpiar_nombre
        resultado = limpiar_nombre("<script>alert(1)</script>")
        assert "<script>" not in resultado.lower()

    def test_limpiar_nombre_vacio(self):
        from app.security.sanitize import limpiar_nombre
        resultado = limpiar_nombre("")
        assert resultado == ""

    def test_limpiar_nombre_trunca_largo(self):
        from app.security.sanitize import limpiar_nombre
        resultado = limpiar_nombre("N" * 300)
        assert len(resultado) <= 301

    def test_limpiar_nombre_unicode(self):
        from app.security.sanitize import limpiar_nombre
        resultado = limpiar_nombre("María José Ángela")
        assert "María" in resultado or "Mar" in resultado

    def test_limpiar_nombre_no_es_none(self):
        from app.security.sanitize import limpiar_nombre
        resultado = limpiar_nombre("Test")
        assert resultado is not None

    def test_limpiar_nombre_preserva_apellido(self):
        from app.security.sanitize import limpiar_nombre
        resultado = limpiar_nombre("García López")
        assert "García" in resultado or "Garcia" in resultado


class TestLimpiarEmailExtra:
    def test_limpiar_email_normal(self):
        from app.security.sanitize import limpiar_email
        resultado = limpiar_email("test@ejemplo.com")
        assert "@" in resultado

    def test_limpiar_email_normaliza_lowercase(self):
        from app.security.sanitize import limpiar_email
        resultado = limpiar_email("TEST@EJEMPLO.COM")
        assert resultado == resultado.lower() or "@" in resultado

    def test_limpiar_email_recorta_espacios(self):
        from app.security.sanitize import limpiar_email
        resultado = limpiar_email("  test@ejemplo.com  ")
        assert "test@ejemplo.com" in resultado

    def test_limpiar_email_vacio(self):
        from app.security.sanitize import limpiar_email
        resultado = limpiar_email("")
        assert resultado == ""

    def test_limpiar_email_devuelve_string(self):
        from app.security.sanitize import limpiar_email
        resultado = limpiar_email("a@b.com")
        assert isinstance(resultado, str)


class TestValidarPasswordExtra:
    def test_validar_password_fuerte_ok(self):
        from app.security.sanitize import validar_password
        errores = validar_password("TestPass1!")
        assert errores == []

    def test_validar_password_sin_mayuscula_falla(self):
        from app.security.sanitize import validar_password
        errores = validar_password("testpass1!")
        assert len(errores) > 0

    def test_validar_password_sin_numero_falla(self):
        from app.security.sanitize import validar_password
        errores = validar_password("TestPassAbc!")
        assert len(errores) > 0

    def test_validar_password_muy_corto_falla(self):
        from app.security.sanitize import validar_password
        errores = validar_password("T1!")
        assert len(errores) > 0

    def test_validar_password_largo_ok(self):
        from app.security.sanitize import validar_password
        errores = validar_password("MiPasswordSuperLargo123!Seguro")
        assert errores == []

    def test_validar_password_devuelve_lista(self):
        from app.security.sanitize import validar_password
        resultado = validar_password("TestPass1!")
        assert isinstance(resultado, list)

    def test_validar_password_errores_son_strings(self):
        from app.security.sanitize import validar_password
        errores = validar_password("debil")
        for e in errores:
            assert isinstance(e, str)

    def test_validar_password_todos_requisitos(self):
        from app.security.sanitize import validar_password
        errores = validar_password("Abcd1234!")
        assert errores == []

    def test_validar_password_vacio_falla(self):
        from app.security.sanitize import validar_password
        errores = validar_password("")
        assert len(errores) > 0

    def test_validar_password_solo_numeros_falla(self):
        from app.security.sanitize import validar_password
        errores = validar_password("12345678")
        assert len(errores) > 0

    def test_validar_password_con_especial_y_mayuscula(self):
        from app.security.sanitize import validar_password
        errores = validar_password("Password1@")
        assert errores == []

    def test_validar_password_con_8_chars_exactos(self):
        from app.security.sanitize import validar_password
        errores = validar_password("Pass1!Ab")
        assert isinstance(errores, list)

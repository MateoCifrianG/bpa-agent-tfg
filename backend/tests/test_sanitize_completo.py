"""
test_sanitize_completo.py — Tests exhaustivos de todas las funciones de sanitización:
limpiar_input, limpiar_nombre, limpiar_email, validar_password.
Cubre XSS, null bytes, caracteres de control, encoding, límites, edge cases.
"""
import pytest
from app.security.sanitize import limpiar_input, limpiar_nombre, limpiar_email, validar_password


# ── limpiar_input ──────────────────────────────────────────────────────────────

class TestLimpiarInputXSS:
    def test_elimina_script_basico(self):
        r = limpiar_input("<script>alert(1)</script>hola")
        assert "<script>" not in r

    def test_elimina_script_con_atributos(self):
        r = limpiar_input("<script type='text/javascript'>evil()</script>")
        assert "<script" not in r

    def test_elimina_script_mayusculas(self):
        r = limpiar_input("<SCRIPT>alert(1)</SCRIPT>")
        assert "<SCRIPT" not in r

    def test_elimina_script_mixto(self):
        r = limpiar_input("<ScRiPt>alert('xss')</ScRiPt>")
        assert "<ScRiPt" not in r

    def test_elimina_img_onerror(self):
        r = limpiar_input('<img src=x onerror=alert(1)>')
        assert "<img" not in r

    def test_elimina_iframe(self):
        r = limpiar_input('<iframe src="evil.html"></iframe>')
        assert "<iframe" not in r

    def test_elimina_link_stylesheet(self):
        r = limpiar_input('<link rel="stylesheet" href="evil.css">')
        assert "<link" not in r

    def test_elimina_svg_con_evento(self):
        r = limpiar_input('<svg onload=alert(1)>')
        assert "<svg" not in r

    def test_elimina_object_tag(self):
        r = limpiar_input('<object data="evil.swf"></object>')
        assert "<object" not in r

    def test_elimina_form_action(self):
        r = limpiar_input('<form action="steal.php"><input></form>')
        assert "<form" not in r

    def test_preserva_texto_normal(self):
        r = limpiar_input("hola mundo qué tal")
        assert "hola mundo" in r

    def test_preserva_texto_con_numeros(self):
        r = limpiar_input("proceso 123 del año 2024")
        assert "proceso" in r
        assert "123" in r

    def test_preserva_acentos(self):
        r = limpiar_input("facturación de clientes españoles")
        assert "facturación" in r
        assert "españoles" in r

    def test_elimina_html_b_tag(self):
        r = limpiar_input("<b>negrita</b>")
        assert "<b>" not in r
        assert "negrita" in r

    def test_elimina_html_i_tag(self):
        r = limpiar_input("<i>cursiva</i>")
        assert "<i>" not in r

    def test_elimina_html_div(self):
        r = limpiar_input("<div class='x'>contenido</div>")
        assert "<div" not in r
        assert "contenido" in r

    def test_elimina_html_p_tag(self):
        r = limpiar_input("<p>párrafo</p>")
        assert "<p>" not in r

    def test_elimina_html_span(self):
        r = limpiar_input("<span style='color:red'>texto</span>")
        assert "<span" not in r


class TestLimpiarInputCaracteresControl:
    def test_elimina_null_byte(self):
        r = limpiar_input("hola\x00mundo")
        assert "\x00" not in r

    def test_elimina_null_bytes_multiples(self):
        r = limpiar_input("\x00\x00abc\x00")
        assert "\x00" not in r

    def test_elimina_ctrl_a(self):
        r = limpiar_input("texto\x01aqui")
        assert "\x01" not in r

    def test_elimina_ctrl_b(self):
        r = limpiar_input("a\x02b")
        assert "\x02" not in r

    def test_elimina_ctrl_g_bell(self):
        r = limpiar_input("texto\x07aqui")
        assert "\x07" not in r

    def test_elimina_ctrl_backspace(self):
        r = limpiar_input("a\x08b")
        assert "\x08" not in r

    def test_preserva_tab(self):
        # Tab (\x09) puede ser preservado
        r = limpiar_input("col1\tcol2")
        assert "col1" in r
        assert "col2" in r

    def test_preserva_newline(self):
        r = limpiar_input("línea1\nlínea2")
        assert "línea1" in r
        assert "línea2" in r

    def test_elimina_ctrl_k(self):
        r = limpiar_input("a\x0bb")
        assert "\x0b" not in r

    def test_elimina_ctrl_c(self):
        r = limpiar_input("text\x0chere")
        assert "\x0c" not in r

    def test_preserva_carriage_return(self):
        # \r puede o no preservarse según implementación
        r = limpiar_input("línea\r\n")
        assert "línea" in r

    def test_elimina_ctrl_n_o_m(self):
        r = limpiar_input("a\x0eb")
        assert "\x0e" not in r

    def test_elimina_ctrl_1f(self):
        r = limpiar_input("a\x1fb")
        assert "\x1f" not in r

    def test_elimina_delete_char(self):
        r = limpiar_input("a\x7fb")
        assert "\x7f" not in r


class TestLimpiarInputHtmlEntities:
    def test_normaliza_amp(self):
        r = limpiar_input("&amp;")
        assert "&amp;" not in r

    def test_normaliza_lt(self):
        r = limpiar_input("&lt;b&gt;")
        assert "&lt;" not in r

    def test_normaliza_gt(self):
        r = limpiar_input("&gt;")
        assert "&gt;" not in r

    def test_normaliza_quot(self):
        r = limpiar_input("&quot;")
        assert "&quot;" not in r

    def test_normaliza_apos(self):
        r = limpiar_input("&apos;")
        assert "&apos;" not in r

    def test_normaliza_nbsp(self):
        r = limpiar_input("&nbsp;")
        assert "&nbsp;" not in r


class TestLimpiarInputLimites:
    def test_trunca_al_max_len(self):
        r = limpiar_input("a" * 5000, max_len=100)
        assert len(r) == 100

    def test_no_trunca_si_menor(self):
        texto = "texto corto"
        r = limpiar_input(texto, max_len=1000)
        assert "texto corto" in r

    def test_max_len_default_4000(self):
        r = limpiar_input("a" * 5000)
        assert len(r) <= 4000

    def test_cadena_vacia(self):
        r = limpiar_input("")
        assert r == ""

    def test_solo_espacios(self):
        r = limpiar_input("   ")
        assert r == ""

    def test_none_devuelve_vacio(self):
        r = limpiar_input(None)
        assert r == ""

    def test_int_devuelve_vacio(self):
        r = limpiar_input(123)
        assert r == ""

    def test_lista_devuelve_vacio(self):
        r = limpiar_input(["a", "b"])
        assert r == ""

    def test_dict_devuelve_vacio(self):
        r = limpiar_input({"key": "val"})
        assert r == ""


class TestLimpiarInputEspacios:
    def test_colapsa_multiples_espacios(self):
        r = limpiar_input("hola      mundo")
        assert "hola" in r
        assert "mundo" in r
        # No debe haber más de 2 espacios consecutivos
        assert "   " not in r

    def test_colapsa_multiples_newlines(self):
        r = limpiar_input("a\n\n\n\n\n\nb")
        assert "a" in r
        assert "b" in r
        # No debe haber más de 3 newlines consecutivos
        assert "\n\n\n\n" not in r

    def test_strip_espacios_inicial_final(self):
        r = limpiar_input("   texto   ")
        assert r == "texto"


# ── limpiar_nombre ──────────────────────────────────────────────────────────────

class TestLimpiarNombreBasico:
    def test_nombre_normal(self):
        r = limpiar_nombre("Proceso de Facturación")
        assert r == "Proceso de Facturación"

    def test_elimina_html(self):
        r = limpiar_nombre("<b>nombre</b>")
        assert "<b>" not in r
        assert "nombre" in r

    def test_elimina_newlines(self):
        r = limpiar_nombre("nombre\ncon\nnewline")
        assert "\n" not in r

    def test_elimina_carriage_return(self):
        r = limpiar_nombre("nombre\raquí")
        assert "\r" not in r

    def test_trunca_a_255(self):
        r = limpiar_nombre("A" * 300)
        assert len(r) <= 255

    def test_trunca_a_max_len_personalizado(self):
        r = limpiar_nombre("A" * 100, max_len=50)
        assert len(r) <= 50

    def test_strip_espacios(self):
        r = limpiar_nombre("  nombre con espacios  ")
        assert r == "nombre con espacios"

    def test_preserva_acentos(self):
        r = limpiar_nombre("Gestión de Nóminas")
        assert "Gestión" in r
        assert "Nóminas" in r

    def test_preserva_eñe(self):
        r = limpiar_nombre("España")
        assert "España" in r

    def test_none_devuelve_vacio(self):
        r = limpiar_nombre(None)
        assert r == ""

    def test_int_devuelve_vacio(self):
        r = limpiar_nombre(42)
        assert r == ""

    def test_cadena_vacia(self):
        r = limpiar_nombre("")
        assert r == ""

    def test_elimina_script_inline(self):
        r = limpiar_nombre("nombre <script>alert(1)</script>")
        assert "<script" not in r

    def test_elimina_null_bytes(self):
        r = limpiar_nombre("proc\x00eso")
        assert "\x00" not in r

    def test_colapsa_multiples_espacios(self):
        r = limpiar_nombre("nombre    con    espacios")
        assert "    " not in r

    def test_nombre_con_parentesis(self):
        r = limpiar_nombre("Proceso (mensual) de facturación")
        assert "(" in r
        assert ")" in r

    def test_nombre_con_guion(self):
        r = limpiar_nombre("Proceso A-B")
        assert "-" in r

    def test_nombre_con_slash(self):
        r = limpiar_nombre("Entrada/Salida de almacén")
        assert "/" in r

    def test_nombre_con_numeros(self):
        r = limpiar_nombre("Proceso 123 del mes")
        assert "123" in r

    def test_nombre_con_emoji(self):
        # Los emojis deben preservarse o al menos no crashear
        r = limpiar_nombre("Proceso ✅ completado")
        assert "completado" in r


# ── limpiar_email ───────────────────────────────────────────────────────────────

class TestLimpiarEmail:
    def test_lowercase(self):
        assert limpiar_email("USUARIO@EMPRESA.COM") == "usuario@empresa.com"

    def test_strip_espacios(self):
        assert limpiar_email("  user@test.com  ") == "user@test.com"

    def test_preserva_email_valido(self):
        assert limpiar_email("user@empresa.com") == "user@empresa.com"

    def test_trunca_a_254(self):
        email_largo = "a" * 200 + "@empresa.com"
        r = limpiar_email(email_largo)
        assert len(r) <= 254

    def test_lowercase_y_strip_combinados(self):
        assert limpiar_email("  ADMIN@BPA.COM  ") == "admin@bpa.com"

    def test_none_devuelve_vacio(self):
        assert limpiar_email(None) == ""

    def test_int_devuelve_vacio(self):
        assert limpiar_email(123) == ""

    def test_email_con_punto_en_local(self):
        assert limpiar_email("user.name@empresa.com") == "user.name@empresa.com"

    def test_email_con_subdominio(self):
        assert limpiar_email("user@mail.empresa.es") == "user@mail.empresa.es"

    def test_email_con_plus(self):
        assert limpiar_email("user+tag@empresa.com") == "user+tag@empresa.com"

    def test_cadena_vacia(self):
        assert limpiar_email("") == ""

    def test_solo_espacios(self):
        assert limpiar_email("   ") == ""

    def test_email_mayusculas_mixtas(self):
        assert limpiar_email("User.Name@Empresa.ES") == "user.name@empresa.es"


# ── validar_password ────────────────────────────────────────────────────────────

class TestValidarPassword:
    def test_password_correcta(self):
        errors = validar_password("TestPass1!")
        assert errors == []

    def test_password_correcta_sin_especial(self):
        errors = validar_password("TestPass123")
        assert errors == []

    def test_muy_corta(self):
        errors = validar_password("Ab1")
        assert len(errors) > 0
        assert any("caracteres" in e.lower() for e in errors)

    def test_exactamente_8_chars(self):
        errors = validar_password("TestPa1!")
        assert errors == []

    def test_exactamente_7_chars_falla(self):
        errors = validar_password("TestP1!")
        assert len(errors) > 0

    def test_sin_mayuscula(self):
        errors = validar_password("sinmayuscula1!")
        assert any("mayúscula" in e for e in errors)

    def test_sin_minuscula(self):
        errors = validar_password("SINMINUSCULA1!")
        assert any("minúscula" in e for e in errors)

    def test_sin_numero(self):
        errors = validar_password("SinNumeroAqui!")
        assert any("número" in e for e in errors)

    def test_todos_mayusculas(self):
        errors = validar_password("TODOSMAS")
        assert len(errors) > 0  # sin minúscula y sin número

    def test_todos_numeros(self):
        errors = validar_password("12345678")
        assert len(errors) > 0  # sin mayúscula ni minúscula

    def test_solo_minusculas(self):
        errors = validar_password("solominusculas")
        assert len(errors) > 0

    def test_con_espacios(self):
        # Espacios no están prohibidos, solo se evalúan los requisitos
        errors = validar_password("Test Pass 1!")
        # Tiene mayúscula, minúscula, número, 10 chars
        assert errors == []

    def test_password_larga_valida(self):
        errors = validar_password("MiPasswordMuyLargoConNumero123YCaracteresEspeciales!")
        assert errors == []

    def test_vacia_tiene_multiples_errores(self):
        errors = validar_password("")
        assert len(errors) >= 3  # longitud, mayúscula, minúscula, número

    def test_solo_un_char(self):
        errors = validar_password("A")
        assert len(errors) > 0

    def test_password_con_unicode(self):
        errors = validar_password("Contraseña1!")
        assert errors == []

    def test_password_con_simbolos_varios(self):
        errors = validar_password("Test@2024#Pass$")
        assert errors == []

    def test_errores_son_lista(self):
        errors = validar_password("abc")
        assert isinstance(errors, list)

    def test_errores_son_strings(self):
        errors = validar_password("abc")
        for e in errors:
            assert isinstance(e, str)

    def test_pass_correcta_devuelve_lista_vacia(self):
        errors = validar_password("MiPass123")
        assert isinstance(errors, list)
        assert len(errors) == 0

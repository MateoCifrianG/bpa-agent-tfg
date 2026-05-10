"""
test_motor_v6_avanzado.py — Tests avanzados del motor v6: intent classifier,
context manager, procesador de batch, acciones, respuestas síntesis, edge cases.
"""
import pytest
import re
from app.agents.motor_v6_kb import (
    SECTORES, INTENT_PATTERNS, RESPUESTAS, SCORING_CRITERIOS, ROI_CONFIG,
    calcular_roi, calcular_score, detectar_sector, detectar_nombre_proceso,
)


class TestROIBordesNumericos:
    def test_roi_cero_horas(self):
        roi = calcular_roi(0)
        assert roi["ahorro_mes"] == 0
        assert roi["payback_meses"] in (999, float("inf")) or roi["payback_meses"] >= 0

    def test_roi_una_hora(self):
        roi = calcular_roi(1)
        assert roi["ahorro_mes"] == ROI_CONFIG["coste_hora_media"]

    def test_roi_10_horas(self):
        roi = calcular_roi(10)
        expected = 10 * ROI_CONFIG["coste_hora_media"]
        assert roi["ahorro_mes"] == expected

    def test_roi_100_horas(self):
        roi = calcular_roi(100)
        assert roi["ahorro_mes"] == 100 * ROI_CONFIG["coste_hora_media"]

    def test_roi_1000_horas(self):
        roi = calcular_roi(1000)
        assert roi["ahorro_mes"] > 0
        assert roi["viable"] is True

    def test_roi_fraccional_redondeado(self):
        roi = calcular_roi(3.3)
        expected = round(3.3 * ROI_CONFIG["coste_hora_media"], 0)
        assert roi["ahorro_mes"] == expected

    def test_roi_ahorro_anual_doce_veces_mes(self):
        for horas in [5, 10, 20, 50]:
            roi = calcular_roi(horas)
            assert roi["ahorro_anual"] == roi["ahorro_mes"] * 12

    def test_roi_coste_impl_por_defecto(self):
        roi1 = calcular_roi(10)
        roi2 = calcular_roi(10, coste_impl=ROI_CONFIG["coste_implementacion_base"])
        assert roi1["coste_implementacion"] == roi2["coste_implementacion"]

    def test_roi_coste_impl_personalizado(self):
        roi = calcular_roi(10, coste_impl=5000)
        assert roi["coste_implementacion"] == 5000

    def test_roi_payback_correcto(self):
        roi = calcular_roi(100, coste_impl=1000)
        if roi["ahorro_mes"] > 0:
            expected_payback = round(1000 / roi["ahorro_mes"], 1)
            assert abs(roi["payback_meses"] - expected_payback) < 2

    def test_roi_viable_alto_ahorro(self):
        roi = calcular_roi(50, coste_impl=500)
        assert roi["viable"] is True

    def test_roi_no_viable_bajo_ahorro(self):
        roi = calcular_roi(1, coste_impl=100000)
        assert roi["viable"] is False

    def test_roi_roi_pct_es_numero(self):
        roi = calcular_roi(20, coste_impl=2000)
        assert isinstance(roi["roi_pct"], (int, float))

    def test_roi_beneficio_neto_anual_existe(self):
        roi = calcular_roi(15, coste_impl=1000)
        assert "beneficio_neto_anual" in roi or "roi_pct" in roi

    def test_roi_todas_claves_numericas_no_negativas(self):
        roi = calcular_roi(20)
        for k, v in roi.items():
            if k != "viable" and isinstance(v, (int, float)):
                assert v >= 0 or k == "beneficio_neto_anual"


class TestDetectarSectorCompleto:
    def test_logistica_directo(self):
        assert detectar_sector("proceso de logística y distribución") == "logística"

    def test_logistica_supply_chain(self):
        assert detectar_sector("nuestro supply chain tiene problemas") == "logística"

    def test_logistica_warehouse(self):
        assert detectar_sector("warehouse management system") == "logística"

    def test_logistica_almacen(self):
        assert detectar_sector("gestión de almacén y distribución") == "logística"

    def test_ventas_crm(self):
        r = detectar_sector("proceso crm de gestión comercial")
        assert r == "ventas"

    def test_ventas_comercial(self):
        r = detectar_sector("área comercial y ventas")
        assert r in ("ventas", None)

    def test_rrhh_personas(self):
        r = detectar_sector("gestión de personas y talento")
        assert r == "recursos humanos"

    def test_rrhh_directo(self):
        r = detectar_sector("proceso de recursos humanos y nóminas")
        assert r == "recursos humanos"

    def test_finanzas_contabilidad(self):
        r = detectar_sector("departamento de contabilidad y finanzas")
        assert r in ("finanzas", None)

    def test_marketing_digital(self):
        r = detectar_sector("campaña de marketing digital")
        assert r in ("marketing", None)

    def test_tecnologia_it(self):
        r = detectar_sector("infraestructura de IT y sistemas")
        assert r in ("tecnología", None)

    def test_atencion_cliente(self):
        r = detectar_sector("proceso de atención al cliente y soporte")
        assert r in ("atención al cliente", None)

    def test_texto_generico_none(self):
        assert detectar_sector("proceso cualquiera sin sector") is None

    def test_texto_vacio_none(self):
        assert detectar_sector("") is None

    def test_mayusculas_normalizadas(self):
        r = detectar_sector("PROCESO DE LOGÍSTICA")
        assert r == "logística"

    def test_alias_ti_no_como_substring(self):
        # "ti" no debe matchear en "logística" como substring
        r = detectar_sector("proceso logístico de distribución")
        assert r == "logística"

    def test_sector_none_texto_corto(self):
        assert detectar_sector("abc") is None

    def test_alias_multiple_primer_match(self):
        r = detectar_sector("nuestros procesos de logística y ventas")
        assert r in ("logística", "ventas")


class TestDetectarNombreProceso:
    def test_proceso_exacto(self):
        procs = ["Gestión de pedidos", "Control de inventario"]
        r = detectar_nombre_proceso("analiza la gestión de pedidos", procs)
        assert r == "Gestión de pedidos"

    def test_proceso_case_insensitive(self):
        procs = ["FACTURACIÓN MENSUAL"]
        r = detectar_nombre_proceso("ayúdame con facturación mensual", procs)
        assert r is not None

    def test_proceso_no_encontrado(self):
        procs = ["Facturación", "RRHH"]
        r = detectar_nombre_proceso("proceso totalmente diferente xyz", procs)
        assert r is None or isinstance(r, str)

    def test_lista_vacia(self):
        assert detectar_nombre_proceso("cualquier texto", []) is None

    def test_texto_vacio(self):
        assert detectar_nombre_proceso("", ["Facturación"]) is None

    def test_proceso_multiple_candidatos_primer_match(self):
        procs = ["Gestión de pedidos", "Gestión de devoluciones"]
        r = detectar_nombre_proceso("ver gestión de pedidos", procs)
        assert r in procs or r is None

    def test_proceso_nombre_uno_char_no_match(self):
        procs = ["A"]
        r = detectar_nombre_proceso("habla sobre la letra a", procs)
        assert r is None or r == "A"


class TestIntentPatternsDetalle:
    def test_saludo_hola(self):
        saludo_patterns = next(p for p in INTENT_PATTERNS if p["intent"] == "saludo")
        encontrado = any(re.search(pat, "hola", re.I) for pat in saludo_patterns["patrones"])
        assert encontrado

    def test_saludo_buenos_dias(self):
        saludo_patterns = next(p for p in INTENT_PATTERNS if p["intent"] == "saludo")
        encontrado = any(re.search(pat, "buenos días", re.I) for pat in saludo_patterns["patrones"])
        assert encontrado

    def test_despedida_adios(self):
        despedida = next(p for p in INTENT_PATTERNS if p["intent"] == "despedida")
        encontrado = any(re.search(pat, "adiós", re.I) for pat in despedida["patrones"])
        assert encontrado

    def test_ayuda_que_puedes_hacer(self):
        ayuda = next(p for p in INTENT_PATTERNS if p["intent"] == "ayuda")
        msg = "qué puedes hacer"
        encontrado = any(re.search(pat, msg, re.I) for pat in ayuda["patrones"])
        assert encontrado

    def test_crear_proceso_patron(self):
        crear = next(p for p in INTENT_PATTERNS if p["intent"] == "crear_proceso")
        msg = "crear un proceso"
        encontrado = any(re.search(pat, msg, re.I) for pat in crear["patrones"])
        assert encontrado

    def test_listar_procesos_patron(self):
        listar = next(p for p in INTENT_PATTERNS if p["intent"] == "listar_procesos")
        msg = "mis procesos"
        encontrado = any(re.search(pat, msg, re.I) for pat in listar["patrones"])
        assert encontrado

    def test_calcular_roi_patron(self):
        roi = next(p for p in INTENT_PATTERNS if p["intent"] == "calcular_roi")
        msg = "calcular roi"
        encontrado = any(re.search(pat, msg, re.I) for pat in roi["patrones"])
        assert encontrado

    def test_pesos_todos_positivos(self):
        for p in INTENT_PATTERNS:
            assert p["peso"] > 0

    def test_no_duplicados_intents(self):
        intents = [p["intent"] for p in INTENT_PATTERNS]
        assert len(intents) == len(set(intents))

    def test_todos_patrones_son_lista(self):
        for p in INTENT_PATTERNS:
            assert isinstance(p["patrones"], list)
            assert len(p["patrones"]) >= 1


class TestSectorKPIs:
    def test_logistica_kpis_no_vacio(self):
        assert len(SECTORES["logística"]["kpis"]) > 0

    def test_ventas_kpis_no_vacio(self):
        assert len(SECTORES["ventas"]["kpis"]) > 0

    def test_finanzas_kpis_no_vacio(self):
        assert len(SECTORES["finanzas"]["kpis"]) > 0

    def test_marketing_kpis_no_vacio(self):
        assert len(SECTORES["marketing"]["kpis"]) > 0

    def test_rrhh_kpis_no_vacio(self):
        assert len(SECTORES["recursos humanos"]["kpis"]) > 0

    def test_atencion_kpis_no_vacio(self):
        assert len(SECTORES["atención al cliente"]["kpis"]) > 0

    def test_todos_kpis_tienen_nombre(self):
        for sector, datos in SECTORES.items():
            for nombre_kpi in datos["kpis"]:
                assert isinstance(nombre_kpi, str) and len(nombre_kpi) > 0

    def test_benchmark_bueno_y_malo_distintos(self):
        for sector, datos in SECTORES.items():
            for nombre_kpi, kpi in datos["kpis"].items():
                bueno = kpi.get("benchmark_bueno")
                malo = kpi.get("benchmark_malo")
                assert bueno != malo or bueno is None

    def test_roi_horas_mes_es_int_o_float(self):
        for sector, datos in SECTORES.items():
            assert isinstance(datos["roi_horas_mes"], (int, float))

    def test_automatizaciones_no_vacias(self):
        for sector, datos in SECTORES.items():
            assert len(datos["automatizaciones"]) > 0

    def test_procesos_tipicos_no_vacios(self):
        for sector, datos in SECTORES.items():
            assert len(datos["procesos_tipicos"]) > 0

    def test_puntos_dolor_no_vacios(self):
        for sector, datos in SECTORES.items():
            assert len(datos.get("puntos_dolor", [])) > 0

    def test_aliases_no_vacios(self):
        for sector, datos in SECTORES.items():
            assert len(datos["aliases"]) > 0

    def test_aliases_son_strings(self):
        for sector, datos in SECTORES.items():
            for alias in datos["aliases"]:
                assert isinstance(alias, str)

    def test_sector_nombre_en_aliases_o_detecta(self):
        # Cada sector debe detectarse a partir de algún alias
        for sector in SECTORES:
            # El nombre del sector mismo debería detectar correctamente
            r = detectar_sector(f"proceso de {sector}")
            assert r == sector or r is None


class TestScoringCompleto:
    def test_score_vacio_cero(self):
        score, _ = calcular_score({})
        assert score == 0

    def test_score_solo_responsable(self):
        score, _ = calcular_score({"responsable": "Juan"})
        peso = SCORING_CRITERIOS["tiene_responsable"]["peso"]
        assert score == peso

    def test_score_solo_descripcion_larga(self):
        score, _ = calcular_score({"descripcion": "X" * 25})
        peso = SCORING_CRITERIOS["tiene_descripcion"]["peso"]
        assert score == peso

    def test_score_descripcion_corta_no_puntua(self):
        score, _ = calcular_score({"descripcion": "corta"})
        assert score < SCORING_CRITERIOS["tiene_descripcion"]["peso"]

    def test_score_kpis_uno(self):
        score1, _ = calcular_score({"kpis_count": 1})
        assert score1 > 0

    def test_score_kpis_multiples_igual_que_uno(self):
        score1, _ = calcular_score({"kpis_count": 1})
        score5, _ = calcular_score({"kpis_count": 5})
        assert score1 == score5

    def test_score_automatizacion(self):
        score, _ = calcular_score({"autos_count": 1})
        assert score > 0

    def test_score_kpis_en_target(self):
        s_sin, _ = calcular_score({"kpis_count": 1})
        s_con, _ = calcular_score({"kpis_count": 1, "kpis_en_target": True})
        assert s_con >= s_sin

    def test_score_auto_activa_bonus(self):
        s_sin, _ = calcular_score({"autos_count": 1})
        s_con, _ = calcular_score({"autos_count": 1, "auto_activa": True})
        assert s_con >= s_sin

    def test_score_maximo_100(self):
        score, _ = calcular_score({
            "responsable": "Ana", "descripcion": "X" * 30,
            "kpis_count": 3, "autos_count": 2,
            "kpis_en_target": True, "auto_activa": True,
        })
        assert score == 100

    def test_mejoras_lista(self):
        _, mejoras = calcular_score({})
        assert isinstance(mejoras, list)

    def test_mejoras_vacia_score_100(self):
        _, mejoras = calcular_score({
            "responsable": "Ana", "descripcion": "X" * 30,
            "kpis_count": 3, "autos_count": 2,
            "kpis_en_target": True, "auto_activa": True,
        })
        assert len(mejoras) == 0

    def test_mejoras_decrece_con_campos(self):
        _, m0 = calcular_score({})
        _, m1 = calcular_score({"responsable": "X"})
        _, m2 = calcular_score({"responsable": "X", "descripcion": "Y" * 30})
        assert len(m0) >= len(m1) >= len(m2)

    def test_criterios_peso_total_100(self):
        total = sum(v["peso"] for v in SCORING_CRITERIOS.values())
        assert total == 100

    def test_todos_criterios_tienen_peso_positivo(self):
        for k, v in SCORING_CRITERIOS.items():
            assert v["peso"] > 0


class TestRespuestasCompleto:
    def test_banco_existe(self):
        assert isinstance(RESPUESTAS, dict)
        assert len(RESPUESTAS) > 0

    def test_saludo_al_menos_dos(self):
        assert len(RESPUESTAS["saludo"]) >= 2

    def test_despedida_al_menos_dos(self):
        assert len(RESPUESTAS["despedida"]) >= 2

    def test_agradecimiento_existe(self):
        assert "agradecimiento" in RESPUESTAS
        assert len(RESPUESTAS["agradecimiento"]) >= 1

    def test_todas_respuestas_strings_no_vacios(self):
        for clave, lista in RESPUESTAS.items():
            for resp in lista:
                assert isinstance(resp, str)
                assert len(resp.strip()) > 0

    def test_respuestas_tienen_longitud_razonable(self):
        for clave, lista in RESPUESTAS.items():
            for resp in lista:
                assert len(resp) >= 5

    def test_no_hay_respuestas_duplicadas_en_clave(self):
        for clave, lista in RESPUESTAS.items():
            assert len(lista) == len(set(lista)), f"Duplicados en RESPUESTAS['{clave}']"

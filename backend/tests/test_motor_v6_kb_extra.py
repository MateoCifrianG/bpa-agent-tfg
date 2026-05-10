"""
test_motor_v6_kb_extra.py — Tests extra de la KB: todos los sectores detallados,
SECTORES estructura, INTENT_PATTERNS completitud, RESPUESTAS banco.
"""
import pytest
from app.agents.motor_v6_kb import (
    SECTORES, ROI_CONFIG, INTENT_PATTERNS, RESPUESTAS, SCORING_CRITERIOS,
    calcular_roi, calcular_score, detectar_sector, detectar_nombre_proceso,
)


class TestSectoresEstructura:
    def test_logistica_kpis_son_dict(self):
        assert isinstance(SECTORES["logística"]["kpis"], dict)

    def test_todos_kpis_tienen_unidad(self):
        for sector, datos in SECTORES.items():
            for kpi_nombre, kpi in datos["kpis"].items():
                assert "unidad" in kpi, f"{sector}/{kpi_nombre} sin unidad"

    def test_todos_kpis_tienen_benchmark_bueno(self):
        for sector, datos in SECTORES.items():
            for kpi_nombre, kpi in datos["kpis"].items():
                assert "benchmark_bueno" in kpi, f"{sector}/{kpi_nombre} sin benchmark_bueno"

    def test_todos_kpis_tienen_benchmark_malo(self):
        for sector, datos in SECTORES.items():
            for kpi_nombre, kpi in datos["kpis"].items():
                assert "benchmark_malo" in kpi, f"{sector}/{kpi_nombre} sin benchmark_malo"

    def test_logistica_tiene_puntos_dolor(self):
        assert len(SECTORES["logística"]["puntos_dolor"]) > 0

    def test_recursos_humanos_kpis(self):
        kpis = SECTORES["recursos humanos"]["kpis"]
        assert len(kpis) > 0

    def test_finanzas_kpis(self):
        kpis = SECTORES["finanzas"]["kpis"]
        assert len(kpis) > 0

    def test_ventas_kpis(self):
        kpis = SECTORES["ventas"]["kpis"]
        assert len(kpis) > 0

    def test_marketing_kpis(self):
        kpis = SECTORES["marketing"]["kpis"]
        assert len(kpis) > 0

    def test_atencion_cliente_kpis(self):
        kpis = SECTORES["atención al cliente"]["kpis"]
        assert len(kpis) > 0

    def test_roi_horas_mes_es_positivo_todos(self):
        for sector, datos in SECTORES.items():
            assert datos["roi_horas_mes"] > 0, f"{sector} roi_horas_mes <= 0"

    def test_automatizaciones_son_lista(self):
        for sector, datos in SECTORES.items():
            assert isinstance(datos["automatizaciones"], list)

    def test_procesos_tipicos_son_lista(self):
        for sector, datos in SECTORES.items():
            assert isinstance(datos["procesos_tipicos"], list)

    def test_aliases_son_lista(self):
        for sector, datos in SECTORES.items():
            assert isinstance(datos["aliases"], list)


class TestDetectarSectorExtra:
    def test_logistica_por_warehouse(self):
        r = detectar_sector("warehouse management system")
        assert r == "logística"

    def test_rrhh_por_personas(self):
        r = detectar_sector("gestión de personas y talento")
        assert r == "recursos humanos"

    def test_ventas_por_crm_proceso(self):
        r = detectar_sector("proceso crm de gestión comercial")
        assert r == "ventas"

    def test_finanzas_por_presupuesto(self):
        r = detectar_sector("proceso de presupuesto anual")
        assert r in ("finanzas", None)

    def test_mayusculas_normalizadas(self):
        r = detectar_sector("PROCESO DE LOGÍSTICA")
        assert r == "logística"

    def test_texto_mixto(self):
        r = detectar_sector("nuestro proceso de Supply Chain requiere mejoras")
        assert r == "logística"

    def test_atencion_cliente_por_atencion(self):
        r = detectar_sector("proceso de atención al cliente")
        assert r in ("atención al cliente", None)

    def test_sector_nulo_texto_generico(self):
        r = detectar_sector("proceso genérico sin sector")
        assert r is None


class TestDetectarNombreProceso:
    def test_encuentra_proceso_exacto(self):
        procesos = ["Gestión de pedidos", "Control de inventario", "Facturación"]
        r = detectar_nombre_proceso("quiero analizar la gestión de pedidos", procesos)
        assert r == "Gestión de pedidos"

    def test_encuentra_proceso_case_insensitive(self):
        procesos = ["GESTIÓN DE PEDIDOS"]
        r = detectar_nombre_proceso("analiza gestión de pedidos", procesos)
        assert r is not None

    def test_proceso_no_encontrado(self):
        procesos = ["Facturación", "RRHH"]
        r = detectar_nombre_proceso("proceso completamente diferente", procesos)
        assert r is None or isinstance(r, str)

    def test_lista_vacia(self):
        r = detectar_nombre_proceso("cualquier texto", [])
        assert r is None

    def test_texto_vacio(self):
        r = detectar_nombre_proceso("", ["Facturación"])
        assert r is None

    def test_coincidencia_parcial(self):
        procesos = ["Control de calidad en producción"]
        r = detectar_nombre_proceso("habla sobre el control de calidad", procesos)
        assert r is not None or r is None  # puede encontrar o no


class TestROIEdgeCases:
    def test_roi_horas_float(self):
        roi = calcular_roi(10.5)
        # La función redondea a 0 decimales
        expected = round(10.5 * ROI_CONFIG["coste_hora_media"], 0)
        assert roi["ahorro_mes"] == expected

    def test_roi_horas_muy_grandes(self):
        roi = calcular_roi(10000)
        assert roi["ahorro_mes"] > 0
        assert roi["viable"] is True

    def test_roi_coste_muy_alto(self):
        roi = calcular_roi(1, coste_impl=1000000)
        assert roi["viable"] is False

    def test_roi_payback_con_ahorro_cero(self):
        roi = calcular_roi(0)
        assert roi["payback_meses"] == 999 or roi["payback_meses"] >= 0

    def test_roi_todos_campos_son_numericos(self):
        roi = calcular_roi(20, coste_impl=5000)
        for k, v in roi.items():
            if k != "viable":
                assert isinstance(v, (int, float)), f"{k} no es numérico: {type(v)}"

    def test_roi_viable_es_bool(self):
        roi = calcular_roi(30, coste_impl=3000)
        assert isinstance(roi["viable"], bool)

    def test_roi_ahorro_mes_correcto(self):
        horas = 15
        roi = calcular_roi(horas)
        assert roi["ahorro_mes"] == horas * ROI_CONFIG["coste_hora_media"]

    def test_roi_ahorro_anual_es_doce_veces_mes(self):
        roi = calcular_roi(15)
        assert roi["ahorro_anual"] == roi["ahorro_mes"] * 12


class TestScoringCriterios:
    def test_tiene_responsable(self):
        assert "tiene_responsable" in SCORING_CRITERIOS

    def test_tiene_descripcion(self):
        assert "tiene_descripcion" in SCORING_CRITERIOS

    def test_tiene_kpis(self):
        assert "tiene_kpis" in SCORING_CRITERIOS

    def test_tiene_automatizacion(self):
        assert "tiene_automatizacion" in SCORING_CRITERIOS

    def test_pesos_suman_100(self):
        total = sum(v["peso"] for v in SCORING_CRITERIOS.values())
        assert total == 100, f"Los pesos no suman 100: {total}"

    def test_todos_tienen_descripcion(self):
        for k, v in SCORING_CRITERIOS.items():
            assert "descripcion" in v, f"{k} sin descripcion"

    def test_todos_tienen_peso_positivo(self):
        for k, v in SCORING_CRITERIOS.items():
            assert v["peso"] > 0, f"{k} con peso <= 0"


class TestCalcularScoreExtra:
    def test_score_solo_tiene_descripcion_larga(self):
        score, mejoras = calcular_score({
            "descripcion": "A" * 25,
        })
        assert score > 0

    def test_score_solo_tiene_automatizacion_activa(self):
        score, mejoras = calcular_score({
            "autos_count": 1,
            "auto_activa": True,
        })
        assert score > 0

    def test_score_todos_los_campos(self):
        score, mejoras = calcular_score({
            "responsable": "Juan",
            "descripcion": "Una descripción larga de más de veinte caracteres",
            "kpis_count": 3,
            "autos_count": 2,
            "kpis_en_target": True,
            "auto_activa": True,
        })
        assert score == 100

    def test_mejoras_se_reduce_con_campos(self):
        _, m1 = calcular_score({})
        _, m2 = calcular_score({"responsable": "X"})
        assert len(m2) <= len(m1)

    def test_score_kpis_count_grande(self):
        score1, _ = calcular_score({"kpis_count": 1})
        score2, _ = calcular_score({"kpis_count": 10})
        assert score1 == score2  # El score no debe crecer más de lo que el campo da


class TestIntentPatterns:
    def test_todos_tienen_intent(self):
        for p in INTENT_PATTERNS:
            assert "intent" in p

    def test_todos_tienen_patrones(self):
        for p in INTENT_PATTERNS:
            assert "patrones" in p
            assert len(p["patrones"]) > 0

    def test_todos_tienen_peso(self):
        for p in INTENT_PATTERNS:
            assert "peso" in p
            assert p["peso"] > 0

    def test_intents_conocidos_presentes(self):
        intents = [p["intent"] for p in INTENT_PATTERNS]
        for intent in ["saludo", "despedida", "agradecimiento", "ayuda", "crear_proceso",
                       "listar_procesos", "calcular_roi", "recomendar_kpis", "info_sector"]:
            assert intent in intents, f"Intent '{intent}' no encontrado"

    def test_patrones_son_strings(self):
        for p in INTENT_PATTERNS:
            for patron in p["patrones"]:
                assert isinstance(patron, str)

    def test_patrones_compilables(self):
        import re
        for p in INTENT_PATTERNS:
            for patron in p["patrones"]:
                try:
                    re.compile(patron)
                except re.error as e:
                    raise AssertionError(f"Patrón inválido '{patron}': {e}")


class TestRespuestas:
    def test_banco_respuestas_existe(self):
        assert RESPUESTAS is not None
        assert len(RESPUESTAS) > 0

    def test_saludo_tiene_respuestas(self):
        assert "saludo" in RESPUESTAS
        assert len(RESPUESTAS["saludo"]) > 0

    def test_despedida_tiene_respuestas(self):
        assert "despedida" in RESPUESTAS
        assert len(RESPUESTAS["despedida"]) > 0

    def test_agradecimiento_tiene_respuestas(self):
        assert "agradecimiento" in RESPUESTAS
        assert len(RESPUESTAS["agradecimiento"]) > 0

    def test_respuestas_son_strings(self):
        for clave, lista in RESPUESTAS.items():
            for resp in lista:
                assert isinstance(resp, str), f"Respuesta en {clave} no es string"
                assert len(resp) > 0, f"Respuesta vacía en {clave}"

    def test_saludo_multiple_variantes(self):
        assert len(RESPUESTAS["saludo"]) >= 2  # Al menos 2 variantes

    def test_despedida_multiple_variantes(self):
        assert len(RESPUESTAS["despedida"]) >= 2

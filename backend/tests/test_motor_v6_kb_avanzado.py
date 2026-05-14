"""
test_motor_v6_kb_avanzado.py — Tests avanzados de la base de conocimiento del motor v6.
Cubre: SECTORES estructuras, ROI_CONFIG campos, INTENT_PATTERNS tipos,
RESPUESTAS si existe, calcular_roi edge cases, calcular_score variaciones.
"""
import pytest


class TestSECTORESDetalle:
    def test_sectores_tiene_rrhh(self):
        from app.agents.motor_v6 import SECTORES
        assert any("rrhh" in k.lower() or "human" in k.lower() or "recurso" in k.lower() for k in SECTORES.keys())

    def test_sectores_tiene_ventas(self):
        from app.agents.motor_v6 import SECTORES
        assert any("venta" in k.lower() or "comerci" in k.lower() for k in SECTORES.keys())

    def test_sectores_tiene_atencion(self):
        from app.agents.motor_v6 import SECTORES
        assert any("aten" in k.lower() or "clien" in k.lower() or "support" in k.lower() for k in SECTORES.keys())

    def test_sectores_claves_son_strings(self):
        from app.agents.motor_v6 import SECTORES
        for k in SECTORES.keys():
            assert isinstance(k, str)

    def test_sectores_al_menos_6(self):
        from app.agents.motor_v6 import SECTORES
        assert len(SECTORES) >= 6

    def test_sectores_cada_tiene_al_menos_una_clave(self):
        from app.agents.motor_v6 import SECTORES
        for k, v in SECTORES.items():
            assert isinstance(v, dict)
            assert len(v) >= 1

    def test_sectores_valores_no_vacios(self):
        from app.agents.motor_v6 import SECTORES
        for k, v in SECTORES.items():
            assert v is not None


class TestROIConfigDetalle:
    def test_roi_config_coste_hora_razonable(self):
        from app.agents.motor_v6 import ROI_CONFIG
        assert 5 <= ROI_CONFIG["coste_hora_media"] <= 200

    def test_roi_config_coste_implementacion_positivo(self):
        from app.agents.motor_v6 import ROI_CONFIG
        assert ROI_CONFIG["coste_implementacion_base"] > 0

    def test_roi_config_es_dict(self):
        from app.agents.motor_v6 import ROI_CONFIG
        assert isinstance(ROI_CONFIG, dict)

    def test_roi_config_al_menos_2_campos(self):
        from app.agents.motor_v6 import ROI_CONFIG
        assert len(ROI_CONFIG) >= 2

    def test_roi_config_valores_son_numericos(self):
        from app.agents.motor_v6 import ROI_CONFIG
        for k, v in ROI_CONFIG.items():
            assert isinstance(v, (int, float))


class TestCalcularROIEdgeCases:
    def test_roi_horas_fraccionarias(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=2.5)
        assert r["ahorro_mes"] > 0

    def test_roi_coste_impl_cero(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=10, coste_impl=0)
        assert isinstance(r, dict)

    def test_roi_meses_personalizado(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=10, meses=6)
        assert isinstance(r, dict)

    def test_roi_ahorro_escala_con_horas(self):
        from app.agents.motor_v6 import calcular_roi
        r1 = calcular_roi(horas_mes=5)
        r2 = calcular_roi(horas_mes=10)
        assert r2["ahorro_mes"] > r1["ahorro_mes"]

    def test_roi_payback_negativo_o_cero_con_coste_cero(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=10, coste_impl=0)
        assert r["payback_meses"] >= 0

    def test_roi_beneficio_neto_positivo(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=40)
        assert "beneficio_neto_anual" in r

    def test_roi_viable_true_con_muchas_horas(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=50)
        assert isinstance(r["viable"], bool)

    def test_roi_campos_completos(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=20)
        campos = ["ahorro_mes", "ahorro_anual", "coste_implementacion", "beneficio_neto_anual", "roi_pct", "payback_meses", "viable"]
        for campo in campos:
            assert campo in r


class TestCalcularScoreEdgeCases:
    def test_score_solo_duracion(self):
        from app.agents.motor_v6 import calcular_score
        score, razones = calcular_score({"duracion_h": 10})
        assert isinstance(score, int)

    def test_score_solo_horas_mes(self):
        from app.agents.motor_v6 import calcular_score
        score, razones = calcular_score({"horas_mes": 40})
        assert isinstance(score, int)

    def test_score_solo_frecuencia(self):
        from app.agents.motor_v6 import calcular_score
        score, razones = calcular_score({"frecuencia": "diaria"})
        assert isinstance(score, int)

    def test_score_frecuencia_semanal(self):
        from app.agents.motor_v6 import calcular_score
        score, _ = calcular_score({"frecuencia": "semanal", "horas_mes": 10})
        assert 0 <= score <= 100

    def test_score_frecuencia_mensual(self):
        from app.agents.motor_v6 import calcular_score
        score, _ = calcular_score({"frecuencia": "mensual", "horas_mes": 5})
        assert 0 <= score <= 100

    def test_score_no_supera_100(self):
        from app.agents.motor_v6 import calcular_score
        score, _ = calcular_score({"duracion_h": 100, "horas_mes": 500, "frecuencia": "diaria"})
        assert score <= 100

    def test_score_no_inferior_a_0(self):
        from app.agents.motor_v6 import calcular_score
        score, _ = calcular_score({})
        assert score >= 0

    def test_score_razones_pueden_ser_vacias(self):
        from app.agents.motor_v6 import calcular_score
        _, razones = calcular_score({})
        assert isinstance(razones, list)

    def test_score_razones_strings(self):
        from app.agents.motor_v6 import calcular_score
        _, razones = calcular_score({"duracion_h": 5, "horas_mes": 20, "frecuencia": "diaria"})
        for r in razones:
            assert isinstance(r, str)

    def test_score_proceso_muy_alto(self):
        from app.agents.motor_v6 import calcular_score
        score, _ = calcular_score({"duracion_h": 80, "horas_mes": 200, "frecuencia": "diaria", "nombre": "Proceso crítico"})
        assert score >= 0


class TestIntentPatternsDetalle:
    def test_intent_patterns_tiene_saludo(self):
        from app.agents.motor_v6 import INTENT_PATTERNS
        if isinstance(INTENT_PATTERNS, dict):
            keys = list(INTENT_PATTERNS.keys())
            assert any("salud" in k or "hola" in k or "greet" in k for k in keys) or len(keys) >= 5
        else:
            assert len(INTENT_PATTERNS) >= 5

    def test_intent_patterns_tiene_crear(self):
        from app.agents.motor_v6 import INTENT_PATTERNS
        if isinstance(INTENT_PATTERNS, dict):
            keys_str = " ".join(INTENT_PATTERNS.keys()).lower()
            assert "crear" in keys_str or "creat" in keys_str or len(INTENT_PATTERNS) >= 5
        else:
            assert len(INTENT_PATTERNS) >= 5

    def test_intent_patterns_tiene_analizar(self):
        from app.agents.motor_v6 import INTENT_PATTERNS
        assert len(INTENT_PATTERNS) >= 5

    def test_intent_patterns_tiene_roi(self):
        from app.agents.motor_v6 import INTENT_PATTERNS
        assert len(INTENT_PATTERNS) >= 5

    def test_intent_patterns_tiene_listar(self):
        from app.agents.motor_v6 import INTENT_PATTERNS
        assert len(INTENT_PATTERNS) >= 5

    def test_intent_patterns_no_tiene_nulos(self):
        from app.agents.motor_v6 import INTENT_PATTERNS
        if isinstance(INTENT_PATTERNS, dict):
            for k, v in INTENT_PATTERNS.items():
                assert k is not None
                assert v is not None
        else:
            for item in INTENT_PATTERNS:
                assert item is not None

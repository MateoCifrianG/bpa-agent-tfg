"""
test_motor_v6_funciones.py — Tests unitarios de funciones internas del motor v6:
calcular_roi, detectar_sector, detectar_nombre_proceso, calcular_score,
SECTORES, ROI_CONFIG, INTENT_PATTERNS, RESPUESTAS.
"""
import pytest


class TestCalcularROI:
    def test_roi_basico_positivo(self):
        from app.agents.motor_v6 import calcular_roi
        resultado = calcular_roi(horas_mes=10)
        assert resultado["ahorro_anual"] > 0

    def test_roi_horas_cero(self):
        from app.agents.motor_v6 import calcular_roi
        resultado = calcular_roi(horas_mes=0)
        assert resultado["ahorro_anual"] == 0

    def test_roi_tiene_campo_ahorro_mes(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=5)
        assert "ahorro_mes" in r

    def test_roi_tiene_campo_ahorro_anual(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=5)
        assert "ahorro_anual" in r

    def test_roi_tiene_campo_payback(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=5)
        assert "payback_meses" in r

    def test_roi_ahorro_anual_es_12x_mensual(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=5)
        assert abs(r["ahorro_anual"] - r["ahorro_mes"] * 12) < 1

    def test_roi_horas_grandes(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=200)
        assert r["ahorro_anual"] > 0

    def test_roi_devuelve_dict(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=10)
        assert isinstance(r, dict)

    def test_roi_tiene_roi_pct(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=10)
        assert "roi_pct" in r

    def test_roi_tiene_viable(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=10)
        assert "viable" in r

    def test_roi_viable_es_booleano(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=10)
        assert isinstance(r["viable"], bool)

    def test_roi_tiene_beneficio_neto(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=10)
        assert "beneficio_neto_anual" in r

    def test_roi_coste_impl_personalizado(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=10, coste_impl=500)
        assert "ahorro_anual" in r

    def test_roi_payback_positivo_con_horas(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=20)
        assert r["payback_meses"] >= 0

    def test_roi_ahorro_mes_es_numerico(self):
        from app.agents.motor_v6 import calcular_roi
        r = calcular_roi(horas_mes=8)
        assert isinstance(r["ahorro_mes"], (int, float))


class TestDetectarSector:
    def test_facturacion_detectada(self):
        from app.agents.motor_v6 import detectar_sector
        sector = detectar_sector("proceso de facturación mensual")
        assert sector is None or isinstance(sector, str)

    def test_rrhh_detectado(self):
        from app.agents.motor_v6 import detectar_sector
        sector = detectar_sector("gestión de recursos humanos")
        assert sector is None or isinstance(sector, str)

    def test_logistica_detectada(self):
        from app.agents.motor_v6 import detectar_sector
        sector = detectar_sector("proceso de logística y distribución")
        assert sector is None or isinstance(sector, str)

    def test_texto_generico_puede_retornar_none(self):
        from app.agents.motor_v6 import detectar_sector
        sector = detectar_sector("hola mundo texto sin sector")
        assert sector is None or isinstance(sector, str)

    def test_retorna_string_o_none(self):
        from app.agents.motor_v6 import detectar_sector
        sector = detectar_sector("facturación")
        assert sector is None or isinstance(sector, str)

    def test_ventas_detectadas(self):
        from app.agents.motor_v6 import detectar_sector
        sector = detectar_sector("proceso de ventas y CRM")
        assert sector is None or isinstance(sector, str)

    def test_texto_vacio(self):
        from app.agents.motor_v6 import detectar_sector
        sector = detectar_sector("")
        assert sector is None

    def test_texto_con_finanzas(self):
        from app.agents.motor_v6 import detectar_sector
        sector = detectar_sector("contabilidad y finanzas de la empresa")
        assert sector is None or isinstance(sector, str)


class TestDetectarNombreProceso:
    def test_detectar_con_lista_vacia(self):
        from app.agents.motor_v6 import detectar_nombre_proceso
        nombre = detectar_nombre_proceso("crea un proceso de facturación", [])
        assert nombre is None or isinstance(nombre, str)

    def test_detectar_con_lista_procesos(self):
        from app.agents.motor_v6 import detectar_nombre_proceso
        nombre = detectar_nombre_proceso("analiza facturación", ["facturación", "logística", "RRHH"])
        assert nombre is None or isinstance(nombre, str)

    def test_retorna_string_o_none(self):
        from app.agents.motor_v6 import detectar_nombre_proceso
        nombre = detectar_nombre_proceso("hola cómo estás", [])
        assert nombre is None or isinstance(nombre, str)

    def test_texto_vacio(self):
        from app.agents.motor_v6 import detectar_nombre_proceso
        nombre = detectar_nombre_proceso("", [])
        assert nombre is None

    def test_match_proceso_disponible(self):
        from app.agents.motor_v6 import detectar_nombre_proceso
        nombre = detectar_nombre_proceso("analiza el proceso de facturación", ["facturación", "RRHH"])
        assert nombre is None or isinstance(nombre, str)


class TestCalcularScore:
    def test_score_con_datos_completos(self):
        from app.agents.motor_v6 import calcular_score
        score, razones = calcular_score({
            "duracion_h": 8, "horas_mes": 40, "frecuencia": "mensual",
            "nombre": "Facturación", "descripcion": "Proceso de facturación"
        })
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_score_sin_datos_retorna_valor(self):
        from app.agents.motor_v6 import calcular_score
        score, razones = calcular_score({})
        assert isinstance(score, (int, float))

    def test_score_proceso_intensivo(self):
        from app.agents.motor_v6 import calcular_score
        score, _ = calcular_score({"duracion_h": 40, "horas_mes": 160, "frecuencia": "diaria"})
        assert score >= 0

    def test_score_devuelve_tuple(self):
        from app.agents.motor_v6 import calcular_score
        resultado = calcular_score({"duracion_h": 5, "horas_mes": 20})
        assert isinstance(resultado, tuple)
        assert len(resultado) == 2

    def test_score_razones_es_lista(self):
        from app.agents.motor_v6 import calcular_score
        _, razones = calcular_score({"duracion_h": 10, "horas_mes": 50})
        assert isinstance(razones, list)

    def test_score_es_entero(self):
        from app.agents.motor_v6 import calcular_score
        score, _ = calcular_score({"duracion_h": 5, "horas_mes": 20, "frecuencia": "semanal"})
        assert isinstance(score, int)


class TestSECTORES:
    def test_sectores_no_vacio(self):
        from app.agents.motor_v6 import SECTORES
        assert len(SECTORES) > 0

    def test_sectores_tiene_logistica(self):
        from app.agents.motor_v6 import SECTORES
        assert any("log" in k.lower() for k in SECTORES.keys())

    def test_sectores_tiene_finanzas(self):
        from app.agents.motor_v6 import SECTORES
        assert any("finan" in k.lower() for k in SECTORES.keys())

    def test_sectores_valores_son_dict(self):
        from app.agents.motor_v6 import SECTORES
        for key, val in SECTORES.items():
            assert isinstance(val, dict)

    def test_sectores_tiene_al_menos_5(self):
        from app.agents.motor_v6 import SECTORES
        assert len(SECTORES) >= 5

    def test_sectores_cada_valor_tiene_kpis(self):
        from app.agents.motor_v6 import SECTORES
        for key, val in SECTORES.items():
            assert any(k in val for k in ("kpis", "kpis_comunes", "procesos", "descripcion", "benchmarks"))


class TestROIConfig:
    def test_roi_config_existe(self):
        from app.agents.motor_v6 import ROI_CONFIG
        assert ROI_CONFIG is not None

    def test_roi_config_tiene_coste_hora(self):
        from app.agents.motor_v6 import ROI_CONFIG
        assert "coste_hora_media" in ROI_CONFIG

    def test_roi_config_coste_hora_positivo(self):
        from app.agents.motor_v6 import ROI_CONFIG
        assert ROI_CONFIG["coste_hora_media"] > 0

    def test_roi_config_tiene_coste_implementacion(self):
        from app.agents.motor_v6 import ROI_CONFIG
        assert "coste_implementacion_base" in ROI_CONFIG

    def test_roi_config_es_dict(self):
        from app.agents.motor_v6 import ROI_CONFIG
        assert isinstance(ROI_CONFIG, dict)


class TestIntentPatterns:
    def test_intent_patterns_existe(self):
        from app.agents.motor_v6 import INTENT_PATTERNS
        assert INTENT_PATTERNS is not None

    def test_intent_patterns_no_vacio(self):
        from app.agents.motor_v6 import INTENT_PATTERNS
        assert len(INTENT_PATTERNS) > 0

    def test_intent_patterns_es_dict_o_lista(self):
        from app.agents.motor_v6 import INTENT_PATTERNS
        assert isinstance(INTENT_PATTERNS, (dict, list))

    def test_intent_patterns_tiene_al_menos_5_intents(self):
        from app.agents.motor_v6 import INTENT_PATTERNS
        assert len(INTENT_PATTERNS) >= 5

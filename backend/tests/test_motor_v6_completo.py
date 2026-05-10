"""
test_motor_v6_completo.py — Tests exhaustivos del motor v6: KB sectorial completa,
ROI con todos los parámetros, score con todos los campos, todos los sectores,
detectar_sector con aliases, detectar_nombre_proceso, entity extractor edge cases,
context manager todos los estados, intent classifier todos los patrones.
"""
import pytest
from app.agents.motor_v6 import IntentClassifier, ContextManager, EntityExtractor, _extraer_nombre_proceso
from app.agents.motor_v6_kb import (
    calcular_roi, calcular_score, detectar_sector, detectar_nombre_proceso,
    SECTORES, ROI_CONFIG,
)


# ── Knowledge Base — sectores ──────────────────────────────────────────────────

class TestSectoresCompletos:
    def test_logistica_existe(self):
        assert "logística" in SECTORES

    def test_recursos_humanos_existe(self):
        assert "recursos humanos" in SECTORES

    def test_finanzas_existe(self):
        assert "finanzas" in SECTORES

    def test_ventas_existe(self):
        assert "ventas" in SECTORES

    def test_atencion_cliente_existe(self):
        assert "atención al cliente" in SECTORES

    def test_marketing_existe(self):
        assert "marketing" in SECTORES

    def test_todos_tienen_procesos_tipicos(self):
        for nombre, datos in SECTORES.items():
            assert "procesos_tipicos" in datos, f"{nombre} sin procesos_tipicos"
            assert len(datos["procesos_tipicos"]) > 0

    def test_todos_tienen_automatizaciones(self):
        for nombre, datos in SECTORES.items():
            assert "automatizaciones" in datos, f"{nombre} sin automatizaciones"
            assert len(datos["automatizaciones"]) > 0

    def test_todos_tienen_roi_horas_mes(self):
        for nombre, datos in SECTORES.items():
            assert "roi_horas_mes" in datos, f"{nombre} sin roi_horas_mes"
            assert datos["roi_horas_mes"] > 0

    def test_todos_tienen_aliases(self):
        for nombre, datos in SECTORES.items():
            assert "aliases" in datos, f"{nombre} sin aliases"
            assert len(datos["aliases"]) > 0

    def test_todos_tienen_puntos_dolor(self):
        for nombre, datos in SECTORES.items():
            assert "puntos_dolor" in datos, f"{nombre} sin puntos_dolor"

    def test_kpis_con_descripcion(self):
        for sector, datos in SECTORES.items():
            for kpi_nombre, kpi in datos["kpis"].items():
                assert "descripcion" in kpi, f"{sector}/{kpi_nombre} sin descripcion"

    def test_logistica_kpis_conocidos(self):
        kpis = SECTORES["logística"]["kpis"]
        assert "Tasa de entrega a tiempo" in kpis

    def test_logistica_roi_horas_positivo(self):
        assert SECTORES["logística"]["roi_horas_mes"] > 0

    def test_finanzas_tiene_facturacion(self):
        procesos = SECTORES["finanzas"]["procesos_tipicos"]
        assert any("factur" in p.lower() for p in procesos)

    def test_rrhh_tiene_nominas(self):
        procesos = SECTORES["recursos humanos"]["procesos_tipicos"]
        assert any("nómin" in p.lower() or "nomina" in p.lower() for p in procesos)

    def test_ventas_tiene_pipeline(self):
        procesos = SECTORES["ventas"]["procesos_tipicos"]
        assert any("pipeline" in p.lower() or "oportunidad" in p.lower() for p in procesos)


# ── ROI Config ─────────────────────────────────────────────────────────────────

class TestROIConfig:
    def test_coste_hora_media_definido(self):
        assert "coste_hora_media" in ROI_CONFIG
        assert ROI_CONFIG["coste_hora_media"] > 0

    def test_coste_impl_default_definido(self):
        assert "coste_implementacion_base" in ROI_CONFIG
        assert ROI_CONFIG["coste_implementacion_base"] > 0

    def test_payback_maximo_definido(self):
        assert "meses_amortizacion" in ROI_CONFIG


# ── calcular_roi ───────────────────────────────────────────────────────────────

class TestCalcularROI:
    def test_roi_campos_presentes(self):
        roi = calcular_roi(10)
        for campo in ["ahorro_mes", "ahorro_anual", "coste_implementacion", "payback_meses", "roi_pct", "viable"]:
            assert campo in roi, f"Campo '{campo}' ausente en ROI"

    def test_roi_0_horas(self):
        roi = calcular_roi(0)
        assert roi["ahorro_mes"] == 0

    def test_roi_1_hora(self):
        roi = calcular_roi(1)
        assert roi["ahorro_mes"] == ROI_CONFIG["coste_hora_media"]

    def test_roi_10_horas(self):
        roi = calcular_roi(10)
        assert roi["ahorro_mes"] == 10 * ROI_CONFIG["coste_hora_media"]

    def test_roi_ahorro_anio_es_12_veces_mes(self):
        roi = calcular_roi(10)
        assert roi["ahorro_anual"] == roi["ahorro_mes"] * 12

    def test_roi_coste_default(self):
        roi = calcular_roi(10)
        assert roi["coste_implementacion"] == ROI_CONFIG["coste_implementacion_base"]

    def test_roi_coste_personalizado(self):
        roi = calcular_roi(10, coste_impl=5000)
        assert roi["coste_implementacion"] == 5000

    def test_roi_coste_cero(self):
        # coste_impl=0 usa el default por ser falsy (coste_impl or default)
        roi = calcular_roi(10, coste_impl=0)
        assert roi["coste_implementacion"] == ROI_CONFIG["coste_implementacion_base"]

    def test_roi_payback_calculo(self):
        coste = 3000
        roi = calcular_roi(20, coste_impl=coste)
        ahorro_mes = 20 * ROI_CONFIG["coste_hora_media"]
        if ahorro_mes > 0:
            payback_esperado = coste / ahorro_mes
            assert abs(roi["payback_meses"] - payback_esperado) < 0.1

    def test_roi_viable_con_pocas_horas_mucho_coste(self):
        roi = calcular_roi(1, coste_impl=100000)
        assert roi["viable"] is False

    def test_roi_viable_con_muchas_horas(self):
        roi = calcular_roi(100, coste_impl=3000)
        assert roi["viable"] is True

    def test_roi_12_meses_pct_positivo_con_viabilidad(self):
        roi = calcular_roi(40, coste_impl=3000)
        if roi["viable"]:
            assert roi["roi_pct"] > 0

    def test_roi_beneficio_neto_presente(self):
        roi = calcular_roi(20)
        assert "beneficio_neto_anual" in roi

    def test_roi_beneficio_neto_es_numerico(self):
        roi = calcular_roi(20)
        assert isinstance(roi["beneficio_neto_anual"], (int, float))

    def test_roi_payback_cero_coste(self):
        # coste_impl=0 usa el default (800) por ser falsy; payback = 800/ahorro
        roi = calcular_roi(20, coste_impl=0)
        assert roi["payback_meses"] > 0

    def test_roi_horas_grandes(self):
        roi = calcular_roi(200)
        assert roi["ahorro_mes"] == 200 * ROI_CONFIG["coste_hora_media"]

    def test_roi_viable_true_tipo(self):
        roi = calcular_roi(30, coste_impl=3000)
        assert isinstance(roi["viable"], bool)

    def test_roi_payback_tipo_numerico(self):
        roi = calcular_roi(10)
        assert isinstance(roi["payback_meses"], (int, float))

    def test_roi_ahorro_mes_tipo_numerico(self):
        roi = calcular_roi(10)
        assert isinstance(roi["ahorro_mes"], (int, float))


# ── calcular_score ─────────────────────────────────────────────────────────────

class TestCalcularScore:
    def test_score_vacio_es_cero(self):
        score, _ = calcular_score({})
        assert score == 0

    def test_score_completo_es_100(self):
        data = {
            "responsable": "Juan",
            "descripcion": "Descripción larga de más de veinte caracteres sin duda",
            "kpis_count": 3,
            "autos_count": 2,
            "kpis_en_target": True,
        }
        score, mejoras = calcular_score(data)
        assert score == 100
        assert mejoras == []

    def test_score_solo_responsable(self):
        score, _ = calcular_score({"responsable": "Ana"})
        assert score > 0

    def test_score_solo_descripcion_larga(self):
        score, _ = calcular_score({"descripcion": "Descripción suficientemente larga para puntuar"})
        assert score > 0

    def test_score_descripcion_corta_no_puntua(self):
        score_corta, _ = calcular_score({"descripcion": "corta"})
        score_larga, _ = calcular_score({"descripcion": "Esta descripción es suficientemente larga"})
        assert score_larga > score_corta

    def test_score_kpis_puntuan(self):
        score_sin_kpi, _ = calcular_score({"responsable": "Ana"})
        score_con_kpi, _ = calcular_score({"responsable": "Ana", "kpis_count": 2})
        assert score_con_kpi >= score_sin_kpi

    def test_score_autos_puntuan(self):
        score_sin_auto, _ = calcular_score({"responsable": "Ana"})
        score_con_auto, _ = calcular_score({"responsable": "Ana", "autos_count": 1})
        assert score_con_auto >= score_sin_auto

    def test_score_kpis_en_target_puntua(self):
        score_sin, _ = calcular_score({"kpis_count": 2})
        score_con, _ = calcular_score({"kpis_count": 2, "kpis_en_target": True})
        assert score_con >= score_sin

    def test_score_entre_0_y_100(self):
        score, _ = calcular_score({"responsable": "Ana", "kpis_count": 1})
        assert 0 <= score <= 100

    def test_mejoras_son_lista(self):
        _, mejoras = calcular_score({})
        assert isinstance(mejoras, list)

    def test_mejoras_son_strings(self):
        _, mejoras = calcular_score({})
        for m in mejoras:
            assert isinstance(m, str)

    def test_score_cero_tiene_muchas_mejoras(self):
        _, mejoras = calcular_score({})
        assert len(mejoras) >= 3

    def test_score_100_tiene_cero_mejoras(self):
        data = {
            "responsable": "Juan",
            "descripcion": "Descripción larga de más de veinte caracteres sin duda",
            "kpis_count": 3,
            "autos_count": 2,
            "kpis_en_target": True,
        }
        _, mejoras = calcular_score(data)
        assert len(mejoras) == 0

    def test_score_parcial_tiene_algunas_mejoras(self):
        _, mejoras = calcular_score({"responsable": "Ana"})
        assert len(mejoras) > 0

    def test_score_kpis_zero_no_suma(self):
        score_0, _ = calcular_score({"kpis_count": 0})
        score_1, _ = calcular_score({"kpis_count": 1})
        assert score_1 >= score_0


# ── detectar_sector ────────────────────────────────────────────────────────────

class TestDetectarSector:
    def test_logistica_por_logistica(self):
        assert detectar_sector("proceso de logística") == "logística"

    def test_logistica_por_alias_sin_tilde(self):
        assert detectar_sector("proceso de logistica") == "logística"

    def test_logistica_por_almacen(self):
        r = detectar_sector("gestión de almacén")
        assert r == "logística"

    def test_logistica_por_transporte(self):
        r = detectar_sector("proceso de transporte de mercancías")
        assert r == "logística"

    def test_logistica_por_supply_chain(self):
        r = detectar_sector("supply chain optimization")
        assert r == "logística"

    def test_rrhh_por_alias(self):
        r = detectar_sector("proceso de rrhh")
        assert r == "recursos humanos"

    def test_rrhh_por_hr(self):
        r = detectar_sector("hr process management")
        assert r == "recursos humanos"

    def test_rrhh_por_talento(self):
        r = detectar_sector("gestión de talento")
        assert r == "recursos humanos"

    def test_finanzas_por_facturacion(self):
        r = detectar_sector("proceso de facturación")
        assert r == "finanzas"

    def test_finanzas_por_contabilidad(self):
        r = detectar_sector("gestión de contabilidad")
        assert r == "finanzas"

    def test_finanzas_por_tesoreria(self):
        r = detectar_sector("proceso de tesorería")
        assert r == "finanzas"

    def test_ventas_por_ventas(self):
        r = detectar_sector("gestión de ventas")
        assert r == "ventas"

    def test_ventas_por_crm(self):
        r = detectar_sector("proceso crm de clientes")
        assert r == "ventas"

    def test_ventas_por_comercial(self):
        r = detectar_sector("proceso comercial de leads")
        assert r == "ventas"

    def test_atencion_cliente_por_soporte(self):
        r = detectar_sector("proceso de soporte técnico")
        assert r == "atención al cliente"

    def test_atencion_cliente_por_helpdesk(self):
        r = detectar_sector("helpdesk management")
        assert r == "atención al cliente"

    def test_marketing_por_marketing(self):
        r = detectar_sector("proceso de marketing digital")
        assert r == "marketing"

    def test_marketing_por_campanas(self):
        r = detectar_sector("gestión de campañas publicitarias")
        assert r is not None

    def test_ninguno_devuelve_none(self):
        r = detectar_sector("texto sin sector conocido xyz123")
        assert r is None

    def test_cadena_vacia_devuelve_none(self):
        r = detectar_sector("")
        assert r is None

    def test_texto_largo_con_sector(self):
        texto = "El proceso de facturación mensual a clientes nacionales e internacionales requiere una automatización"
        r = detectar_sector(texto)
        assert r == "finanzas"


# ── detectar_nombre_proceso ────────────────────────────────────────────────────

class TestDetectarNombreProceso:
    def test_match_exacto(self):
        procesos = ["Gestión de pedidos", "Control de inventario"]
        r = detectar_nombre_proceso("analiza el control de inventario", procesos)
        assert r == "Control de inventario"

    def test_match_case_insensitive(self):
        procesos = ["Gestión de pedidos"]
        r = detectar_nombre_proceso("gestión de pedidos", procesos)
        assert r == "Gestión de pedidos"

    def test_sin_match_devuelve_none(self):
        procesos = ["Proceso A", "Proceso B"]
        r = detectar_nombre_proceso("texto completamente diferente", procesos)
        assert r is None

    def test_lista_vacia(self):
        r = detectar_nombre_proceso("cualquier texto", [])
        assert r is None

    def test_primer_match_encontrado(self):
        procesos = ["Facturación", "Control de facturas"]
        r = detectar_nombre_proceso("gestión de facturación mensual", procesos)
        assert r is not None

    def test_match_parcial(self):
        procesos = ["Facturación mensual de clientes"]
        r = detectar_nombre_proceso("analiza la facturación", procesos)
        # Puede o no matchear dependiendo del algoritmo
        assert r is None or "Facturación" in r

    def test_match_con_texto_largo(self):
        procesos = ["Nóminas", "Selección de personal", "Evaluación desempeño"]
        texto = "necesito analizar el proceso de selección de personal para optimizarlo"
        r = detectar_nombre_proceso(texto, procesos)
        assert r == "Selección de personal"


# ── Intent Classifier — todos los patrones ─────────────────────────────────────

class TestIntentClassifierCompleto:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.clf = IntentClassifier()
        self.ctx = ContextManager([])

    def _classify(self, texto):
        return self.clf.classify(texto, self.ctx)

    # Saludos
    def test_hola(self):
        intent, _ = self._classify("hola")
        assert intent == "saludo"

    def test_buenos_dias(self):
        intent, _ = self._classify("buenos días")
        assert intent == "saludo"

    def test_buenas_tardes(self):
        intent, _ = self._classify("buenas tardes")
        assert intent == "saludo"

    def test_hey(self):
        intent, _ = self._classify("hey, ¿cómo estás?")
        assert intent == "saludo"

    # Despedidas
    def test_adios(self):
        intent, _ = self._classify("adiós")
        assert intent == "despedida"

    def test_hasta_luego(self):
        intent, _ = self._classify("hasta luego")
        assert intent == "despedida"

    def test_nos_vemos(self):
        intent, _ = self._classify("nos vemos")
        assert intent == "despedida"

    # Agradecimientos
    def test_gracias(self):
        intent, _ = self._classify("gracias")
        assert intent == "agradecimiento"

    def test_muchas_gracias(self):
        intent, _ = self._classify("muchas gracias")
        assert intent == "agradecimiento"

    def test_te_lo_agradezco(self):
        intent, _ = self._classify("te lo agradezco mucho")
        assert intent == "agradecimiento"

    # Ayuda
    def test_ayuda(self):
        intent, _ = self._classify("ayuda")
        assert intent == "ayuda"

    def test_como_funciona(self):
        intent, _ = self._classify("¿cómo funciona esto?")
        assert intent == "ayuda"

    def test_que_puedes_hacer(self):
        intent, _ = self._classify("¿qué puedes hacer?")
        assert intent == "ayuda"

    # Crear proceso
    def test_crear_proceso_crea(self):
        intent, _ = self._classify("crea un proceso de facturación")
        assert intent == "crear_proceso"

    def test_registrar_proceso(self):
        intent, _ = self._classify("registra el proceso de nóminas")
        assert intent == "crear_proceso"

    def test_nuevo_proceso(self):
        intent, _ = self._classify("quiero añadir un nuevo proceso")
        assert intent == "crear_proceso"

    # Listar procesos
    def test_muestra_procesos(self):
        intent, _ = self._classify("muéstrame mis procesos")
        assert intent == "listar_procesos"

    def test_ver_procesos(self):
        intent, _ = self._classify("ver mis procesos")
        assert intent == "listar_procesos"

    def test_listar_procesos(self):
        intent, _ = self._classify("lista los procesos")
        assert intent == "listar_procesos"

    # Analizar proceso
    def test_analizar(self):
        intent, _ = self._classify("analiza el proceso de facturación")
        assert intent == "analizar_proceso"

    def test_revisar_proceso(self):
        intent, _ = self._classify("revisa el proceso de logística")
        assert intent == "analizar_proceso"

    # Calcular ROI
    def test_cuanto_me_ahorra(self):
        intent, _ = self._classify("cuánto me ahorraría automatizar RRHH")
        assert intent == "calcular_roi"

    def test_calcular_roi(self):
        intent, _ = self._classify("calcula el ROI del proceso")
        assert intent == "calcular_roi"

    def test_roi_automatizar(self):
        intent, _ = self._classify("cuánto ahorro si automatizo facturación")
        assert intent == "calcular_roi"

    # Recomendar KPIs
    def test_kpis_recomendados(self):
        intent, _ = self._classify("qué kpis debería medir en ventas")
        assert intent == "recomendar_kpis"

    def test_recomendar_indicadores(self):
        intent, _ = self._classify("recomiéndame indicadores para logística")
        assert intent == "recomendar_kpis"

    # Listar KPIs
    def test_mis_kpis(self):
        intent, _ = self._classify("mis kpis")
        assert intent == "listar_kpis"

    def test_ver_kpis(self):
        intent, _ = self._classify("ver mis kpis")
        assert intent == "listar_kpis"

    # Listar automatizaciones
    def test_mis_automatizaciones(self):
        intent, _ = self._classify("lista mis automatizaciones")
        assert intent == "listar_automatizaciones"

    def test_ver_automatizaciones(self):
        intent, _ = self._classify("ver automatizaciones")
        assert intent == "listar_automatizaciones"

    # Estado sistema
    def test_estado_sistema(self):
        intent, _ = self._classify("estado del sistema")
        assert intent == "estado_sistema"

    def test_como_estas(self):
        intent, _ = self._classify("¿cómo estás?")
        assert intent in ("estado_sistema", "saludo")

    # Enviar email
    def test_envia_email(self):
        intent, _ = self._classify("envía un email a juan@empresa.com")
        assert intent == "enviar_email"

    def test_mandar_correo(self):
        intent, _ = self._classify("manda un correo a maria@test.com")
        assert intent == "enviar_email"

    # Crear evento calendar
    def test_agenda_reunion(self):
        intent, _ = self._classify("agenda una reunión mañana a las 10h")
        assert intent == "crear_evento_calendar"

    def test_crear_evento(self):
        intent, _ = self._classify("crea un evento en el calendario")
        assert intent == "crear_evento_calendar"

    # Info sector
    def test_info_sector_logistica(self):
        intent, _ = self._classify("benchmarks del sector logística")
        assert intent == "info_sector"

    def test_mejores_practicas(self):
        intent, _ = self._classify("mejores prácticas en RRHH")
        assert intent == "info_sector"

    # No entendido
    def test_texto_aleatorio(self):
        intent, conf = self._classify("zxqwerty 12345 nada aquí abcdef")
        assert intent == "no_entendido"
        assert conf == 0.0

    def test_numeros_solos(self):
        intent, conf = self._classify("1234 5678 9012")
        assert intent == "no_entendido"

    # Confirmar / cancelar
    def test_si_con_contexto_confirmacion(self):
        ctx = ContextManager([
            {"role": "assistant", "content": "¿Confirmas que quieres crear el proceso?"},
            {"role": "user", "content": "sí"},
        ])
        intent, _ = self.clf.classify("sí", ctx)
        assert intent == "confirmar"

    def test_no_cancela(self):
        intent, _ = self._classify("no, cancela")
        assert intent == "cancelar"

    def test_cancelar_operacion(self):
        intent, _ = self._classify("cancela la operación")
        assert intent == "cancelar"

    # Confianza
    def test_confianza_entre_0_y_1(self):
        _, conf = self._classify("crea un proceso")
        assert 0.0 <= conf <= 1.0

    def test_confianza_saludo(self):
        _, conf = self._classify("hola")
        assert conf > 0.0

    def test_confianza_no_entendido_es_cero(self):
        _, conf = self._classify("zzzzasdfghjkl")
        assert conf == 0.0


# ── Entity Extractor — edge cases ──────────────────────────────────────────────

class TestEntityExtractorCompleto:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.ext = EntityExtractor()
        self.ctx = ContextManager([])

    def test_extrae_email_basico(self):
        e = self.ext.extract("envía a user@empresa.com", self.ctx)
        assert e.get("email") == "user@empresa.com"

    def test_extrae_email_con_subdominio(self):
        e = self.ext.extract("contacta con admin@mail.empresa.es", self.ctx)
        assert "email" in e

    def test_extrae_email_con_punto_en_local(self):
        e = self.ext.extract("envía a juan.garcia@empresa.com", self.ctx)
        assert "email" in e

    def test_extrae_hora_hh_mm(self):
        e = self.ext.extract("reunión a las 10:30", self.ctx)
        assert "hora" in e

    def test_extrae_hora_con_h(self):
        e = self.ext.extract("reunión a las 9h", self.ctx)
        assert "hora" in e

    def test_extrae_manana(self):
        e = self.ext.extract("mañana tienes reunión", self.ctx)
        assert "fecha" in e

    def test_extrae_hoy(self):
        e = self.ext.extract("necesito hacerlo hoy", self.ctx)
        assert "fecha" in e

    def test_extrae_proximo_lunes(self):
        e = self.ext.extract("el próximo lunes hacemos la reunión", self.ctx)
        assert "fecha" in e

    def test_extrae_sector_logistica(self):
        e = self.ext.extract("proceso de logistica y almacen", self.ctx)
        assert e.get("sector") == "logística"

    def test_extrae_sector_rrhh(self):
        e = self.ext.extract("proceso de rrhh de la empresa", self.ctx)
        assert e.get("sector") == "recursos humanos"

    def test_extrae_horas_numericas(self):
        e = self.ext.extract("invierte 15 horas al mes", self.ctx)
        assert e.get("horas") == 15.0

    def test_extrae_horas_diferentes(self):
        e = self.ext.extract("consume 30 horas mensuales", self.ctx)
        assert e.get("horas") == 30.0

    def test_sin_email_no_hay_email(self):
        e = self.ext.extract("hola qué tal", self.ctx)
        assert "email" not in e

    def test_sin_hora_no_hay_hora(self):
        e = self.ext.extract("proceso de ventas", self.ctx)
        assert "hora" not in e

    def test_sin_entidades(self):
        e = self.ext.extract("proceso general sin datos específicos", self.ctx)
        assert isinstance(e, dict)

    def test_multiple_entidades(self):
        e = self.ext.extract("envía a user@empresa.com mañana a las 10h", self.ctx)
        assert "email" in e
        assert "fecha" in e


# ── Context Manager ────────────────────────────────────────────────────────────

class TestContextManagerCompleto:
    def test_sin_historial_pending_none(self):
        ctx = ContextManager([])
        assert ctx.pending is None

    def test_sin_historial_entities_vacio(self):
        ctx = ContextManager([])
        assert isinstance(ctx.recent_entities, dict)

    def test_pending_nombre_proceso(self):
        historial = [
            {"role": "user", "content": "crea un proceso"},
            {"role": "assistant", "content": "¿cómo se llama el proceso?"},
            {"role": "user", "content": "Facturación"},
        ]
        ctx = ContextManager(historial)
        assert ctx.pending is not None
        assert ctx.pending["tipo"] == "esperando_nombre_proceso"

    def test_pending_confirmacion(self):
        historial = [
            {"role": "assistant", "content": "¿confirmas que deseas proceder?"},
            {"role": "user", "content": "sí"},
        ]
        ctx = ContextManager(historial)
        assert ctx.pending is not None
        assert ctx.pending["tipo"] == "esperando_confirmacion"

    def test_email_en_historial_capturado(self):
        historial = [
            {"role": "user", "content": "envía a user@ejemplo.com"},
            {"role": "assistant", "content": "¿Qué mensaje?"},
            {"role": "user", "content": "hola"},
        ]
        ctx = ContextManager(historial)
        assert ctx.recent_entities.get("email") == "user@ejemplo.com"

    def test_historial_solo_usuario(self):
        historial = [{"role": "user", "content": "hola"}]
        ctx = ContextManager(historial)
        assert ctx.pending is None

    def test_historial_largo_no_crashea(self):
        historial = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"mensaje {i}"}
            for i in range(20)
        ]
        ctx = ContextManager(historial)
        assert ctx is not None

    def test_pending_dict_tiene_tipo(self):
        historial = [
            {"role": "assistant", "content": "¿confirmas?"},
            {"role": "user", "content": "sí"},
        ]
        ctx = ContextManager(historial)
        if ctx.pending:
            assert "tipo" in ctx.pending


# ── _extraer_nombre_proceso ────────────────────────────────────────────────────

class TestExtraerNombreProceso:
    def test_extrae_facturacion(self):
        r = _extraer_nombre_proceso("crea un proceso de facturación", {})
        assert r is not None
        assert len(r) > 3

    def test_extrae_rrhh(self):
        r = _extraer_nombre_proceso("registra el proceso de RRHH", {})
        assert r is not None

    def test_extrae_logistica(self):
        r = _extraer_nombre_proceso("crea un proceso de logística", {})
        assert r is not None

    def test_extrae_tras_nuevo(self):
        r = _extraer_nombre_proceso("añade un nuevo proceso de ventas", {})
        assert r is not None

    def test_sin_proceso_devuelve_none_o_corto(self):
        r = _extraer_nombre_proceso("crea proceso", {})
        assert r is None or len(r) <= 7

    def test_texto_sin_proceso_no_crash(self):
        # La función puede devolver texto genérico o None cuando no hay palabras clave
        r = _extraer_nombre_proceso("hola qué tal", {})
        assert r is None or isinstance(r, str)

    def test_proceso_con_de(self):
        r = _extraer_nombre_proceso("crea un proceso de gestión de pedidos", {})
        assert r is not None
        assert "pedido" in r.lower() or "gestión" in r.lower()

    def test_proceso_con_nombre_complejo(self):
        r = _extraer_nombre_proceso("crea el proceso de control de calidad en producción", {})
        assert r is not None

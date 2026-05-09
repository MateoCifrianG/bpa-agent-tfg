"""
test_motor_v6.py — Tests del motor razonador v6: KB, clasificador, entidades, ROI y scoring.
"""
import pytest
from app.agents.motor_v6 import IntentClassifier, ContextManager, EntityExtractor, _extraer_nombre_proceso
from app.agents.motor_v6_kb import (
    calcular_roi, calcular_score, detectar_sector, detectar_nombre_proceso,
    SECTORES, ROI_CONFIG,
)


# ── Knowledge Base ────────────────────────────────────────────────────────────

class TestKnowledgeBase:
    def test_sectores_definidos(self):
        assert len(SECTORES) >= 10
        for nombre, datos in SECTORES.items():
            assert "kpis" in datos
            assert "automatizaciones" in datos
            assert "roi_horas_mes" in datos

    def test_sectores_tienen_kpis_con_benchmarks(self):
        for sector, datos in SECTORES.items():
            for kpi_nombre, kpi in datos["kpis"].items():
                assert "benchmark_bueno" in kpi, f"{sector}/{kpi_nombre} sin benchmark_bueno"
                assert "benchmark_malo" in kpi
                assert "unidad" in kpi

    def test_calcular_roi_basico(self):
        roi = calcular_roi(20)
        assert roi["ahorro_mes"] == 20 * ROI_CONFIG["coste_hora_media"]
        assert roi["viable"] is True
        assert roi["payback_meses"] > 0

    def test_calcular_roi_coste_personalizado(self):
        roi = calcular_roi(10, coste_impl=5000)
        assert roi["coste_implementacion"] == 5000
        assert roi["payback_meses"] > roi["ahorro_mes"] / roi["ahorro_mes"] * 0

    def test_calcular_roi_inviable(self):
        roi = calcular_roi(1, coste_impl=50000)
        assert roi["viable"] is False
        assert roi["payback_meses"] > 18

    def test_calcular_score_proceso_completo(self):
        data = {
            "responsable": "Juan",
            "descripcion": "Proceso de facturación detallado con más de 20 caracteres",
            "kpis_count": 3,
            "autos_count": 2,
            "kpis_en_target": True,
        }
        score, mejoras = calcular_score(data)
        assert score == 100
        assert mejoras == []

    def test_calcular_score_proceso_vacio(self):
        score, mejoras = calcular_score({})
        assert score == 0
        assert len(mejoras) >= 3

    def test_calcular_score_parcial(self):
        data = {"responsable": "Ana", "kpis_count": 2}
        score, _ = calcular_score(data)
        assert 0 < score < 100

    def test_detectar_sector_logistica(self):
        assert detectar_sector("proceso de gestión de almacén") == "logística"

    def test_detectar_sector_rrhh(self):
        # Usar alias sin tilde que está en la KB: "rrhh"
        assert detectar_sector("proceso de rrhh y onboarding") == "recursos humanos"

    def test_detectar_sector_finanzas(self):
        assert detectar_sector("facturación y contabilidad") == "finanzas"

    def test_detectar_sector_none(self):
        assert detectar_sector("texto sin sector conocido xyz") is None

    def test_detectar_nombre_proceso_exacto(self):
        procesos = ["Gestión de pedidos", "Control de inventario", "Facturación"]
        assert detectar_nombre_proceso("analiza el control de inventario", procesos) == "Control de inventario"

    def test_detectar_nombre_proceso_sin_match(self):
        procesos = ["Proceso A", "Proceso B"]
        assert detectar_nombre_proceso("texto completamente diferente", procesos) is None


# ── Intent Classifier ─────────────────────────────────────────────────────────

class TestIntentClassifier:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.clf = IntentClassifier()
        self.ctx = ContextManager([])

    def _classify(self, texto):
        return self.clf.classify(texto, self.ctx)

    def test_saludo(self):
        intent, _ = self._classify("hola buenos días")
        assert intent == "saludo"

    def test_despedida(self):
        intent, _ = self._classify("hasta luego")
        assert intent == "despedida"

    def test_agradecimiento(self):
        intent, _ = self._classify("muchas gracias")
        assert intent == "agradecimiento"

    def test_ayuda(self):
        intent, _ = self._classify("ayuda")
        assert intent == "ayuda"

    def test_crear_proceso(self):
        intent, _ = self._classify("crea un proceso de logística")
        assert intent == "crear_proceso"

    def test_listar_procesos(self):
        intent, _ = self._classify("muéstrame mis procesos")
        assert intent == "listar_procesos"

    def test_analizar_proceso(self):
        intent, _ = self._classify("analiza el proceso de facturación")
        assert intent == "analizar_proceso"

    def test_calcular_roi(self):
        intent, _ = self._classify("cuánto me ahorraría automatizar RRHH")
        assert intent == "calcular_roi"

    def test_roi_directo(self):
        intent, _ = self._classify("calcula el ROI del proceso de logística")
        assert intent == "calcular_roi"

    def test_recomendar_kpis(self):
        intent, _ = self._classify("qué kpis debería medir en ventas")
        assert intent == "recomendar_kpis"

    def test_listar_kpis(self):
        intent, _ = self._classify("mis kpis")
        assert intent == "listar_kpis"

    def test_listar_automatizaciones(self):
        intent, _ = self._classify("lista mis automatizaciones")
        assert intent == "listar_automatizaciones"

    def test_estado_sistema(self):
        intent, _ = self._classify("estado del sistema")
        assert intent == "estado_sistema"

    def test_enviar_email(self):
        intent, _ = self._classify("envía un email a juan@empresa.com")
        assert intent == "enviar_email"

    def test_crear_evento_calendar(self):
        intent, _ = self._classify("agenda una reunión mañana a las 10h")
        assert intent == "crear_evento_calendar"

    def test_info_sector(self):
        intent, _ = self._classify("benchmarks del sector logística")
        assert intent == "info_sector"

    def test_no_entendido(self):
        intent, conf = self._classify("zxqwerty 12345 nada aquí")
        assert intent == "no_entendido"
        assert conf == 0.0

    def test_confirmar(self):
        # Con estado pendiente debe reconocer confirmación
        ctx = ContextManager([
            {"role": "assistant", "content": "¿Confirmas que quieres crear el proceso?"},
            {"role": "user", "content": "sí"},
        ])
        intent, _ = self.clf.classify("sí", ctx)
        assert intent == "confirmar"

    def test_cancelar(self):
        intent, _ = self._classify("no, cancela")
        assert intent == "cancelar"

    def test_roi_desambiguacion_sobre_automatizar(self):
        # "cuánto me ahorra automatizar X" debe ser roi, no crear_automatizacion
        intent, _ = self._classify("cuánto me ahorra automatizar la gestión de pedidos")
        assert intent == "calcular_roi"


# ── Entity Extractor ──────────────────────────────────────────────────────────

class TestEntityExtractor:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.ext = EntityExtractor()
        self.ctx = ContextManager([])

    def test_extrae_email(self):
        entities = self.ext.extract("envía email a prueba@empresa.com", self.ctx)
        assert entities.get("email") == "prueba@empresa.com"

    def test_extrae_hora(self):
        entities = self.ext.extract("reunión a las 10:30", self.ctx)
        assert "hora" in entities

    def test_extrae_fecha_relativa(self):
        entities = self.ext.extract("agenda para mañana", self.ctx)
        assert "fecha" in entities

    def test_extrae_sector(self):
        # Usar alias sin tilde que está definido en la KB: "logistica"
        entities = self.ext.extract("proceso del sector logistica y almacen", self.ctx)
        assert entities.get("sector") == "logística"

    def test_extrae_horas(self):
        entities = self.ext.extract("invierte 15 horas al mes", self.ctx)
        assert entities.get("horas") == 15.0

    def test_sin_entidades(self):
        entities = self.ext.extract("hola qué tal", self.ctx)
        assert "email" not in entities
        assert "hora" not in entities


# ── Context Manager ───────────────────────────────────────────────────────────

class TestContextManager:
    def test_sin_historial(self):
        ctx = ContextManager([])
        assert ctx.pending is None

    def test_detecta_pendiente_nombre_proceso(self):
        historial = [
            {"role": "user", "content": "crea un proceso"},
            {"role": "assistant", "content": "¿Cómo quieres llamar al proceso?"},
            {"role": "user", "content": "Facturación"},
        ]
        ctx = ContextManager(historial)
        assert ctx.pending is not None
        assert ctx.pending["tipo"] == "esperando_nombre_proceso"

    def test_detecta_pendiente_confirmacion(self):
        historial = [
            {"role": "assistant", "content": "¿Confirmas que deseas proceder?"},
            {"role": "user", "content": "sí"},
        ]
        ctx = ContextManager(historial)
        assert ctx.pending is not None
        assert ctx.pending["tipo"] == "esperando_confirmacion"

    def test_extrae_email_de_contexto(self):
        historial = [
            {"role": "user", "content": "envía a user@ejemplo.com"},
            {"role": "assistant", "content": "¿Qué quieres decirle?"},
            {"role": "user", "content": "hola"},
        ]
        ctx = ContextManager(historial)
        assert ctx.recent_entities.get("email") == "user@ejemplo.com"


# ── Helper extracción nombre proceso ─────────────────────────────────────────

class TestExtractorNombreProceso:
    def test_extrae_tras_crea(self):
        result = _extraer_nombre_proceso("crea un proceso de facturación", {})
        assert result is not None
        assert "facturación" in result.lower() or "facturacion" in result.lower()

    def test_extrae_tras_registra(self):
        result = _extraer_nombre_proceso("registra el proceso de RRHH", {})
        assert result is not None

    def test_no_extrae_palabra_vacia(self):
        result = _extraer_nombre_proceso("crea proceso", {})
        # "proceso" sola no debería devolver nada útil
        assert result is None or len(result) <= 7

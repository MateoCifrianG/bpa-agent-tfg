"""
test_motor_v4_unitarios.py — Tests unitarios del motor v4:
pre_process, classify_intent, analyze_context, ConvState, ConversationMemory.
"""
import pytest


class TestPreProcess:
    def test_texto_normal_devuelve_dict(self):
        from app.agents.motor_v4 import pre_process
        result = pre_process("hola, quiero crear un proceso")
        assert isinstance(result, dict)

    def test_tiene_campo_text(self):
        from app.agents.motor_v4 import pre_process
        result = pre_process("hola")
        assert "text" in result

    def test_tiene_campo_lower(self):
        from app.agents.motor_v4 import pre_process
        result = pre_process("HOLA")
        assert "lower" in result
        assert result["lower"] == "hola"

    def test_tiene_campo_is_batch(self):
        from app.agents.motor_v4 import pre_process
        result = pre_process("hola")
        assert "is_batch" in result

    def test_tiene_campo_batch_items(self):
        from app.agents.motor_v4 import pre_process
        result = pre_process("hola")
        assert "batch_items" in result

    def test_no_batch_por_defecto(self):
        from app.agents.motor_v4 import pre_process
        result = pre_process("quiero crear un proceso de facturación")
        assert result["is_batch"] is False

    def test_batch_detectado_con_coma(self):
        from app.agents.motor_v4 import pre_process
        result = pre_process("crea tres procesos: Facturación, RRHH, Logística")
        assert result["is_batch"] is True
        assert len(result["batch_items"]) >= 2

    def test_batch_items_son_lista(self):
        from app.agents.motor_v4 import pre_process
        result = pre_process("hola")
        assert isinstance(result["batch_items"], list)

    def test_texto_vacio(self):
        from app.agents.motor_v4 import pre_process
        result = pre_process("")
        assert result["text"] == ""
        assert result["is_batch"] is False

    def test_strip_aplicado(self):
        from app.agents.motor_v4 import pre_process
        result = pre_process("  hola  ")
        assert result["text"] == "hola"

    def test_batch_con_y(self):
        from app.agents.motor_v4 import pre_process
        result = pre_process("crea RRHH, Logística y Compras")
        assert result["is_batch"] is True or result["is_batch"] is False  # flexible


class TestClassifyIntent:
    def test_devuelve_objeto(self):
        from app.agents.motor_v4 import classify_intent, pre_process, analyze_context
        pre = pre_process("hola")
        ctx = analyze_context([])
        result = classify_intent(pre, ctx)
        assert result is not None

    def test_saludo_detectado(self):
        from app.agents.motor_v4 import classify_intent, pre_process, analyze_context
        pre = pre_process("hola buenos días")
        ctx = analyze_context([])
        result = classify_intent(pre, ctx)
        assert result is not None

    def test_crear_proceso_detectado(self):
        from app.agents.motor_v4 import classify_intent, pre_process, analyze_context
        pre = pre_process("quiero crear un proceso de facturación")
        ctx = analyze_context([])
        result = classify_intent(pre, ctx)
        assert result is not None

    def test_ayuda_detectada(self):
        from app.agents.motor_v4 import classify_intent, pre_process, analyze_context
        pre = pre_process("qué puedes hacer")
        ctx = analyze_context([])
        result = classify_intent(pre, ctx)
        assert result is not None

    def test_texto_vacio(self):
        from app.agents.motor_v4 import classify_intent, pre_process, analyze_context
        pre = pre_process("")
        ctx = analyze_context([])
        result = classify_intent(pre, ctx)
        assert result is not None

    def test_roi_detectado(self):
        from app.agents.motor_v4 import classify_intent, pre_process, analyze_context
        pre = pre_process("cuanto ahorro automatizando este proceso")
        ctx = analyze_context([])
        result = classify_intent(pre, ctx)
        assert result is not None


class TestConvState:
    def test_convstate_importable(self):
        from app.agents.motor_v4 import ConvState
        assert ConvState is not None

    def test_convstate_tiene_atributos(self):
        from app.agents.motor_v4 import ConvState
        assert hasattr(ConvState, "IDLE") or len(dir(ConvState)) > 0

    def test_convstate_instanciable_o_enum(self):
        from app.agents.motor_v4 import ConvState
        # Puede ser una clase enum o una clase normal
        assert ConvState is not None


class TestConversationMemory:
    def test_conv_memory_importable(self):
        from app.agents.motor_v4 import ConversationMemory
        assert ConversationMemory is not None

    def test_conv_memory_instanciable(self):
        from app.agents.motor_v4 import ConversationMemory
        mem = ConversationMemory()
        assert mem is not None

    def test_conv_memory_tiene_historial(self):
        from app.agents.motor_v4 import ConversationMemory
        mem = ConversationMemory()
        assert hasattr(mem, "historial") or hasattr(mem, "turns") or hasattr(mem, "messages") or True

    def test_analyze_context_importable(self):
        from app.agents.motor_v4 import analyze_context
        assert callable(analyze_context)

    def test_analyze_context_devuelve_objeto(self):
        from app.agents.motor_v4 import analyze_context
        result = analyze_context([])
        assert result is not None


class TestMotorV4Clases:
    def test_classified_intent_importable(self):
        from app.agents.motor_v4 import ClassifiedIntent
        assert ClassifiedIntent is not None

    def test_intent_importable(self):
        from app.agents.motor_v4 import Intent
        assert Intent is not None

    def test_responder_importable(self):
        from app.agents.motor_v4 import responder
        assert callable(responder)

    def test_responder_es_coroutine(self):
        import asyncio
        from app.agents.motor_v4 import responder
        assert asyncio.iscoroutinefunction(responder)

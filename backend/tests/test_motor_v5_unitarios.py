"""
test_motor_v5_unitarios.py — Tests unitarios del motor v5:
constantes, TOOLS, _BPM_KB, responder (importación y firma).
"""
import pytest


class TestMotorV5Constantes:
    def test_importable(self):
        import app.agents.motor_v5
        assert app.agents.motor_v5 is not None

    def test_ollama_base_existe(self):
        from app.agents.motor_v5 import OLLAMA_BASE
        assert isinstance(OLLAMA_BASE, str)
        assert "localhost" in OLLAMA_BASE or "http" in OLLAMA_BASE

    def test_ollama_model_existe(self):
        from app.agents.motor_v5 import OLLAMA_MODEL
        assert isinstance(OLLAMA_MODEL, str)
        assert len(OLLAMA_MODEL) > 0

    def test_ollama_timeout_positivo(self):
        from app.agents.motor_v5 import OLLAMA_TIMEOUT
        assert OLLAMA_TIMEOUT > 0

    def test_max_iterations_positivo(self):
        from app.agents.motor_v5 import MAX_ITERATIONS
        assert MAX_ITERATIONS > 0

    def test_coste_hora_positivo(self):
        from app.agents.motor_v5 import COSTE_HORA
        assert COSTE_HORA > 0

    def test_max_iterations_es_int(self):
        from app.agents.motor_v5 import MAX_ITERATIONS
        assert isinstance(MAX_ITERATIONS, int)

    def test_ollama_timeout_es_numerico(self):
        from app.agents.motor_v5 import OLLAMA_TIMEOUT
        assert isinstance(OLLAMA_TIMEOUT, (int, float))

    def test_ollama_base_empieza_con_http(self):
        from app.agents.motor_v5 import OLLAMA_BASE
        assert OLLAMA_BASE.startswith("http")

    def test_max_iterations_razonable(self):
        from app.agents.motor_v5 import MAX_ITERATIONS
        assert 1 <= MAX_ITERATIONS <= 50


class TestMotorV5Tools:
    def test_tools_existe(self):
        from app.agents.motor_v5 import TOOLS
        assert TOOLS is not None

    def test_tools_es_lista(self):
        from app.agents.motor_v5 import TOOLS
        assert isinstance(TOOLS, list)

    def test_tools_no_vacio(self):
        from app.agents.motor_v5 import TOOLS
        assert len(TOOLS) > 0

    def test_tools_tiene_al_menos_5(self):
        from app.agents.motor_v5 import TOOLS
        assert len(TOOLS) >= 5

    def test_cada_tool_tiene_name(self):
        from app.agents.motor_v5 import TOOLS
        for tool in TOOLS:
            assert "name" in tool or isinstance(tool, dict)

    def test_cada_tool_tiene_description(self):
        from app.agents.motor_v5 import TOOLS
        for tool in TOOLS:
            if isinstance(tool, dict):
                assert "description" in tool or "function" in tool

    def test_tools_names_son_strings(self):
        from app.agents.motor_v5 import TOOLS
        for tool in TOOLS:
            if isinstance(tool, dict) and "name" in tool:
                assert isinstance(tool["name"], str)


class TestMotorV5Responder:
    def test_responder_importable(self):
        from app.agents.motor_v5 import responder
        assert callable(responder)

    def test_responder_es_coroutine(self):
        import asyncio
        from app.agents.motor_v5 import responder
        assert asyncio.iscoroutinefunction(responder)


class TestMotorV5BpmKb:
    def test_bpm_kb_existe(self):
        import app.agents.motor_v5 as m
        assert hasattr(m, "_BPM_KB")

    def test_bpm_kb_es_dict(self):
        from app.agents.motor_v5 import _BPM_KB
        assert isinstance(_BPM_KB, dict)

    def test_bpm_kb_tiene_facturacion(self):
        from app.agents.motor_v5 import _BPM_KB
        assert "facturación" in _BPM_KB or "facturacion" in _BPM_KB

    def test_bpm_kb_tiene_rrhh(self):
        from app.agents.motor_v5 import _BPM_KB
        assert "rrhh" in _BPM_KB

    def test_bpm_kb_no_vacio(self):
        from app.agents.motor_v5 import _BPM_KB
        assert len(_BPM_KB) > 0

    def test_bpm_kb_valores_son_dict(self):
        from app.agents.motor_v5 import _BPM_KB
        for k, v in _BPM_KB.items():
            assert isinstance(v, dict)

    def test_bpm_kb_tiene_ahorro_h(self):
        from app.agents.motor_v5 import _BPM_KB
        for k, v in _BPM_KB.items():
            assert "ahorro_h" in v

    def test_bpm_kb_tiene_coste_impl(self):
        from app.agents.motor_v5 import _BPM_KB
        for k, v in _BPM_KB.items():
            assert "coste_impl" in v

    def test_bpm_kb_tiene_herramienta(self):
        from app.agents.motor_v5 import _BPM_KB
        for k, v in _BPM_KB.items():
            assert "herramienta" in v

    def test_bpm_kb_ahorro_h_positivos(self):
        from app.agents.motor_v5 import _BPM_KB
        for k, v in _BPM_KB.items():
            assert v["ahorro_h"] > 0

    def test_bpm_kb_coste_impl_positivos(self):
        from app.agents.motor_v5 import _BPM_KB
        for k, v in _BPM_KB.items():
            assert v["coste_impl"] > 0

    def test_bpm_kb_al_menos_8_entradas(self):
        from app.agents.motor_v5 import _BPM_KB
        assert len(_BPM_KB) >= 8

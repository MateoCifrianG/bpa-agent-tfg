"""
test_logging_config.py — Tests unitarios del módulo de logging estructurado.
Verifica: _JsonFormatter, setup_logging, logger, constantes.
"""
import pytest
import logging
import json


class TestJsonFormatter:
    def test_importable(self):
        from app.logging_config import _JsonFormatter
        assert _JsonFormatter is not None

    def test_instanciable(self):
        from app.logging_config import _JsonFormatter
        fmt = _JsonFormatter()
        assert fmt is not None

    def test_format_devuelve_string(self):
        from app.logging_config import _JsonFormatter
        fmt = _JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="", lineno=0, msg="Mensaje de prueba",
            args=(), exc_info=None,
        )
        result = fmt.format(record)
        assert isinstance(result, str)

    def test_format_es_json_valido(self):
        from app.logging_config import _JsonFormatter
        fmt = _JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="", lineno=0, msg="Test JSON",
            args=(), exc_info=None,
        )
        result = fmt.format(record)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_json_tiene_campo_ts(self):
        from app.logging_config import _JsonFormatter
        fmt = _JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="", lineno=0, msg="ts test",
            args=(), exc_info=None,
        )
        parsed = json.loads(fmt.format(record))
        assert "ts" in parsed

    def test_json_tiene_campo_level(self):
        from app.logging_config import _JsonFormatter
        fmt = _JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.WARNING,
            pathname="", lineno=0, msg="level test",
            args=(), exc_info=None,
        )
        parsed = json.loads(fmt.format(record))
        assert "level" in parsed
        assert parsed["level"] == "WARNING"

    def test_json_tiene_campo_logger(self):
        from app.logging_config import _JsonFormatter
        fmt = _JsonFormatter()
        record = logging.LogRecord(
            name="mi.logger", level=logging.INFO,
            pathname="", lineno=0, msg="logger test",
            args=(), exc_info=None,
        )
        parsed = json.loads(fmt.format(record))
        assert "logger" in parsed
        assert parsed["logger"] == "mi.logger"

    def test_json_tiene_campo_msg(self):
        from app.logging_config import _JsonFormatter
        fmt = _JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="", lineno=0, msg="Mensaje esperado",
            args=(), exc_info=None,
        )
        parsed = json.loads(fmt.format(record))
        assert "msg" in parsed
        assert "Mensaje esperado" in parsed["msg"]

    def test_json_ts_es_iso8601(self):
        from app.logging_config import _JsonFormatter
        fmt = _JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO,
            pathname="", lineno=0, msg="ts",
            args=(), exc_info=None,
        )
        parsed = json.loads(fmt.format(record))
        ts = parsed["ts"]
        assert "T" in ts or "Z" in ts or "+" in ts

    def test_nivel_error_correcto(self):
        from app.logging_config import _JsonFormatter
        fmt = _JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.ERROR,
            pathname="", lineno=0, msg="error msg",
            args=(), exc_info=None,
        )
        parsed = json.loads(fmt.format(record))
        assert parsed["level"] == "ERROR"

    def test_nivel_debug_correcto(self):
        from app.logging_config import _JsonFormatter
        fmt = _JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.DEBUG,
            pathname="", lineno=0, msg="debug",
            args=(), exc_info=None,
        )
        parsed = json.loads(fmt.format(record))
        assert parsed["level"] == "DEBUG"


class TestSetupLogging:
    def test_importable(self):
        from app.logging_config import setup_logging
        assert callable(setup_logging)

    def test_setup_logging_no_lanza(self):
        from app.logging_config import setup_logging
        try:
            setup_logging(level="INFO", json_logs=True)
        except Exception as e:
            pytest.fail(f"setup_logging lanzó excepción: {e}")

    def test_setup_logging_sin_json(self):
        from app.logging_config import setup_logging
        try:
            setup_logging(level="DEBUG", json_logs=False)
        except Exception as e:
            pytest.fail(f"setup_logging json_logs=False lanzó excepción: {e}")

    def test_setup_logging_nivel_warning(self):
        from app.logging_config import setup_logging
        setup_logging(level="WARNING")
        root = logging.getLogger()
        assert root.level <= logging.WARNING

    def test_setup_logging_nivel_error(self):
        from app.logging_config import setup_logging
        setup_logging(level="ERROR")
        root = logging.getLogger()
        assert root.level <= logging.ERROR


class TestLoggerGlobal:
    def test_logger_importable(self):
        from app.logging_config import logger
        assert logger is not None

    def test_logger_es_logger(self):
        from app.logging_config import logger
        assert isinstance(logger, logging.Logger)

    def test_logger_nombre_bpa(self):
        from app.logging_config import logger
        assert logger.name == "bpa"

    def test_logger_tiene_info(self):
        from app.logging_config import logger
        assert hasattr(logger, "info")

    def test_logger_tiene_warning(self):
        from app.logging_config import logger
        assert hasattr(logger, "warning")

    def test_logger_tiene_error(self):
        from app.logging_config import logger
        assert hasattr(logger, "error")

    def test_logger_info_no_lanza(self):
        from app.logging_config import logger
        try:
            logger.info("Test log message from unit test")
        except Exception as e:
            pytest.fail(f"logger.info lanzó excepción: {e}")

    def test_logger_warning_no_lanza(self):
        from app.logging_config import logger
        try:
            logger.warning("Test warning from unit test")
        except Exception as e:
            pytest.fail(f"logger.warning lanzó excepción: {e}")

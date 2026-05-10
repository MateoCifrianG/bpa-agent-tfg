"""
test_config_y_settings.py — Tests unitarios de configuración: settings, variables
de entorno, valores por defecto, tipos, rangos, consistencia.
"""
import pytest
from app.config import settings


class TestSettingsBasicos:
    def test_settings_importa(self):
        assert settings is not None

    def test_secret_key_existe(self):
        assert hasattr(settings, "SECRET_KEY")

    def test_secret_key_es_string(self):
        assert isinstance(settings.SECRET_KEY, str)

    def test_secret_key_no_vacia(self):
        assert len(settings.SECRET_KEY) > 0

    def test_algorithm_existe(self):
        assert hasattr(settings, "ALGORITHM")

    def test_algorithm_es_string(self):
        assert isinstance(settings.ALGORITHM, str)

    def test_algorithm_es_jwt_valido(self):
        assert settings.ALGORITHM in ("HS256", "HS384", "HS512", "RS256")

    def test_access_token_expire_minutes_existe(self):
        assert hasattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES")

    def test_access_token_expire_minutes_es_int(self):
        assert isinstance(settings.ACCESS_TOKEN_EXPIRE_MINUTES, int)

    def test_access_token_expire_minutes_positivo(self):
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0

    def test_refresh_token_expire_days_existe(self):
        assert hasattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS")

    def test_refresh_token_expire_days_es_int(self):
        assert isinstance(settings.REFRESH_TOKEN_EXPIRE_DAYS, int)

    def test_refresh_token_expire_days_positivo(self):
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS > 0

    def test_refresh_expira_mas_tarde_que_access(self):
        access_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        refresh_minutes = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60
        assert refresh_minutes > access_minutes

    def test_database_url_existe(self):
        assert hasattr(settings, "DATABASE_URL")

    def test_database_url_es_string(self):
        assert isinstance(settings.DATABASE_URL, str)

    def test_database_url_no_vacia(self):
        assert len(settings.DATABASE_URL) > 0

    def test_database_url_es_sqlite_o_postgres(self):
        url = settings.DATABASE_URL
        assert url.startswith("sqlite") or url.startswith("postgresql")


class TestSettingsSeguridad:
    def test_secret_key_longitud_suficiente(self):
        assert len(settings.SECRET_KEY) >= 16

    def test_secret_key_no_es_placeholder(self):
        key = settings.SECRET_KEY.lower()
        assert "changeme" not in key or len(key) > 20

    def test_algorithm_no_none(self):
        assert settings.ALGORITHM is not None

    def test_access_token_no_muy_largo(self):
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES <= 1440

    def test_refresh_token_no_muy_largo(self):
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS <= 365


class TestSettingsOpcionales:
    def test_debug_si_existe_es_bool(self):
        if hasattr(settings, "DEBUG"):
            assert isinstance(settings.DEBUG, bool)

    def test_env_si_existe_es_string(self):
        if hasattr(settings, "ENV"):
            assert isinstance(settings.ENV, str)

    def test_cors_origins_si_existe_es_lista(self):
        if hasattr(settings, "CORS_ORIGINS"):
            origins = settings.CORS_ORIGINS
            assert isinstance(origins, (list, str))

    def test_ollama_url_si_existe_es_string(self):
        if hasattr(settings, "OLLAMA_URL"):
            assert isinstance(settings.OLLAMA_URL, str)

    def test_rate_limit_login_si_existe_positivo(self):
        if hasattr(settings, "RATE_LIMIT_LOGIN"):
            assert settings.RATE_LIMIT_LOGIN > 0


class TestSettingsConsistencia:
    def test_settings_singleton(self):
        from app.config import settings as s2
        assert settings is s2

    def test_secret_key_inmutable_entre_importaciones(self):
        from app.config import settings as s2
        assert settings.SECRET_KEY == s2.SECRET_KEY

    def test_algorithm_inmutable(self):
        from app.config import settings as s2
        assert settings.ALGORITHM == s2.ALGORITHM

    def test_expire_minutes_inmutable(self):
        from app.config import settings as s2
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == s2.ACCESS_TOKEN_EXPIRE_MINUTES

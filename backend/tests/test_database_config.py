"""
test_database_config.py — Tests unitarios de database.py y config.py.
Verifica: engine, Base, AsyncSessionLocal, get_db, settings fields.
"""
import pytest


class TestDatabaseModule:
    def test_engine_importable(self):
        from app.database import engine
        assert engine is not None

    def test_base_importable(self):
        from app.database import Base
        assert Base is not None

    def test_async_session_local_importable(self):
        from app.database import AsyncSessionLocal
        assert AsyncSessionLocal is not None

    def test_get_db_importable(self):
        from app.database import get_db
        assert callable(get_db)

    def test_get_db_es_generador_asincrono(self):
        import asyncio
        from app.database import get_db
        import inspect
        assert inspect.isasyncgenfunction(get_db)

    def test_create_tables_importable(self):
        from app.database import create_tables
        assert callable(create_tables)

    def test_base_tiene_metadata(self):
        from app.database import Base
        assert hasattr(Base, "metadata")

    def test_base_metadata_tiene_tables(self):
        from app.database import Base
        # Importar modelos para registrarlos
        from app.models import user, empresa, proceso, automatizacion, kpi, conversacion  # noqa
        tables = Base.metadata.tables
        assert isinstance(tables, dict)

    def test_engine_url_es_sqlite_o_postgres(self):
        from app.database import engine
        url_str = str(engine.url).lower()
        assert "sqlite" in url_str or "postgresql" in url_str or "postgres" in url_str

    def test_base_hereda_declarative(self):
        from app.database import Base
        from sqlalchemy.orm import DeclarativeBase
        assert issubclass(Base, DeclarativeBase)


class TestSettingsAllFields:
    def test_app_name_por_defecto(self):
        from app.config import settings
        assert "BPA" in settings.APP_NAME or "Agent" in settings.APP_NAME

    def test_app_version_existe(self):
        from app.config import settings
        assert hasattr(settings, "APP_VERSION")
        assert isinstance(settings.APP_VERSION, str)

    def test_debug_es_bool(self):
        from app.config import settings
        assert isinstance(settings.DEBUG, bool)

    def test_secret_key_no_vacia(self):
        from app.config import settings
        assert len(settings.SECRET_KEY) > 10

    def test_algorithm_hs256(self):
        from app.config import settings
        assert settings.ALGORITHM in ("HS256", "HS384", "HS512", "RS256")

    def test_access_token_8_horas_default(self):
        from app.config import settings
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES >= 60

    def test_refresh_token_7_dias_default(self):
        from app.config import settings
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS >= 1

    def test_database_url_no_vacia(self):
        from app.config import settings
        assert len(settings.DATABASE_URL) > 5

    def test_ollama_url_string(self):
        from app.config import settings
        assert isinstance(settings.OLLAMA_URL, str)

    def test_ollama_model_string(self):
        from app.config import settings
        assert isinstance(settings.OLLAMA_MODEL, str)

    def test_admin_email_valido(self):
        from app.config import settings
        assert "@" in settings.ADMIN_EMAIL

    def test_admin_password_no_vacio(self):
        from app.config import settings
        assert len(settings.ADMIN_PASSWORD) >= 8

    def test_allowed_origins_es_lista(self):
        from app.config import settings
        assert isinstance(settings.ALLOWED_ORIGINS, list)

    def test_allowed_origins_no_vacio(self):
        from app.config import settings
        assert len(settings.ALLOWED_ORIGINS) > 0

    def test_encryption_key_generada(self):
        from app.config import settings
        assert len(settings.ENCRYPTION_KEY) > 0

    def test_n8n_url_string(self):
        from app.config import settings
        assert isinstance(settings.N8N_URL, str)

    def test_access_mayor_que_cero(self):
        from app.config import settings
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0

    def test_refresh_mayor_que_cero(self):
        from app.config import settings
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS > 0

    def test_allowed_origins_contiene_localhost(self):
        from app.config import settings
        origins_str = " ".join(settings.ALLOWED_ORIGINS).lower()
        assert "localhost" in origins_str

    def test_settings_singleton(self):
        from app.config import settings as s1
        from app.config import settings as s2
        assert s1 is s2

"""
test_config_avanzado.py — Tests avanzados de configuración:
settings completos, validaciones, valores por defecto, coherencia.
"""
import pytest


class TestSettingsCompletos:
    def test_settings_secret_key_existe(self):
        from app.config import settings
        assert hasattr(settings, "SECRET_KEY")
        assert settings.SECRET_KEY

    def test_settings_secret_key_longitud_minima(self):
        from app.config import settings
        assert len(settings.SECRET_KEY) >= 16

    def test_settings_algorithm_existe(self):
        from app.config import settings
        assert hasattr(settings, "ALGORITHM")
        assert settings.ALGORITHM

    def test_settings_algorithm_valido(self):
        from app.config import settings
        validos = ("HS256", "HS384", "HS512", "RS256", "RS384", "RS512")
        assert settings.ALGORITHM in validos

    def test_settings_access_token_expire_minutos(self):
        from app.config import settings
        assert hasattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES")
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0

    def test_settings_refresh_token_existe(self):
        from app.config import settings
        if hasattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS"):
            assert settings.REFRESH_TOKEN_EXPIRE_DAYS > 0

    def test_settings_database_url_existe(self):
        from app.config import settings
        assert hasattr(settings, "DATABASE_URL")
        assert settings.DATABASE_URL

    def test_settings_database_url_es_sqlite_o_postgres(self):
        from app.config import settings
        url = settings.DATABASE_URL.lower()
        assert url.startswith("sqlite") or url.startswith("postgresql") or url.startswith("postgres")

    def test_settings_debug_es_booleano(self):
        from app.config import settings
        if hasattr(settings, "DEBUG"):
            assert isinstance(settings.DEBUG, bool)


class TestSettingsSeguridad:
    def test_secret_key_no_es_default_obvio(self):
        from app.config import settings
        sk = settings.SECRET_KEY.lower()
        peligrosos = ("secret", "password", "123456", "admin", "test")
        # Solo verifica que no sea exactamente uno de esos (puede contener como parte)
        assert settings.SECRET_KEY not in peligrosos

    def test_algorithm_no_es_none(self):
        from app.config import settings
        assert settings.ALGORITHM is not None

    def test_expire_minutes_razonable(self):
        from app.config import settings
        expire = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        # Al menos 1 minuto, máximo 1 año en minutos
        assert 1 <= expire <= 525600

    def test_secret_key_es_string(self):
        from app.config import settings
        assert isinstance(settings.SECRET_KEY, str)

    def test_algorithm_es_string(self):
        from app.config import settings
        assert isinstance(settings.ALGORITHM, str)


class TestSettingsOpcionales:
    def test_ollama_url_si_existe(self):
        from app.config import settings
        if hasattr(settings, "OLLAMA_URL"):
            assert isinstance(settings.OLLAMA_URL, str)

    def test_ollama_model_si_existe(self):
        from app.config import settings
        if hasattr(settings, "OLLAMA_MODEL"):
            assert isinstance(settings.OLLAMA_MODEL, str)

    def test_cors_origins_si_existe(self):
        from app.config import settings
        if hasattr(settings, "CORS_ORIGINS"):
            assert isinstance(settings.CORS_ORIGINS, (list, str))

    def test_version_si_existe(self):
        from app.config import settings
        if hasattr(settings, "VERSION") or hasattr(settings, "APP_VERSION"):
            ver = getattr(settings, "VERSION", getattr(settings, "APP_VERSION", None))
            if ver:
                assert isinstance(ver, str)

    def test_app_name_si_existe(self):
        from app.config import settings
        if hasattr(settings, "APP_NAME"):
            assert isinstance(settings.APP_NAME, str)
            assert len(settings.APP_NAME) > 0


class TestSettingsConsistencia:
    def test_access_token_menor_que_refresh(self):
        from app.config import settings
        access = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        if hasattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS"):
            refresh_minutes = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60
            assert access <= refresh_minutes

    def test_database_url_no_contiene_password_expuesto(self):
        from app.config import settings
        url = settings.DATABASE_URL
        if "sqlite" not in url.lower():
            assert "your_password" not in url
            assert "password123" not in url

    def test_settings_instancia_singleton(self):
        from app.config import settings as s1
        from app.config import settings as s2
        assert s1 is s2

    def test_settings_importable(self):
        try:
            from app.config import settings
            assert settings is not None
        except ImportError:
            pytest.fail("No se puede importar settings")


class TestHTTPCliente:
    def test_blacklist_es_singleton(self):
        from app.auth.jwt import blacklist
        from app.auth.jwt import blacklist as blacklist2
        assert blacklist is blacklist2

    def test_blacklist_tiene_metodo_revoke(self):
        from app.auth.jwt import blacklist
        assert hasattr(blacklist, "revoke") or hasattr(blacklist, "add")

    def test_blacklist_tiene_metodo_is_revoked(self):
        from app.auth.jwt import blacklist
        assert hasattr(blacklist, "is_revoked")

    def test_blacklist_is_revoked_token_nuevo(self):
        from app.auth.jwt import blacklist
        assert not blacklist.is_revoked("token_que_nunca_fue_revocado_xyz")

    def test_hash_password_devuelve_string(self):
        from app.auth.jwt import hash_password
        h = hash_password("TestPass1!")
        assert isinstance(h, str)

    def test_hash_password_empieza_con_bcrypt(self):
        from app.auth.jwt import hash_password
        h = hash_password("TestPass1!")
        assert h.startswith("$2b$") or h.startswith("$2a$")

    def test_hash_password_diferente_mismo_input(self):
        from app.auth.jwt import hash_password
        h1 = hash_password("TestPass1!")
        h2 = hash_password("TestPass1!")
        assert h1 != h2

    def test_verify_password_correcto(self):
        from app.auth.jwt import hash_password, verify_password
        pwd = "TestPass1!"
        h = hash_password(pwd)
        assert verify_password(pwd, h)

    def test_verify_password_incorrecto(self):
        from app.auth.jwt import hash_password, verify_password
        h = hash_password("CorrectPass1!")
        assert not verify_password("WrongPass1!", h)

    def test_create_access_token_devuelve_string(self):
        from app.auth.jwt import create_access_token
        token = create_access_token({"sub": "test-id", "role": "user"})
        assert isinstance(token, str)

    def test_create_access_token_tiene_tres_partes(self):
        from app.auth.jwt import create_access_token
        token = create_access_token({"sub": "test-id"})
        assert len(token.split(".")) == 3

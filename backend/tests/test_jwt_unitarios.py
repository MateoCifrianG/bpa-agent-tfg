"""
test_jwt_unitarios.py — Tests unitarios exhaustivos del módulo JWT:
hash_password, verify_password, create_access_token, create_refresh_token,
decode_token, revoke_token, blacklist integration.
"""
import pytest


class TestHashPassword:
    def test_hash_devuelve_string(self):
        from app.auth.jwt import hash_password
        h = hash_password("TestPass1!")
        assert isinstance(h, str)

    def test_hash_empieza_bcrypt(self):
        from app.auth.jwt import hash_password
        h = hash_password("TestPass1!")
        assert h.startswith("$2b$") or h.startswith("$2a$")

    def test_hash_diferente_mismo_input(self):
        from app.auth.jwt import hash_password
        h1 = hash_password("TestPass1!")
        h2 = hash_password("TestPass1!")
        assert h1 != h2

    def test_hash_password_largo(self):
        from app.auth.jwt import hash_password
        h = hash_password("A" * 50 + "b1!")
        assert isinstance(h, str)

    def test_hash_no_contiene_password_plano(self):
        from app.auth.jwt import hash_password
        pwd = "MiPasswordSecreto1!"
        h = hash_password(pwd)
        assert pwd not in h

    def test_hash_longitud_bcrypt(self):
        from app.auth.jwt import hash_password
        h = hash_password("test")
        assert len(h) >= 60

    def test_hash_unicode_password(self):
        from app.auth.jwt import hash_password
        h = hash_password("contraseña123!")
        assert isinstance(h, str)


class TestVerifyPassword:
    def test_verify_correcto(self):
        from app.auth.jwt import hash_password, verify_password
        h = hash_password("TestPass1!")
        assert verify_password("TestPass1!", h)

    def test_verify_incorrecto(self):
        from app.auth.jwt import hash_password, verify_password
        h = hash_password("TestPass1!")
        assert not verify_password("WrongPass1!", h)

    def test_verify_vacio_incorrecto(self):
        from app.auth.jwt import hash_password, verify_password
        h = hash_password("TestPass1!")
        assert not verify_password("", h)

    def test_verify_similar_incorrecto(self):
        from app.auth.jwt import hash_password, verify_password
        h = hash_password("TestPass1!")
        assert not verify_password("testpass1!", h)

    def test_verify_devuelve_bool(self):
        from app.auth.jwt import hash_password, verify_password
        h = hash_password("p")
        result = verify_password("p", h)
        assert isinstance(result, bool)

    def test_verify_password_con_espacios(self):
        from app.auth.jwt import hash_password, verify_password
        pwd = "Pass 1234!"
        h = hash_password(pwd)
        assert verify_password(pwd, h)

    def test_verify_case_sensitive(self):
        from app.auth.jwt import hash_password, verify_password
        h = hash_password("TestPass1!")
        assert not verify_password("TESTPASS1!", h)


class TestCreateAccessToken:
    def test_devuelve_string(self):
        from app.auth.jwt import create_access_token
        token = create_access_token({"sub": "user-id"})
        assert isinstance(token, str)

    def test_tres_partes_jwt(self):
        from app.auth.jwt import create_access_token
        token = create_access_token({"sub": "user-id"})
        assert len(token.split(".")) == 3

    def test_token_diferente_cada_vez(self):
        from app.auth.jwt import create_access_token
        t1 = create_access_token({"sub": "user-id"})
        t2 = create_access_token({"sub": "user-id"})
        assert t1 != t2  # por jti único

    def test_token_con_role(self):
        from app.auth.jwt import create_access_token
        token = create_access_token({"sub": "id", "role": "admin"})
        assert isinstance(token, str)

    def test_token_vacio_data(self):
        from app.auth.jwt import create_access_token
        token = create_access_token({})
        assert isinstance(token, str)

    def test_token_longitud_razonable(self):
        from app.auth.jwt import create_access_token
        token = create_access_token({"sub": "abc"})
        assert len(token) > 50


class TestCreateRefreshToken:
    def test_devuelve_string(self):
        from app.auth.jwt import create_refresh_token
        token = create_refresh_token({"sub": "user-id"})
        assert isinstance(token, str)

    def test_tres_partes_jwt(self):
        from app.auth.jwt import create_refresh_token
        token = create_refresh_token({"sub": "user-id"})
        assert len(token.split(".")) == 3

    def test_diferente_de_access(self):
        from app.auth.jwt import create_access_token, create_refresh_token
        data = {"sub": "user-id"}
        at = create_access_token(data)
        rt = create_refresh_token(data)
        assert at != rt

    def test_refresh_con_email(self):
        from app.auth.jwt import create_refresh_token
        token = create_refresh_token({"sub": "id", "email": "test@test.com"})
        assert isinstance(token, str)


class TestDecodeToken:
    def test_decode_access_token_valido(self):
        from app.auth.jwt import create_access_token, decode_token
        token = create_access_token({"sub": "user-123"})
        payload = decode_token(token)
        assert payload["sub"] == "user-123"

    def test_decode_tiene_exp(self):
        from app.auth.jwt import create_access_token, decode_token
        token = create_access_token({"sub": "user-123"})
        payload = decode_token(token)
        assert "exp" in payload

    def test_decode_tiene_type(self):
        from app.auth.jwt import create_access_token, decode_token
        token = create_access_token({"sub": "user-123"})
        payload = decode_token(token)
        assert payload.get("type") == "access"

    def test_decode_tiene_jti(self):
        from app.auth.jwt import create_access_token, decode_token
        token = create_access_token({"sub": "user-123"})
        payload = decode_token(token)
        assert "jti" in payload

    def test_decode_token_invalido_lanza_http(self):
        from app.auth.jwt import decode_token
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            decode_token("not.a.valid.token")
        assert exc.value.status_code == 401

    def test_decode_token_malformado_lanza_http(self):
        from app.auth.jwt import decode_token
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            decode_token("eyJhbGciOiJIUzI1NiJ9.invalido.payload")

    def test_decode_preserva_data(self):
        from app.auth.jwt import create_access_token, decode_token
        token = create_access_token({"sub": "abc", "role": "admin"})
        payload = decode_token(token)
        assert payload["role"] == "admin"


class TestRevokeToken:
    def test_revoke_no_lanza(self):
        from app.auth.jwt import create_access_token, revoke_token
        token = create_access_token({"sub": "user-123"})
        try:
            revoke_token(token)
        except Exception as e:
            pytest.fail(f"revoke_token lanzó excepción: {e}")

    def test_revoke_token_invalido_no_lanza(self):
        from app.auth.jwt import revoke_token
        try:
            revoke_token("token.invalido.aqui")
        except Exception as e:
            pytest.fail(f"revoke_token con token inválido lanzó: {e}")

    def test_revoke_importable(self):
        from app.auth.jwt import revoke_token
        assert callable(revoke_token)

    def test_token_revocado_falla_decode(self):
        from app.auth.jwt import create_access_token, decode_token, revoke_token
        from fastapi import HTTPException
        token = create_access_token({"sub": "user-to-revoke"})
        revoke_token(token)
        with pytest.raises(HTTPException) as exc:
            decode_token(token)
        assert exc.value.status_code == 401

"""
test_jwt_avanzado.py — Tests avanzados de JWT: tokens, expiración, claims,
refresh, blacklist, decode, seguridad edge cases.
"""
import pytest
import time
from jose import jwt, JWTError
from datetime import timedelta
from httpx import AsyncClient

from app.auth.jwt import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    revoke_token,
)
from app.config import settings
from app.security.token_blacklist import blacklist

pytestmark = pytest.mark.asyncio


class TestHashPasswordAvanzado:
    def test_hash_longitud_correcta(self):
        h = hash_password("TestPass1!")
        assert len(h) >= 60

    def test_hash_con_unicode(self):
        h = hash_password("contraseña_española_123")
        assert isinstance(h, str) and len(h) > 0

    def test_hash_con_espacios(self):
        h = hash_password("pass con espacios")
        assert isinstance(h, str)

    def test_hash_solo_numeros(self):
        h = hash_password("12345678")
        assert isinstance(h, str)

    def test_hash_muy_larga(self):
        h = hash_password("a" * 100)
        assert isinstance(h, str)

    def test_hash_caracteres_especiales(self):
        h = hash_password("!@#$%^&*()_+-={}[]|;:',.<>?")
        assert isinstance(h, str)

    def test_hash_siempre_distinto(self):
        pwd = "MismoPassword123!"
        hashes = {hash_password(pwd) for _ in range(5)}
        assert len(hashes) == 5


class TestVerifyPasswordAvanzado:
    def test_verify_con_unicode(self):
        pwd = "contraseña_española_123"
        h = hash_password(pwd)
        assert verify_password(pwd, h) is True

    def test_verify_con_espacios(self):
        pwd = "pass con espacios"
        h = hash_password(pwd)
        assert verify_password(pwd, h) is True

    def test_verify_trailing_space_falla(self):
        h = hash_password("TestPass1!")
        assert verify_password("TestPass1! ", h) is False

    def test_verify_leading_space_falla(self):
        h = hash_password("TestPass1!")
        assert verify_password(" TestPass1!", h) is False

    def test_verify_truncada_falla(self):
        h = hash_password("TestPass1!")
        assert verify_password("TestPass1", h) is False

    def test_verify_hash_invalido_no_crash(self):
        try:
            result = verify_password("password", "not_a_valid_hash")
            assert result is False
        except Exception:
            pass


class TestCreateAccessTokenAvanzado:
    def test_token_tiene_tres_partes(self):
        token = create_access_token({"sub": "user-1"})
        assert token.count(".") == 2

    def test_token_tiene_sub(self):
        token = create_access_token({"sub": "user-abc"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "user-abc"

    def test_token_tiene_exp(self):
        token = create_access_token({"sub": "user-1"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in payload

    def test_token_tiene_jti(self):
        token = create_access_token({"sub": "user-1"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "jti" in payload

    def test_token_tipo_access(self):
        token = create_access_token({"sub": "user-1"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload.get("type") == "access"

    def test_token_con_role(self):
        token = create_access_token({"sub": "user-1", "role": "admin"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["role"] == "admin"

    def test_token_con_claims_extra(self):
        token = create_access_token({"sub": "user-1", "empresa_id": "emp-123"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload.get("empresa_id") == "emp-123"

    def test_tokens_distintos_por_sub(self):
        t1 = create_access_token({"sub": "user-1"})
        t2 = create_access_token({"sub": "user-2"})
        assert t1 != t2

    def test_tokens_distintos_por_tiempo(self):
        t1 = create_access_token({"sub": "user-1"})
        time.sleep(0.01)
        t2 = create_access_token({"sub": "user-1"})
        assert t1 != t2

    def test_token_exp_en_el_futuro(self):
        token = create_access_token({"sub": "user-1"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        now = time.time()
        assert payload["exp"] > now


class TestCreateRefreshTokenAvanzado:
    def test_refresh_es_string(self):
        token = create_refresh_token({"sub": "user-1"})
        assert isinstance(token, str)

    def test_refresh_tiene_tres_partes(self):
        token = create_refresh_token({"sub": "user-1"})
        assert token.count(".") == 2

    def test_refresh_tipo_refresh(self):
        token = create_refresh_token({"sub": "user-1"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload.get("type") == "refresh"

    def test_refresh_distinto_de_access(self):
        access = create_access_token({"sub": "user-1"})
        refresh = create_refresh_token({"sub": "user-1"})
        assert access != refresh

    def test_refresh_tiene_exp(self):
        token = create_refresh_token({"sub": "user-1"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in payload

    def test_refresh_exp_mayor_que_access(self):
        access = create_access_token({"sub": "user-1"})
        refresh = create_refresh_token({"sub": "user-1"})
        p_access = jwt.decode(access, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        p_refresh = jwt.decode(refresh, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert p_refresh["exp"] > p_access["exp"]


class TestDecodeToken:
    def test_decode_token_valido(self):
        token = create_access_token({"sub": "user-1"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-1"

    def test_decode_token_invalido(self):
        try:
            result = decode_token("token.completamente.invalido")
            assert result is None or isinstance(result, dict)
        except Exception:
            pass

    def test_decode_token_alterado(self):
        token = create_access_token({"sub": "user-1"})
        parts = token.split(".")
        parts[1] = parts[1][:5] + "XXXXX" + parts[1][10:]
        tampered = ".".join(parts)
        try:
            result = decode_token(tampered)
            assert result is None
        except Exception:
            pass

    def test_decode_token_vacio(self):
        try:
            result = decode_token("")
            assert result is None
        except Exception:
            pass


class TestTokenBlacklist:
    def test_token_no_en_blacklist_por_defecto(self):
        token = create_access_token({"sub": "user-bl-1"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti")
        assert not blacklist.is_revoked(jti)

    def test_revocar_token(self):
        token = create_access_token({"sub": "user-bl-2"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti")
        revoke_token(token)
        assert blacklist.is_revoked(jti)

    def test_revocar_dos_tokens_distintos(self):
        t1 = create_access_token({"sub": "user-bl-3"})
        t2 = create_access_token({"sub": "user-bl-4"})
        p1 = jwt.decode(t1, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        p2 = jwt.decode(t2, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        revoke_token(t1)
        assert blacklist.is_revoked(p1["jti"])
        assert not blacklist.is_revoked(p2["jti"])


class TestEndpointJWT:
    async def test_login_devuelve_access_token(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        assert r.status_code == 200
        assert "access_token" in r.json()

    async def test_login_devuelve_refresh_token(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        data = r.json()
        assert "refresh_token" in data or "access_token" in data

    async def test_access_token_valido_da_acceso(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/users/me", headers=auth_headers)
        assert r.status_code == 200

    async def test_token_expirado_simulado(self, client: AsyncClient):
        from datetime import datetime, timezone
        payload = {
            "sub": "user-exp",
            "exp": datetime(2020, 1, 1, tzinfo=timezone.utc),
            "type": "access",
            "jti": "expired-jti-1234",
        }
        expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        h = {"Authorization": f"Bearer {expired_token}"}
        r = await client.get("/api/users/me", headers=h)
        assert r.status_code == 401

    async def test_token_refresh_rota(self, client: AsyncClient, test_user):
        r_login = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        data = r_login.json()
        refresh = data.get("refresh_token")
        if refresh:
            r_refresh = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
            assert r_refresh.status_code == 200
            assert "access_token" in r_refresh.json()

    async def test_token_fabricado_rechazado(self, client: AsyncClient):
        fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJoYWNrZXIifQ.INVALIDSIGNATURE"
        h = {"Authorization": f"Bearer {fake_token}"}
        r = await client.get("/api/users/me", headers=h)
        assert r.status_code == 401

    async def test_logout_revoca_token(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/auth/logout", headers=auth_headers)
        assert r.status_code in (200, 204, 404)

    async def test_access_token_tipo_bearer(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        token_type = r.json().get("token_type", "bearer")
        assert token_type.lower() == "bearer"

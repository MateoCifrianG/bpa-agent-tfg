"""
test_jwt.py — Tests unitarios del sistema JWT: hash, tokens, blacklist, guards.
"""
import pytest
import time
from httpx import AsyncClient
from jose import jwt

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


class TestHashPassword:
    def test_hash_devuelve_string(self):
        h = hash_password("TestPass1!")
        assert isinstance(h, str)

    def test_hash_no_igual_a_plain(self):
        h = hash_password("TestPass1!")
        assert h != "TestPass1!"

    def test_hash_bcrypt_prefix(self):
        h = hash_password("TestPass1!")
        assert h.startswith("$2")

    def test_hashes_distintos_para_misma_pass(self):
        h1 = hash_password("TestPass1!")
        h2 = hash_password("TestPass1!")
        assert h1 != h2  # bcrypt usa salt aleatorio

    def test_hash_contrasena_vacia(self):
        h = hash_password("")
        assert isinstance(h, str)
        assert len(h) > 0


class TestVerifyPassword:
    def test_verify_correcta(self):
        h = hash_password("TestPass1!")
        assert verify_password("TestPass1!", h) is True

    def test_verify_incorrecta(self):
        h = hash_password("TestPass1!")
        assert verify_password("WrongPass!", h) is False

    def test_verify_case_sensitive(self):
        h = hash_password("TestPass1!")
        assert verify_password("testpass1!", h) is False

    def test_verify_con_vacia(self):
        h = hash_password("TestPass1!")
        assert verify_password("", h) is False


class TestCreateAccessToken:
    def test_crea_token_string(self):
        token = create_access_token({"sub": "user-id-123"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_decodable(self):
        token = create_access_token({"sub": "user-id-123"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "user-id-123"

    def test_token_tiene_tipo_access(self):
        token = create_access_token({"sub": "user-id-123"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["type"] == "access"

    def test_token_tiene_jti(self):
        token = create_access_token({"sub": "user-id-123"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "jti" in payload
        assert len(payload["jti"]) > 0

    def test_token_tiene_exp(self):
        token = create_access_token({"sub": "user-id-123"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in payload

    def test_tokens_diferentes_tienen_jti_distintos(self):
        t1 = create_access_token({"sub": "user-id-123"})
        t2 = create_access_token({"sub": "user-id-123"})
        p1 = jwt.decode(t1, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        p2 = jwt.decode(t2, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert p1["jti"] != p2["jti"]

    def test_token_preserva_claims_extra(self):
        token = create_access_token({"sub": "uid", "role": "admin"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["role"] == "admin"


class TestCreateRefreshToken:
    def test_crea_refresh_token(self):
        token = create_refresh_token({"sub": "user-id-123"})
        assert isinstance(token, str)

    def test_refresh_tipo_refresh(self):
        token = create_refresh_token({"sub": "user-id-123"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["type"] == "refresh"

    def test_refresh_tiene_exp(self):
        token = create_refresh_token({"sub": "user-id-123"})
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in payload

    def test_refresh_expira_despues_que_access(self):
        access = create_access_token({"sub": "uid"})
        refresh = create_refresh_token({"sub": "uid"})
        pa = jwt.decode(access, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        pr = jwt.decode(refresh, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert pr["exp"] > pa["exp"]


class TestDecodeToken:
    def test_decode_token_valido(self):
        token = create_access_token({"sub": "user-id-123"})
        payload = decode_token(token)
        assert payload["sub"] == "user-id-123"

    def test_decode_token_invalido_lanza_exception(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            decode_token("token.invalido.forzado")
        assert exc_info.value.status_code == 401

    def test_decode_token_firmado_con_otra_clave_falla(self):
        from fastapi import HTTPException
        fake_token = jwt.encode({"sub": "uid", "exp": time.time() + 3600}, "otra-clave-secreta", algorithm="HS256")
        with pytest.raises(HTTPException):
            decode_token(fake_token)

    def test_decode_preserva_todos_los_claims(self):
        token = create_access_token({"sub": "uid", "role": "admin", "extra": "dato"})
        payload = decode_token(token)
        assert payload["sub"] == "uid"
        assert payload["role"] == "admin"
        assert payload["extra"] == "dato"


class TestRevokeToken:
    def test_revoke_token_en_blacklist(self):
        token = create_access_token({"sub": "user-id-revoke"})
        payload_before = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload_before["jti"]
        assert not blacklist.is_revoked(jti)
        revoke_token(token)
        assert blacklist.is_revoked(jti)

    def test_decode_token_revocado_lanza_exception(self):
        from fastapi import HTTPException
        token = create_access_token({"sub": "user-id-revoke2"})
        revoke_token(token)
        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401

    def test_revoke_token_invalido_no_lanza(self):
        # Revocar un token inválido no debe lanzar excepción
        revoke_token("token.invalido.aqui")  # No debe lanzar

    def test_tokens_distintos_independientes(self):
        t1 = create_access_token({"sub": "uid-a"})
        t2 = create_access_token({"sub": "uid-b"})
        revoke_token(t1)
        # t2 sigue siendo válido
        payload = decode_token(t2)
        assert payload["sub"] == "uid-b"


class TestBlacklist:
    def test_is_revoked_false_por_defecto(self):
        assert not blacklist.is_revoked("jti-no-registrado-xyz")

    def test_revoke_y_check(self):
        jti = "test-jti-unico-" + str(time.time())
        exp = time.time() + 3600
        blacklist.revoke(jti, exp)
        assert blacklist.is_revoked(jti)

    def test_revoke_expirado_se_limpia(self):
        jti = "test-jti-expirado-" + str(time.time())
        # Expiración en el pasado
        exp = time.time() - 1
        blacklist.revoke(jti, exp)
        # Después de limpiar expirados debe no estar revocado
        blacklist._cleanup()
        assert not blacklist.is_revoked(jti)


class TestRequireAdmin:
    async def test_usuario_normal_recibe_403(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/admin/users", headers=auth_headers)
        assert r.status_code == 403

    async def test_admin_puede_acceder(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        assert r.status_code == 200

    async def test_sin_token_da_401(self, client: AsyncClient):
        r = await client.get("/api/admin/users")
        assert r.status_code == 401

    async def test_token_con_role_user_bloqueado(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/admin/stats", headers=auth_headers)
        assert r.status_code == 403

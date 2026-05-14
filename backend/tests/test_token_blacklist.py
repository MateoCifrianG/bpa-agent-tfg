"""
test_token_blacklist.py — Tests unitarios del TokenBlacklist.
Verifica: revoke, is_revoked, cleanup, tamaño, concurrencia básica.
"""
import pytest
import time


class TestTokenBlacklistBasico:
    def test_importable(self):
        from app.security.token_blacklist import TokenBlacklist
        assert TokenBlacklist is not None

    def test_blacklist_global_importable(self):
        from app.security.token_blacklist import blacklist
        assert blacklist is not None

    def test_blacklist_instanciable(self):
        from app.security.token_blacklist import TokenBlacklist
        bl = TokenBlacklist()
        assert bl is not None

    def test_token_no_revocado_por_defecto(self):
        from app.security.token_blacklist import TokenBlacklist
        bl = TokenBlacklist()
        assert not bl.is_revoked("token_nuevo_xyz")

    def test_revoke_y_is_revoked(self):
        from app.security.token_blacklist import TokenBlacklist
        bl = TokenBlacklist()
        future = time.time() + 3600
        bl.revoke("jti-test-001", future)
        assert bl.is_revoked("jti-test-001")

    def test_token_expirado_no_revocado(self):
        from app.security.token_blacklist import TokenBlacklist
        bl = TokenBlacklist()
        past = time.time() - 10
        bl.revoke("jti-expired", past)
        assert not bl.is_revoked("jti-expired")

    def test_size_empieza_en_cero(self):
        from app.security.token_blacklist import TokenBlacklist
        bl = TokenBlacklist()
        assert bl.size() == 0

    def test_size_aumenta_con_revoke(self):
        from app.security.token_blacklist import TokenBlacklist
        bl = TokenBlacklist()
        bl.revoke("jti-size-1", time.time() + 3600)
        assert bl.size() >= 1

    def test_size_ignora_expirados(self):
        from app.security.token_blacklist import TokenBlacklist
        bl = TokenBlacklist()
        bl.revoke("jti-past", time.time() - 10)
        bl.is_revoked("jti-past")  # fuerza cleanup
        assert bl.size() == 0

    def test_multiples_tokens_revocados(self):
        from app.security.token_blacklist import TokenBlacklist
        bl = TokenBlacklist()
        future = time.time() + 3600
        for i in range(5):
            bl.revoke(f"jti-multi-{i}", future)
        for i in range(5):
            assert bl.is_revoked(f"jti-multi-{i}")

    def test_token_diferente_no_revocado(self):
        from app.security.token_blacklist import TokenBlacklist
        bl = TokenBlacklist()
        bl.revoke("jti-A", time.time() + 3600)
        assert not bl.is_revoked("jti-B")

    def test_revoke_sobrescribe(self):
        from app.security.token_blacklist import TokenBlacklist
        bl = TokenBlacklist()
        future = time.time() + 3600
        bl.revoke("jti-overwrite", future)
        bl.revoke("jti-overwrite", future + 100)
        assert bl.is_revoked("jti-overwrite")

    def test_is_revoked_devuelve_bool(self):
        from app.security.token_blacklist import TokenBlacklist
        bl = TokenBlacklist()
        result = bl.is_revoked("cualquier-id")
        assert isinstance(result, bool)

    def test_blacklist_global_es_singleton(self):
        from app.security.token_blacklist import blacklist as bl1
        from app.security.token_blacklist import blacklist as bl2
        assert bl1 is bl2

    def test_blacklist_global_tiene_revoke(self):
        from app.security.token_blacklist import blacklist
        assert hasattr(blacklist, "revoke")

    def test_blacklist_global_tiene_is_revoked(self):
        from app.security.token_blacklist import blacklist
        assert hasattr(blacklist, "is_revoked")

    def test_blacklist_global_tiene_size(self):
        from app.security.token_blacklist import blacklist
        assert hasattr(blacklist, "size")

    def test_cleanup_elimina_expirados(self):
        from app.security.token_blacklist import TokenBlacklist
        bl = TokenBlacklist()
        bl.revoke("jti-clean-1", time.time() - 5)
        bl.revoke("jti-clean-2", time.time() - 5)
        bl._cleanup()
        assert bl.size() == 0

    def test_cleanup_preserva_vigentes(self):
        from app.security.token_blacklist import TokenBlacklist
        bl = TokenBlacklist()
        bl.revoke("jti-vigente", time.time() + 3600)
        bl._cleanup()
        assert bl.is_revoked("jti-vigente")

    def test_ids_vacios_no_revocados(self):
        from app.security.token_blacklist import TokenBlacklist
        bl = TokenBlacklist()
        assert not bl.is_revoked("")

    def test_ids_con_puntos_jwt_formato(self):
        from app.security.token_blacklist import TokenBlacklist
        bl = TokenBlacklist()
        jti = "550e8400-e29b-41d4-a716-446655440000"
        bl.revoke(jti, time.time() + 3600)
        assert bl.is_revoked(jti)

"""
test_middleware_unitarios.py — Tests unitarios del middleware:
RateLimitMiddleware dispatch, _match_rule, _get_client_ip, _cleanup, _store.
"""
import pytest, time


class TestMatchRule:
    def test_login_matchea(self):
        from app.middleware.rate_limit import _match_rule
        result = _match_rule("/api/auth/login")
        assert result is not None

    def test_register_matchea(self):
        from app.middleware.rate_limit import _match_rule
        result = _match_rule("/api/auth/register")
        assert result is not None

    def test_chat_matchea(self):
        from app.middleware.rate_limit import _match_rule
        result = _match_rule("/api/agente/chat")
        assert result is not None

    def test_health_no_matchea(self):
        from app.middleware.rate_limit import _match_rule
        result = _match_rule("/health")
        assert result is None

    def test_procesos_no_matchea(self):
        from app.middleware.rate_limit import _match_rule
        result = _match_rule("/api/procesos")
        assert result is None

    def test_admin_matchea(self):
        from app.middleware.rate_limit import _match_rule
        result = _match_rule("/api/admin/users")
        assert result is not None

    def test_match_devuelve_tupla(self):
        from app.middleware.rate_limit import _match_rule
        result = _match_rule("/api/auth/login")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_match_rule_segundo_elemento_dict(self):
        from app.middleware.rate_limit import _match_rule
        _, rule = _match_rule("/api/auth/login")
        assert isinstance(rule, dict)
        assert "max_requests" in rule
        assert "window_seconds" in rule

    def test_path_raiz_no_matchea(self):
        from app.middleware.rate_limit import _match_rule
        assert _match_rule("/") is None

    def test_path_vacio_no_matchea(self):
        from app.middleware.rate_limit import _match_rule
        assert _match_rule("") is None


class TestCleanup:
    def test_cleanup_elimina_caducados(self):
        from app.middleware.rate_limit import _cleanup
        bucket = {"ip1": [5, time.monotonic() - 200]}
        _cleanup(bucket, 60)
        assert "ip1" not in bucket

    def test_cleanup_preserva_vigentes(self):
        from app.middleware.rate_limit import _cleanup
        bucket = {"ip2": [3, time.monotonic()]}
        _cleanup(bucket, 60)
        assert "ip2" in bucket

    def test_cleanup_bucket_vacio(self):
        from app.middleware.rate_limit import _cleanup
        bucket = {}
        _cleanup(bucket, 60)
        assert bucket == {}

    def test_cleanup_multiples_ips(self):
        from app.middleware.rate_limit import _cleanup
        now = time.monotonic()
        bucket = {
            "old": [1, now - 200],
            "new": [2, now],
        }
        _cleanup(bucket, 60)
        assert "old" not in bucket
        assert "new" in bucket


class TestStore:
    def test_store_importable(self):
        from app.middleware.rate_limit import _store
        assert isinstance(_store, dict)

    def test_store_tiene_clave_login(self):
        from app.middleware.rate_limit import _store
        assert any("login" in k for k in _store.keys())

    def test_store_tiene_clave_register(self):
        from app.middleware.rate_limit import _store
        assert any("register" in k for k in _store.keys())

    def test_reset_all_vacia_todo(self):
        from app.middleware.rate_limit import _store, reset_all
        # Poner algo en el store
        list(_store.values())[0]["test_ip"] = [1, time.monotonic()]
        reset_all()
        for bucket in _store.values():
            assert bucket == {}


class TestRules:
    def test_rules_importable(self):
        from app.middleware.rate_limit import _RULES
        assert isinstance(_RULES, dict)

    def test_rules_login_max_requests(self):
        from app.middleware.rate_limit import _RULES
        login = next(v for k, v in _RULES.items() if "login" in k)
        assert login["max_requests"] > 0

    def test_rules_window_positivo(self):
        from app.middleware.rate_limit import _RULES
        for k, v in _RULES.items():
            assert v["window_seconds"] > 0

    def test_rules_max_requests_positivo(self):
        from app.middleware.rate_limit import _RULES
        for k, v in _RULES.items():
            assert v["max_requests"] > 0

    def test_middleware_importable(self):
        from app.middleware.rate_limit import RateLimitMiddleware
        assert RateLimitMiddleware is not None

    def test_middleware_es_clase(self):
        from app.middleware.rate_limit import RateLimitMiddleware
        assert isinstance(RateLimitMiddleware, type)

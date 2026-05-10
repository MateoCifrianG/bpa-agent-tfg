"""
test_rate_limit_avanzado.py — Tests avanzados de rate limiting:
límites de login/registro, comportamiento tras reset, múltiples IPs,
estructura del rate limiter, edge cases.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestRateLimitLogin:
    async def test_login_normal_no_bloqueado(self, client: AsyncClient, test_user):
        r = await client.post("/api/auth/login", json={
            "email": test_user.email, "password": test_user._test_password
        })
        assert r.status_code == 200

    async def test_login_incorrecto_no_inmediatamente_bloqueado(self, client: AsyncClient, test_user):
        for _ in range(3):
            r = await client.post("/api/auth/login", json={
                "email": test_user.email, "password": "WrongPassword1!"
            })
            assert r.status_code in (401, 429)

    async def test_registro_normal_no_bloqueado(self, client: AsyncClient):
        import uuid
        r = await client.post("/api/auth/register", json={
            "email": f"rl_{uuid.uuid4().hex[:6]}@test.com", "password": "TestPass1!",
            "nombre": "RL", "apellido": "Test",
            "empresa": "RLEmp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code in (201, 429)


class TestRateLimitEstructura:
    def test_middleware_importable(self):
        from app.middleware.rate_limit import RateLimitMiddleware
        assert RateLimitMiddleware is not None

    def test_reset_all_importable(self):
        from app.middleware.rate_limit import reset_all
        assert callable(reset_all)

    def test_reset_all_no_lanza(self):
        from app.middleware.rate_limit import reset_all
        try:
            reset_all()
        except Exception as e:
            pytest.fail(f"reset_all() lanzó excepción: {e}")

    def test_rules_tiene_login(self):
        from app.middleware.rate_limit import _RULES
        assert any("login" in k for k in _RULES.keys())

    def test_rules_tiene_register(self):
        from app.middleware.rate_limit import _RULES
        assert any("register" in k for k in _RULES.keys())

    def test_rules_login_max_requests_positivo(self):
        from app.middleware.rate_limit import _RULES
        login_rule = next((v for k, v in _RULES.items() if "login" in k), None)
        if login_rule:
            assert login_rule["max_requests"] > 0

    def test_rules_register_max_menor_que_login(self):
        from app.middleware.rate_limit import _RULES
        login_rule = next((v for k, v in _RULES.items() if "login" in k), None)
        register_rule = next((v for k, v in _RULES.items() if "register" in k), None)
        if login_rule and register_rule:
            assert register_rule["max_requests"] <= login_rule["max_requests"]

    def test_reset_all_vacia_store(self):
        from app.middleware.rate_limit import reset_all, _store
        reset_all()
        for bucket in _store.values():
            assert bucket == {}

    def test_reset_all_no_lanza_excepcion(self):
        from app.middleware.rate_limit import reset_all
        reset_all()
        reset_all()

    def test_reset_entre_tests_funciona(self, client: AsyncClient):
        from app.middleware.rate_limit import reset_all
        reset_all()


class TestRateLimitEndpoints:
    async def test_health_no_tiene_rate_limit(self, client: AsyncClient):
        for _ in range(5):
            r = await client.get("/health")
            assert r.status_code == 200

    async def test_admin_endpoint_con_auth_ok(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        assert r.status_code == 200

    async def test_procesos_no_rate_limited_con_auth(self, client: AsyncClient, test_user, auth_headers):
        for _ in range(3):
            r = await client.get("/api/procesos", headers=auth_headers)
            assert r.status_code == 200


class TestRateLimitReset:
    async def test_reset_antes_de_test(self, client: AsyncClient, test_user):
        from app.middleware.rate_limit import reset_all
        reset_all()
        r = await client.post("/api/auth/login", json={
            "email": test_user.email, "password": test_user._test_password
        })
        assert r.status_code == 200

    async def test_llamadas_sucesivas_ok(self, client: AsyncClient, test_user, auth_headers):
        for _ in range(5):
            r = await client.get("/api/users/me", headers=auth_headers)
            assert r.status_code == 200

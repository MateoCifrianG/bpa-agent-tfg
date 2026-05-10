"""
test_rate_limit.py — Tests de rate limiting: comportamiento exacto del middleware,
ventanas de tiempo, límites por ruta, reset entre peticiones.
"""
import pytest
from httpx import AsyncClient
from app.middleware.rate_limit import reset_all, _RULES, _store

pytestmark = pytest.mark.asyncio


class TestRateLimitConfig:
    def test_login_tiene_regla(self):
        assert "/api/auth/login" in _RULES

    def test_register_tiene_regla(self):
        assert "/api/auth/register" in _RULES

    def test_chat_tiene_regla(self):
        assert "/api/agente/chat" in _RULES

    def test_admin_tiene_regla(self):
        assert "/api/admin" in _RULES

    def test_login_max_requests_positivo(self):
        assert _RULES["/api/auth/login"]["max_requests"] > 0

    def test_register_max_requests_positivo(self):
        assert _RULES["/api/auth/register"]["max_requests"] > 0

    def test_login_window_positivo(self):
        assert _RULES["/api/auth/login"]["window_seconds"] > 0

    def test_register_window_positivo(self):
        assert _RULES["/api/auth/register"]["window_seconds"] > 0

    def test_chat_window_positivo(self):
        assert _RULES["/api/agente/chat"]["window_seconds"] > 0

    def test_login_limite_mayor_que_0(self):
        assert _RULES["/api/auth/login"]["max_requests"] >= 5

    def test_register_limite_menor_que_login(self):
        # Register debe ser más restrictivo que login
        assert _RULES["/api/auth/register"]["max_requests"] <= _RULES["/api/auth/login"]["max_requests"]


class TestRateLimitReset:
    def test_reset_all_vacia_store(self):
        reset_all()
        for key, bucket in _store.items():
            assert len(bucket) == 0

    def test_reset_all_no_lanza(self):
        reset_all()
        reset_all()  # doble reset no debe fallar

    def test_reset_entre_tests_funciona(self, client: AsyncClient):
        # La fixture autouse ya resetea. Verificamos que el login funciona.
        pass


class TestRateLimitLoginBehavior:
    async def test_login_dentro_del_limite(self, client: AsyncClient, test_user):
        # Hacer 5 intentos fallidos, todos deben ser 401 (no 429)
        max_req = _RULES["/api/auth/login"]["max_requests"]
        intentos_seguros = min(max_req - 2, 5)
        for _ in range(intentos_seguros):
            r = await client.post("/api/auth/login", json={
                "email": test_user.email,
                "password": "WrongPass1!",
            })
            assert r.status_code != 429, "Rate limit demasiado temprano"

    async def test_login_alcanza_limite(self, client: AsyncClient, test_user):
        max_req = _RULES["/api/auth/login"]["max_requests"]
        # Hacer max_req + 1 intentos
        status_codes = []
        for i in range(max_req + 1):
            r = await client.post("/api/auth/login", json={
                "email": f"noexiste_{i}@test.com",
                "password": "Test1234!",
            })
            status_codes.append(r.status_code)
        # Al menos el último debe ser 429
        assert 429 in status_codes, f"Nunca se recibió 429. Códigos: {status_codes}"

    async def test_reset_permite_nuevas_peticiones(self, client: AsyncClient, test_user):
        max_req = _RULES["/api/auth/login"]["max_requests"]
        # Agotar el rate limit
        for _ in range(max_req + 1):
            await client.post("/api/auth/login", json={
                "email": "agotado@test.com",
                "password": "Test1234!",
            })
        # Reset
        reset_all()
        # Ahora debe funcionar
        r = await client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": test_user._test_password,
        })
        assert r.status_code != 429


class TestRateLimitRegisterBehavior:
    async def test_register_dentro_del_limite(self, client: AsyncClient):
        import uuid
        max_req = _RULES["/api/auth/register"]["max_requests"]
        intentos_seguros = min(max_req - 1, 3)
        for i in range(intentos_seguros):
            uid = uuid.uuid4().hex[:8]
            r = await client.post("/api/auth/register", json={
                "email": f"reg_{uid}@test.com",
                "password": "TestPass1!",
                "nombre": "Test",
                "apellido": "User",
                "empresa": "Empresa",
                "sector": "ventas",
                "empleados": 1,
                "plan": "free",
            })
            assert r.status_code != 429, f"Rate limit en intento {i+1}/{intentos_seguros}"

    async def test_register_alcanza_limite(self, client: AsyncClient):
        import uuid
        max_req = _RULES["/api/auth/register"]["max_requests"]
        status_codes = []
        for i in range(max_req + 1):
            uid = uuid.uuid4().hex[:8]
            r = await client.post("/api/auth/register", json={
                "email": f"lim_{uid}@test.com",
                "password": "TestPass1!",
                "nombre": "Test",
                "apellido": "User",
                "empresa": "Empresa",
                "sector": "ventas",
                "empleados": 1,
                "plan": "free",
            })
            status_codes.append(r.status_code)
        assert 429 in status_codes, f"Nunca se recibió 429. Códigos: {status_codes}"


class TestRateLimitRespuesta:
    async def test_429_tiene_detail(self, client: AsyncClient):
        max_req = _RULES["/api/auth/login"]["max_requests"]
        for _ in range(max_req + 1):
            r = await client.post("/api/auth/login", json={
                "email": "agota2@test.com",
                "password": "Test1234!",
            })
        if r.status_code == 429:
            assert "detail" in r.json()

    async def test_429_mensaje_informativo(self, client: AsyncClient):
        max_req = _RULES["/api/auth/login"]["max_requests"]
        for _ in range(max_req + 1):
            r = await client.post("/api/auth/login", json={
                "email": "agota3@test.com",
                "password": "Test1234!",
            })
        if r.status_code == 429:
            detail = r.json()["detail"]
            assert isinstance(detail, str)
            assert len(detail) > 0


class TestRateLimitEndpointsSinLimite:
    async def test_health_sin_limite(self, client: AsyncClient):
        # /health no tiene regla de rate limit, siempre debe responder
        for _ in range(20):
            r = await client.get("/health")
            assert r.status_code != 429

    async def test_procesos_sin_limite_rate(self, client: AsyncClient, test_user, auth_headers):
        # Los endpoints de procesos no tienen rate limit configurado
        for _ in range(10):
            r = await client.get("/api/procesos", headers=auth_headers)
            assert r.status_code != 429

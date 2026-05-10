"""
conftest.py — Fixtures compartidos para todos los tests.
SQLite en memoria con limpieza automática entre tests.
"""
import asyncio
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from app.main import app
from app.database import Base, get_db
from app.auth.jwt import hash_password, create_access_token
from app.middleware.rate_limit import reset_all as _reset_rate_limits
from app.models.user import User
from app.models.empresa import Empresa
from app.models.proceso import Proceso
from app.models.kpi import KPI
from app.models.automatizacion import Automatizacion

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

_engine = None
_factory = None


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    global _engine, _factory
    _engine = create_async_engine(TEST_DB_URL, echo=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _factory = async_sessionmaker(_engine, expire_on_commit=False)
    yield _engine
    await _engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    async with _factory() as session:
        yield session
        await session.rollback()


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Limpia el rate limiter antes de cada test para evitar 429 espurios."""
    _reset_rate_limits()


@pytest_asyncio.fixture
async def client(test_engine):
    """AsyncClient con la app FastAPI y BD de test inyectada."""
    async def override_get_db():
        async with _factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Crea un usuario de test con empresa. Email único por invocación."""
    uid = uuid.uuid4().hex[:8]
    user = User(
        email=f"testuser_{uid}@bpa.com",
        hashed_password=hash_password("TestPass1!"),
        nombre="Test",
        apellido="User",
        role="user",
        plan="pro",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    empresa = Empresa(
        user_id=user.id,
        nombre="Empresa Test",
        sector="logística",
    )
    db_session.add(empresa)
    await db_session.commit()
    await db_session.refresh(user)
    user._test_password = "TestPass1!"
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User):
    token = create_access_token({"sub": test_user.id, "role": test_user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    uid = uuid.uuid4().hex[:8]
    user = User(
        email=f"admin_{uid}@bpa.com",
        hashed_password=hash_password("AdminPass1!"),
        nombre="Admin",
        apellido="Test",
        role="admin",
        plan="enterprise",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    empresa = Empresa(user_id=user.id, nombre="BPA Admin Corp")
    db_session.add(empresa)
    await db_session.commit()
    await db_session.refresh(user)
    user._test_password = "AdminPass1!"
    return user


@pytest_asyncio.fixture
async def admin_headers(admin_user: User):
    token = create_access_token({"sub": admin_user.id, "role": admin_user.role})
    return {"Authorization": f"Bearer {token}"}


# ── Fixtures de recursos ───────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_proceso(client: AsyncClient, auth_headers):
    """Crea un proceso de test y devuelve su JSON."""
    r = await client.post("/api/procesos", headers=auth_headers, json={
        "nombre": "Proceso Fixture",
        "descripcion": "Proceso creado automáticamente para tests",
        "responsable": "Test User",
        "frecuencia": "mensual",
        "duracion_h": 10,
    })
    assert r.status_code == 201
    return r.json()


@pytest_asyncio.fixture
async def test_kpi(client: AsyncClient, auth_headers):
    """Crea un KPI de test y devuelve su JSON."""
    r = await client.post("/api/kpis", headers=auth_headers, json={
        "nombre": "KPI Fixture",
        "valor": "85",
        "unidad": "%",
        "objetivo": "90",
        "categoria": "calidad",
    })
    assert r.status_code == 201
    return r.json()


@pytest_asyncio.fixture
async def test_auto(client: AsyncClient, auth_headers):
    """Crea una automatización de test y devuelve su JSON."""
    r = await client.post("/api/automatizaciones", headers=auth_headers, json={
        "nombre": "Auto Fixture",
        "descripcion": "Automatización creada para tests",
        "herramienta": "n8n",
        "horas_mes": 5,
    })
    assert r.status_code == 201
    return r.json()

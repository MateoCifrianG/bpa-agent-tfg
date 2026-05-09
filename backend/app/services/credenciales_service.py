"""
Servicio para cifrar/descifrar credenciales MCP con Fernet.
NUNCA devuelve el valor en claro en las respuestas de la API.
"""
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.credencial import Credencial
from app.config import settings


def _get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY
    if not key:
        raise RuntimeError("ENCRYPTION_KEY no configurada. Ejecuta: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
    return Fernet(key.encode() if isinstance(key, str) else key)


def cifrar(valor: str) -> str:
    return _get_fernet().encrypt(valor.encode()).decode()


def descifrar(valor_cifrado: str) -> str:
    try:
        return _get_fernet().decrypt(valor_cifrado.encode()).decode()
    except InvalidToken:
        raise ValueError("No se pudo descifrar la credencial. Clave incorrecta o dato corrupto.")


async def guardar_credencial(db: AsyncSession, empresa_id: str, servicio: str, token: str) -> Credencial:
    # Buscar si ya existe para ese servicio+empresa
    result = await db.execute(
        select(Credencial).where(
            Credencial.empresa_id == empresa_id,
            Credencial.servicio == servicio
        )
    )
    cred = result.scalar_one_or_none()

    valor_cifrado = cifrar(token)

    if cred:
        cred.valor_cifrado = valor_cifrado
    else:
        cred = Credencial(
            empresa_id=empresa_id,
            servicio=servicio,
            valor_cifrado=valor_cifrado,
        )
        db.add(cred)

    await db.commit()
    await db.refresh(cred)
    return cred


async def obtener_credencial(db: AsyncSession, empresa_id: str, servicio: str) -> str | None:
    """Devuelve el token en claro solo en memoria, nunca persiste ni loguea."""
    result = await db.execute(
        select(Credencial).where(
            Credencial.empresa_id == empresa_id,
            Credencial.servicio == servicio
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        return None
    return descifrar(cred.valor_cifrado)


async def eliminar_credencial(db: AsyncSession, empresa_id: str, servicio: str) -> bool:
    result = await db.execute(
        select(Credencial).where(
            Credencial.empresa_id == empresa_id,
            Credencial.servicio == servicio
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        return False
    await db.delete(cred)
    await db.commit()
    return True

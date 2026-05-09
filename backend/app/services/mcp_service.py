"""
Servicio MCP (Model Context Protocol) para llamadas a servidores externos.
SEGURIDAD: Recupera tokens de BD cifrada, nunca hardcodeados.
"""
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.services import credenciales_service


async def ejecutar_via_mcp(
    servidor: str,
    herramienta: str,
    parametros: dict,
    empresa_id: str,
    db: AsyncSession,
) -> dict:
    """
    Ejecuta una herramienta en un servidor MCP.
    Recupera el token OAuth de la BD cifrada y lo pasa como Bearer.
    """
    # Obtener credencial descifrada en memoria (nunca se persiste en claro)
    token = await credenciales_service.obtener_credencial(db, empresa_id, servidor)
    if not token:
        raise ValueError(f"No hay credencial configurada para el servicio '{servidor}'. Configúrala en Integraciones.")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",  # token OAuth descifrado, solo en memoria
    }

    # TODO: Sustituir por URL real del servidor MCP según el servicio
    mcp_urls = {
        "gmail":    "https://mcp.gmail.com/execute",
        "drive":    "https://mcp.drive.com/execute",
        "calendar": "https://mcp.calendar.com/execute",
        "n8n":      "http://localhost:5678/mcp/execute",
    }

    url = mcp_urls.get(servidor)
    if not url:
        raise ValueError(f"Servidor MCP '{servidor}' no soportado.")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json={
            "tool": herramienta,
            "parameters": parametros,
        }, headers=headers)
        response.raise_for_status()
        return response.json()

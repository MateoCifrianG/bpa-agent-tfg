"""
BPA-Agent — Verificador de entorno.
Ejecutar: python scripts/check_env.py
"""
import sys
import os
import base64

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REQUIRED = {
    "DATABASE_URL":                ("sqlite+aiosqlite", "URL de la base de datos"),
    "SECRET_KEY":                  ("dev-secret-key", "Clave JWT (cambiar en producción)"),
    "ANTHROPIC_API_KEY":           ("",                "API Key de Claude (requerida para el agente)"),
    "ENCRYPTION_KEY":              ("",                "Clave Fernet para cifrar credenciales MCP"),
}

def check_fernet_key(key: str) -> bool:
    try:
        decoded = base64.urlsafe_b64decode(key.encode())
        return len(decoded) == 32
    except Exception:
        return False

def main():
    print("\n=== BPA-Agent check_env ===\n")
    ok = True

    for var, (default, desc) in REQUIRED.items():
        val = os.environ.get(var, default)
        if not val:
            print(f"[FALTA]  {var} — {desc}")
            ok = False
        elif var == "ENCRYPTION_KEY":
            if check_fernet_key(val):
                print(f"[OK]     {var} — Clave Fernet valida (32 bytes)")
            else:
                print(f"[ERROR]  {var} — Formato Fernet invalido. Genera una con:")
                print(f"         python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
                ok = False
        elif var == "SECRET_KEY" and "dev-secret-key" in val:
            print(f"[WARN]   {var} — Usando clave de desarrollo. Cambiar en produccion.")
        elif var == "ANTHROPIC_API_KEY" and not val:
            print(f"[WARN]   {var} — No configurada. El agente IA no funcionara.")
        else:
            masked = val[:6] + "..." if len(val) > 6 else "***"
            print(f"[OK]     {var} = {masked}")

    print()
    if ok:
        print("Todo OK. Listo para desarrollar.")
    else:
        print("Hay variables faltantes. Crea un archivo .env basandote en .env.example")
    print()
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())

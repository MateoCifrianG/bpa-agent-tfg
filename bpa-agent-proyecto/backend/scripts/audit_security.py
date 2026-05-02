"""
BPA-Agent — Auditoría de seguridad.
Ejecutar: python scripts/audit_security.py
"""
import sys, os, base64, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_fernet(key):
    try:
        return len(base64.urlsafe_b64decode(key.encode())) == 32
    except:
        return False

def main():
    print("\n=== BPA-Agent audit_security ===\n")
    issues = []

    # 1. Variables de entorno críticas
    for var in ["ANTHROPIC_API_KEY", "DATABASE_URL", "SECRET_KEY", "ENCRYPTION_KEY"]:
        val = os.environ.get(var, "")
        if not val:
            issues.append(f"CRITICO: {var} no configurada")
        elif var == "ENCRYPTION_KEY" and not check_fernet(val):
            issues.append(f"CRITICO: ENCRYPTION_KEY con formato Fernet invalido")
        elif var == "SECRET_KEY" and "dev-secret" in val:
            issues.append(f"MEDIO: SECRET_KEY es la clave de desarrollo — cambiar en prod")

    # 2. Verificar que no hay credenciales hardcodeadas en el código
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    credential_patterns = [
        r'password\s*=\s*["\'][^"\']{8,}["\']',
        r'api_key\s*=\s*["\'][^"\']{10,}["\']',
        r'secret\s*=\s*["\'][^"\']{10,}["\']',
        r'sk-[A-Za-z0-9]{32,}',
        r'ghp_[A-Za-z0-9]{36}',
    ]
    compiled = [re.compile(p, re.IGNORECASE) for p in credential_patterns]

    for root, dirs, files in os.walk(backend_dir):
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.venv', 'venv', '.git']]
        for fname in files:
            if not fname.endswith('.py'):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f, 1):
                    for pat in compiled:
                        if pat.search(line) and 'audit_security' not in fpath:
                            rel = os.path.relpath(fpath, backend_dir)
                            issues.append(f"BAJO: Posible credencial hardcodeada en {rel}:{i}")

    # 3. Verificar .env no commiteado
    env_file = os.path.join(backend_dir, '.env')
    gitignore = os.path.join(os.path.dirname(backend_dir), '.gitignore')
    if os.path.exists(env_file):
        if os.path.exists(gitignore):
            with open(gitignore) as f:
                if '.env' not in f.read():
                    issues.append("CRITICO: .env existe pero no está en .gitignore")
        else:
            issues.append("MEDIO: .env existe pero no hay .gitignore")

    # Resultado
    if not issues:
        print("[OK] Sin problemas de seguridad detectados.\n")
    else:
        for issue in issues:
            prefix = "[CRITICO]" if "CRITICO" in issue else "[MEDIO]" if "MEDIO" in issue else "[BAJO]"
            print(f"{prefix} {issue.split(':', 1)[-1].strip()}")
        print(f"\nTotal: {len(issues)} problema(s) encontrado(s).")
    print()

if __name__ == "__main__":
    main()

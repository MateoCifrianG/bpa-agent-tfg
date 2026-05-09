"""
token_blacklist.py — Blacklist de tokens JWT revocados.
Almacén en memoria con limpieza automática de tokens expirados.
En producción con múltiples workers reemplazar por Redis.
"""

import threading
import time
from typing import Optional


class TokenBlacklist:
    """
    Almacena tokens revocados con su tiempo de expiración.
    Estructura: { jti_or_token_hash: expires_at_timestamp }
    """

    def __init__(self):
        self._store: dict[str, float] = {}
        self._lock = threading.Lock()

    def revoke(self, token_id: str, expires_at: float) -> None:
        """Revoca un token identificado por su jti o hash. expires_at = unix timestamp."""
        with self._lock:
            self._store[token_id] = expires_at
            self._cleanup()

    def is_revoked(self, token_id: str) -> bool:
        with self._lock:
            exp = self._store.get(token_id)
            if exp is None:
                return False
            if time.time() > exp:
                del self._store[token_id]
                return False
            return True

    def _cleanup(self) -> None:
        now = time.time()
        expired = [tid for tid, exp in self._store.items() if now > exp]
        for tid in expired:
            del self._store[tid]

    def size(self) -> int:
        with self._lock:
            return len(self._store)


# Instancia global
blacklist = TokenBlacklist()

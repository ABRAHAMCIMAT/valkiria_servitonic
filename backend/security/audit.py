"""
Audit trail inmutable (append-only JSONL) para acciones sensibles (Fase 0).

Registra quien hizo que, cuando y con que resultado. El actor se identifica
por el hash de su credencial (key_id), nunca por la clave. El archivo es
append-only; la rotacion se gestiona fuera del proceso (logrotate).
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
import threading
from datetime import UTC, datetime

_lock = threading.Lock()


class AuditLog:
    def __init__(self, path: str | None = None):
        if path is None:
            from ..config import AUDIT_LOG

            path = AUDIT_LOG
        self.path = path

    def record(
        self, *, action: str, actor: str, target: str = "", outcome: str = "ok", metadata: dict | None = None
    ) -> None:
        """Escribe una entrada de auditoria. Nunca lanza excepciones."""
        entry = {
            "ts": datetime.now(UTC).isoformat(),
            "action": action,
            "actor": actor,
            "target": target,
            "outcome": outcome,
            "metadata": metadata or {},
        }
        from .. import config

        if config.STRUCTURED_STDOUT:
            # Cloud Logging: un sink filtra log_type="audit" hacia un bucket
            # con retencion larga (infra/terraform/logging.tf)
            with contextlib.suppress(Exception):
                line = {"severity": "NOTICE", "log_type": "audit", "message": f"audit {action}", **entry}
                sys.stdout.write(json.dumps(line, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        if not self.path:
            return
        with _lock:
            try:
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
                with open(self.path, "a") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception:
                pass  # la auditoria nunca debe romper el flujo


_log: AuditLog | None = None


def get_audit_log() -> AuditLog:
    global _log
    if _log is None:
        _log = AuditLog()
    return _log

"""
Redaccion de PII para logs y telemetria (Fase 0).

Detecta y enmascara correos, telefonos, tarjetas, IPs y SSN antes de escribir
cualquier traza. El texto crudo del usuario nunca se persiste en logs.
"""

from __future__ import annotations

import re

# El ORDEN importa: los patrones especificos se evaluan antes que el generico
# de telefono (voraz), de lo contrario una tarjeta, una IPv4 o un SSN se
# etiquetarian como "phone". Regresion cubierta en tests/unit/test_security_redaction.py
_PATTERNS = [
    # Credenciales que accidentalmente aparezcan dentro de mensajes de error.
    # Los valores estructurados se cubren además con `sanitize_for_logging`.
    ("credential", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")),
    (
        "credential",
        re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*[^\s,;]+"),
    ),
    ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("ssn", re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")),
    ("card", re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")),
    ("ipv4", re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")),
    ("phone", re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")),
]

_PLACEHOLDER = "[REDACTED:{kind}]"


class Redactor:
    """Aplica una cadena de expresiones de redaccion sobre texto libre."""

    def __init__(self, extra_patterns=None):
        self._patterns = _PATTERNS + (extra_patterns or [])

    def redact(self, text: str) -> str:
        if not text:
            return text
        out = text
        for kind, rx in self._patterns:
            out = rx.sub(_PLACEHOLDER.format(kind=kind), out)
        return out

    def summary(self, text: str, max_len: int = 120) -> str:
        """Resumen seguro para logs: redacta y trunca."""
        safe = self.redact(text)
        return safe[:max_len] + ("..." if len(safe) > max_len else "")


_default = Redactor()


def redact_text(text: str) -> str:
    """Redacta PII en un texto completo."""
    return _default.redact(text)


_SENSITIVE_FIELDS = {
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
    "webhook_url",
}
_SENSITIVE_FIELD_SUFFIXES = (
    "_api_key",
    "_apikey",
    "_authorization",
    "_cookie",
    "_credential",
    "_password",
    "_secret",
    "_token",
    "_webhook_url",
)


def sanitize_for_logging(value, field_name: str = ""):
    """Redacta PII y secretos en estructuras destinadas a logs.

    Los secretos arbitrarios no siempre tienen un patrón reconocible. Por eso,
    además de redactar texto, cualquier valor bajo una clave sensible se omite
    por completo. Se aplica recursivamente a diccionarios y listas.
    """
    normalized = field_name.strip().lower().replace("-", "_")
    if normalized in _SENSITIVE_FIELDS or normalized.endswith(_SENSITIVE_FIELD_SUFFIXES):
        return "[REDACTED:secret]"
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {key: sanitize_for_logging(item, str(key)) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_for_logging(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_for_logging(item) for item in value)
    return value


def redact(text: str, max_len: int = 120) -> str:
    """Redacta PII y trunca: uso directo en logs."""
    return _default.summary(text, max_len)


_TRUE = ("1", "true", "yes", "on")


def log_user_content_enabled() -> bool:
    """Indica si se permite registrar contenido del usuario (opt-in)."""
    import os

    return os.getenv("LOG_USER_CONTENT", "false").strip().lower() in _TRUE


def preview(text: str, max_len: int = 120) -> str:
    """Texto seguro para logs.

    Por defecto el contenido del usuario NO se registra (privacidad primero).
    Si LOG_USER_CONTENT=true, se registra redactado de PII y truncado.
    """
    if not log_user_content_enabled():
        return "[contenido del usuario omitido]"
    return _default.summary(text, max_len)

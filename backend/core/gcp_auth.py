"""
Tokens de acceso de Google Cloud para Vertex AI (Fase 2, I2).

El endpoint compatible con OpenAI de Vertex AI no acepta API keys: exige un
token OAuth de Google que expira en ~1 hora. `GoogleTokenProvider` lo obtiene
con Application Default Credentials (ADC):
  * en Cloud Run: la cuenta de servicio del servicio, sin archivos de llaves;
  * en local:     `gcloud auth application-default login`.

El token se cachea y se renueva antes de expirar; es seguro entre hilos
(FastAPI atiende las rutas síncronas en un pool de hilos).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
REFRESH_MARGIN = timedelta(minutes=5)


class GoogleTokenProvider:
    def __init__(self, credentials_factory: Callable[[], Any] | None = None):
        self._factory = credentials_factory or _adc_credentials
        self._credentials: Any = None
        self._lock = threading.Lock()

    def _needs_refresh(self) -> bool:
        creds = self._credentials
        if creds is None or not creds.token:
            return True
        expiry: datetime | None = creds.expiry
        if expiry is None:
            return False
        # google-auth expresa `expiry` como datetime UTC "naive"
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=UTC)
        return datetime.now(UTC) >= expiry - REFRESH_MARGIN

    def token(self) -> str:
        with self._lock:
            if self._credentials is None:
                self._credentials = self._factory()
            if self._needs_refresh():
                from google.auth.transport.requests import Request

                self._credentials.refresh(Request())
            return str(self._credentials.token)


def _adc_credentials() -> Any:
    import google.auth  # import diferido: solo se necesita con LLM_PROVIDER=vertex

    credentials, _project = google.auth.default(scopes=[CLOUD_PLATFORM_SCOPE])
    return credentials


def default_project() -> str:
    """Proyecto de ADC (útil en Cloud Run, donde no hace falta configurarlo)."""
    import google.auth

    _credentials, project = google.auth.default(scopes=[CLOUD_PLATFORM_SCOPE])
    return project or ""

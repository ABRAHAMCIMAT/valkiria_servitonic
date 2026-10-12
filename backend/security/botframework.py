"""
Validación de las llamadas del Bot Framework a /api/teams/messages (Fase 2, I7.b).

Ese endpoint no usa las API keys de Fase 0: quien llama es el servicio de
Microsoft, que firma cada solicitud con un JWT. Se verifica:
  * firma RS256 con las claves públicas publicadas por Bot Framework (JWKS),
  * emisor  = https://api.botframework.com,
  * audiencia = el App ID de nuestro bot,
  * vigencia (exp / nbf),
  * que el claim `serviceurl` coincida con el `serviceUrl` de la actividad.

Referencia: "Authenticate requests from the Bot Connector service to your bot".
"""

from __future__ import annotations

import threading
from typing import Any

import httpx
import jwt
from fastapi import HTTPException, status

OPENID_CONFIG_URL = "https://login.botframework.com/v1/.well-known/openidconfiguration"
ISSUER = "https://api.botframework.com"
LEEWAY_SECONDS = 300  # tolerancia de reloj recomendada por Microsoft


class BotAuthError(HTTPException):
    def __init__(self, detail: str = "Token de Bot Framework inválido"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class BotFrameworkAuth:
    def __init__(self, app_id: str, jwks_client: Any | None = None):
        self.app_id = app_id
        self._jwks_client = jwks_client
        self._lock = threading.Lock()

    def _jwks(self) -> Any:
        with self._lock:
            if self._jwks_client is None:
                cfg = httpx.get(OPENID_CONFIG_URL, timeout=10.0).json()
                self._jwks_client = jwt.PyJWKClient(cfg["jwks_uri"], cache_keys=True, lifespan=86400)
            return self._jwks_client

    def verify(self, authorization: str | None, service_url: str | None = None) -> dict:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise BotAuthError("Falta el token de Bot Framework.")
        token = authorization[7:].strip()
        try:
            key = self._jwks().get_signing_key_from_jwt(token).key
            claims: dict = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.app_id,
                issuer=ISSUER,
                leeway=LEEWAY_SECONDS,
                options={"require": ["exp", "iss", "aud"]},
            )
        except (jwt.PyJWTError, httpx.HTTPError, KeyError) as e:
            raise BotAuthError(f"Token de Bot Framework inválido: {type(e).__name__}") from e
        claimed = claims.get("serviceurl") or claims.get("serviceUrl")
        if service_url and claimed and claimed.rstrip("/") != service_url.rstrip("/"):
            raise BotAuthError("serviceUrl no coincide con el token.")
        return claims

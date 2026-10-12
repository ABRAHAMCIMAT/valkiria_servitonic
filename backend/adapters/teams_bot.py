"""
Cliente del bot de Microsoft Teams (Bot Framework) — Fase 2, I7.b.

Envía mensajes proactivos 1:1 (la tarjeta de aprobación al manager) a través
de la Bot Connector API, y resuelve el usuario de Teams a partir de su correo
con Microsoft Graph. Usa el registro de la app en Entra ID (single-tenant):

  TEAMS_BOT_APP_ID        ID de la aplicación (cliente) en Entra ID
  TEAMS_BOT_APP_PASSWORD  secreto de cliente (Secret Manager)
  TEAMS_TENANT_ID         tenant de Microsoft 365
  TEAMS_SERVICE_URL       Bot Connector de Teams (por defecto el global)

Requisitos fuera del código (docs/integraciones/TEAMS.md): Azure Bot con el
endpoint de mensajería apuntando a /api/teams/messages, la app de Teams
instalada para los managers y el permiso de aplicación de Graph User.Read.All.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from ..llmops.errors import ProviderError, RetryableError, retry
from ..llmops.logging import get_logger
from . import teams_cards

log = get_logger("adapter.teams_bot")

BOT_SCOPE = "https://api.botframework.com/.default"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"
GRAPH_URL = "https://graph.microsoft.com/v1.0"
DEFAULT_SERVICE_URL = "https://smba.trafficmanager.net/teams/"


@dataclass
class BotConfig:
    app_id: str = ""
    app_password: str = ""
    tenant_id: str = ""
    service_url: str = DEFAULT_SERVICE_URL

    @classmethod
    def from_env(cls) -> BotConfig:
        service_url = os.getenv("TEAMS_SERVICE_URL", "") or DEFAULT_SERVICE_URL
        return cls(
            app_id=os.getenv("TEAMS_BOT_APP_ID", ""),
            app_password=os.getenv("TEAMS_BOT_APP_PASSWORD", ""),
            tenant_id=os.getenv("TEAMS_TENANT_ID", ""),
            service_url=service_url if service_url.endswith("/") else service_url + "/",
        )

    @property
    def configured(self) -> bool:
        return bool(self.app_id and self.app_password and self.tenant_id)


class TeamsBotClient:
    def __init__(self, config: BotConfig | None = None, client: httpx.Client | None = None):
        self.config = config or BotConfig.from_env()
        self._client = client or httpx.Client(timeout=20.0)
        self._tokens: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()

    @property
    def configured(self) -> bool:
        return self.config.configured

    # -- autenticación (client credentials) ----------------------------------
    def _token(self, scope: str) -> str:
        with self._lock:
            cached = self._tokens.get(scope)
            if cached and cached[1] - time.time() > 300:
                return cached[0]
        url = f"https://login.microsoftonline.com/{self.config.tenant_id}/oauth2/v2.0/token"
        resp = self._send(
            "POST",
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.config.app_id,
                "client_secret": self.config.app_password,
                "scope": scope,
            },
        )
        data = resp.json()
        token = str(data["access_token"])
        with self._lock:
            self._tokens[scope] = (token, time.time() + int(data.get("expires_in", 3600)))
        return token

    def _send(self, method: str, url: str, token: str | None = None, **kw) -> httpx.Response:
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        def _call() -> httpx.Response:
            try:
                resp = self._client.request(method, url, headers=headers, **kw)
            except httpx.TransportError as e:
                raise RetryableError(f"error de red hacia Microsoft: {e}") from e
            if resp.status_code == 429 or resp.status_code >= 500:
                raise RetryableError(f"Microsoft devolvió {resp.status_code}")
            if resp.status_code >= 400:
                raise ProviderError(f"Microsoft devolvió {resp.status_code}: {resp.text[:300]}")
            return resp

        return retry(_call, max_attempts=3, base_delay=0.5, max_delay=8.0, logger=log)

    # -- Graph: correo → ID de Entra ID ---------------------------------------
    def resolve_user_id(self, email: str) -> str:
        resp = self._send(
            "GET",
            f"{GRAPH_URL}/users/{quote(email)}",
            token=self._token(GRAPH_SCOPE),
            params={"$select": "id"},
        )
        return str(resp.json()["id"])

    # -- mensajes proactivos --------------------------------------------------
    def send_card_to_user(self, aad_object_id: str, card: dict) -> dict[str, Any]:
        """Abre (o reutiliza) la conversación 1:1 del bot con el usuario y
        publica la tarjeta. Devuelve los IDs para poder rastrearla."""
        token = self._token(BOT_SCOPE)
        base = self.config.service_url
        conv = self._send(
            "POST",
            f"{base}v3/conversations",
            token=token,
            json={
                "bot": {"id": f"28:{self.config.app_id}"},
                "members": [{"id": aad_object_id}],
                "channelData": {"tenant": {"id": self.config.tenant_id}},
                "tenantId": self.config.tenant_id,
                "isGroup": False,
            },
        ).json()
        conversation_id = conv["id"]
        activity = self._send(
            "POST",
            f"{base}v3/conversations/{quote(conversation_id, safe='')}/activities",
            token=token,
            json={"type": "message", "attachments": [teams_cards.attachment(card)]},
        ).json()
        return {"conversation_id": conversation_id, "activity_id": activity.get("id", "")}

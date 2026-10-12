"""
Notificaciones por Microsoft Teams (Fase 2, I7) — sustituye a Slack.

Tres modos de entrega, de más a menos completo:

  * bot      — TEAMS_BOT_* configurado (adapters/teams_bot.py). La aprobación
               llega 1:1 al manager con botones Aprobar/Rechazar; su respuesta
               vuelve a /api/teams/messages y reanuda la conversación.
  * workflow — TEAMS_WORKFLOW_URL configurado: webhook de Workflows (Power
               Automate, "When a Teams webhook request is received") que
               publica la tarjeta en un canal. Sin botones: la decisión se
               registra con POST /api/approvals/{id}/decision.
  * demo     — nada configurado: no se envía nada, solo se registra.

Los Incoming Webhooks de Office 365 (TEAMS_WEBHOOK_URL) se retiraron; si solo
existe esa variable se usa como URL de Workflows, que acepta el mismo POST con
el formato de Adaptive Card de abajo.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import httpx

from .. import config
from ..llmops.errors import LLMOpsError
from ..llmops.logging import get_logger
from . import teams_cards
from .teams_bot import TeamsBotClient

if TYPE_CHECKING:
    from ..core.approvals import ApprovalRequest

log = get_logger("adapter.teams")


class TeamsNotifier:
    channel = "teams"

    def __init__(self, bot: TeamsBotClient | None = None, client: httpx.Client | None = None):
        self.workflow_url = os.getenv("TEAMS_WORKFLOW_URL", "") or os.getenv("TEAMS_WEBHOOK_URL", "")
        self.bot = bot or TeamsBotClient()
        self.live = bool(self.workflow_url or self.bot.configured)
        if config.IS_PRODUCTION and not self.live:
            raise RuntimeError(
                "NOTIFY_CHANNEL='teams' requiere TEAMS_BOT_* o TEAMS_WORKFLOW_URL en produccion."
            )
        self._client = client or httpx.Client(timeout=20.0)

    @property
    def mode(self) -> str:
        if self.bot.configured:
            return "bot"
        return "workflow" if self.workflow_url else "demo"

    # -- entrega --------------------------------------------------------------
    def _post_workflow(self, card: dict) -> dict:
        if not self.workflow_url:
            return {"success": True, "delivered": "demo"}
        try:
            resp = self._client.post(
                self.workflow_url, json={"type": "message", "attachments": [teams_cards.attachment(card)]}
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("no se pudo publicar en Teams (Workflows)", extra={"error": str(e)})
            return {"success": False, "error": str(e), "delivered": "workflow"}
        return {"success": True, "delivered": "workflow"}

    def _result(self, delivery: dict, to: str, subject: str, body: str) -> dict:
        return {"channel": self.channel, "to": to, "subject": subject, "body": body, **delivery}

    # -- NotifierPort ---------------------------------------------------------
    def send(self, to: str, subject: str, body: str, channel: str | None = None) -> dict:
        delivery = self._post_workflow(teams_cards.message_card(subject, body))
        return self._result(delivery, to, subject, body)

    def send_approval_request(
        self,
        manager: str,
        resource: str,
        ticket_number: str,
        channel: str | None = None,
        approval: ApprovalRequest | None = None,
    ) -> dict:
        subject = f"🔔 Aprobación requerida: {resource}"
        body = f"Ticket: {ticket_number}"
        if approval is None:
            return self.send(manager, subject, body)

        if self.bot.configured and approval.manager_email:
            try:
                if not approval.manager_aad_id:
                    approval.manager_aad_id = self.bot.resolve_user_id(approval.manager_email)
                ids = self.bot.send_card_to_user(
                    approval.manager_aad_id, teams_cards.approval_card(approval, interactive=True)
                )
                return self._result(
                    {"success": True, "delivered": "bot", "interactive": True, **ids}, manager, subject, body
                )
            except (LLMOpsError, KeyError, ValueError) as e:
                # Sin bot no hay botones, pero la solicitud no se pierde: cae a
                # Workflows (si existe) y se resuelve por la API de aprobaciones.
                log.warning("no se pudo enviar la aprobación por el bot", extra={"error": str(e)})

        delivery = self._post_workflow(teams_cards.approval_card(approval, interactive=False))
        return self._result({**delivery, "interactive": False}, manager, subject, body)

    def send_ticket_update(
        self, user: str, ticket_number: str, state: str, note: str, channel: str | None = None
    ) -> dict:
        subject = f"🔄 Actualización de tu ticket {ticket_number}"
        delivery = self._post_workflow(teams_cards.ticket_update_card(ticket_number, state, note))
        return self._result(delivery, user, subject, f"Estado: {state}\n{note}")

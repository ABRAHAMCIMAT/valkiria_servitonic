"""
Puertos (interfaces) de los sistemas externos.

Mismo enfoque que `core/storage.py`: contratos con tipado estructural
(`typing.Protocol`), sin herencia. Los agentes dependen de estas interfaces y
no de una clase concreta, de modo que el sistema de tickets (ServiceNow hoy,
ServiceTonic después — ver docs/PLAN_FASE2_GOOGLE_CLOUD.md, I1/I5) o el canal
de notificaciones (Slack, Teams) se cambian con una variable de entorno, sin
tocar los agentes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from ..core.models import Ticket

if TYPE_CHECKING:
    from ..core.approvals import ApprovalRequest


@runtime_checkable
class TicketingPort(Protocol):
    """Sistema de registro de tickets, base de conocimiento y organigrama."""

    live: bool

    # -- tickets --------------------------------------------------------------
    def create_incident(self, ticket: Ticket) -> Ticket: ...
    def update_incident(self, ticket: Ticket, fields: dict) -> Ticket: ...
    def get_incident(self, number: str) -> Ticket | None: ...
    def list_tickets(self, caller: str, limit: int = 5) -> list[Ticket]: ...

    # -- conocimiento y organización -----------------------------------------
    def search_kb(self, query: str, top_k: int = 3) -> list[dict]: ...
    def get_manager(self, employee: str) -> dict | None: ...

    # -- autoservicio ---------------------------------------------------------
    def unlock_account(self, target: str) -> dict: ...
    def reset_password(self, target: str) -> dict: ...
    def assign_license(self, software: str, user: str) -> dict: ...


@runtime_checkable
class NotifierPort(Protocol):
    """Canal de notificaciones (aprobaciones y actualizaciones de ticket)."""

    channel: str
    live: bool

    def send(self, to: str, subject: str, body: str, channel: str | None = None) -> dict: ...

    def send_approval_request(
        self,
        manager: str,
        resource: str,
        ticket_number: str,
        channel: str | None = None,
        approval: ApprovalRequest | None = None,
    ) -> dict: ...

    def send_ticket_update(
        self, user: str, ticket_number: str, state: str, note: str, channel: str | None = None
    ) -> dict: ...

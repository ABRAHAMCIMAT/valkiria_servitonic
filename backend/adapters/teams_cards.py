"""
Adaptive Cards para Microsoft Teams (Fase 2, I7).

Funciones puras que devuelven el JSON de cada tarjeta (esquema 1.5). La
tarjeta de aprobación usa `Action.Execute` (Universal Actions): el clic llega
al bot como una invocación `adaptiveCard/action` (ver server.py,
/api/teams/messages) y el bot responde con la misma tarjeta ya resuelta.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.approvals import ApprovalRequest

CARD_CONTENT_TYPE = "application/vnd.microsoft.card.adaptive"
SCHEMA = "http://adaptivecards.io/schemas/adaptive-card.json"
VERSION = "1.5"

VERB_APPROVE = "approve"
VERB_REJECT = "reject"

_STATUS_TEXT = {
    "approved": ("✅ Aprobada", "Good"),
    "rejected": ("❌ Rechazada", "Attention"),
    "expired": ("⌛ Expirada sin respuesta", "Warning"),
}


def _card(body: list[dict], actions: list[dict] | None = None) -> dict:
    card: dict = {"type": "AdaptiveCard", "$schema": SCHEMA, "version": VERSION, "body": body}
    if actions:
        card["actions"] = actions
    return card


def attachment(card: dict) -> dict:
    return {"contentType": CARD_CONTENT_TYPE, "content": card}


def message_card(subject: str, body: str) -> dict:
    return _card(
        [
            {"type": "TextBlock", "text": subject, "weight": "Bolder", "size": "Medium", "wrap": True},
            {"type": "TextBlock", "text": body, "wrap": True},
        ]
    )


def ticket_update_card(ticket_number: str, state: str, note: str) -> dict:
    return _card(
        [
            {
                "type": "TextBlock",
                "text": f"🔄 Actualización del ticket {ticket_number}",
                "weight": "Bolder",
                "size": "Medium",
                "wrap": True,
            },
            {"type": "FactSet", "facts": [{"title": "Estado", "value": state}]},
            {"type": "TextBlock", "text": note, "wrap": True},
        ]
    )


def approval_card(approval: ApprovalRequest, interactive: bool = True) -> dict:
    """Tarjeta de aprobación. Pendiente + interactive → botones Aprobar /
    Rechazar con un comentario opcional. Resuelta → muestra la decisión,
    quién la tomó y cuándo, sin botones (un segundo clic no hace nada)."""
    facts = [
        {"title": "Recurso", "value": approval.resource},
        {"title": "Solicitante", "value": approval.requester or "—"},
        {"title": "Ticket", "value": approval.ticket_number or "—"},
    ]
    body: list[dict] = [
        {
            "type": "TextBlock",
            "text": f"🔔 Aprobación requerida: {approval.resource}",
            "weight": "Bolder",
            "size": "Medium",
            "wrap": True,
        },
        {"type": "FactSet", "facts": facts},
    ]

    if approval.status in _STATUS_TEXT:
        label, color = _STATUS_TEXT[approval.status]
        by = f" por {approval.decided_by}" if approval.decided_by else ""
        body.append(
            {"type": "TextBlock", "text": f"{label}{by}", "weight": "Bolder", "color": color, "wrap": True}
        )
        if approval.comment:
            body.append({"type": "TextBlock", "text": f"Comentario: {approval.comment}", "wrap": True})
        return _card(body)

    if not interactive:
        body.append(
            {
                "type": "TextBlock",
                "text": "Responde a esta solicitud desde el portal del Help Desk.",
                "isSubtle": True,
                "wrap": True,
            }
        )
        return _card(body)

    body.append(
        {
            "type": "Input.Text",
            "id": "comment",
            "placeholder": "Comentario (opcional)",
            "isMultiline": True,
        }
    )
    data = {"approval_id": approval.id}
    actions = [
        {
            "type": "Action.Execute",
            "title": "Aprobar",
            "verb": VERB_APPROVE,
            "data": data,
            "style": "positive",
        },
        {
            "type": "Action.Execute",
            "title": "Rechazar",
            "verb": VERB_REJECT,
            "data": data,
            "style": "destructive",
        },
    ]
    return _card(body, actions)


def error_card(message: str) -> dict:
    return _card([{"type": "TextBlock", "text": f"⚠️ {message}", "wrap": True, "color": "Attention"}])

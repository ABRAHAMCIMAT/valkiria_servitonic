"""
Solicitudes de aprobación pendientes (Fase 2, I4/I7).

Cuando el Coordinador necesita la aprobación de un manager, registra aquí una
`ApprovalRequest`. La respuesta llega después y por otro camino (tarjeta de
Teams o `POST /api/approvals/{id}/decision`), posiblemente en otra instancia
de Cloud Run; con este registro se sabe qué conversación reanudar.

`decide()` es la única forma de resolver una aprobación y es atómica: solo la
primera decisión cuenta. Un segundo clic en "Aprobar" o una respuesta tras la
expiración no vuelven a ejecutar la acción.

Implementaciones:
  * InMemoryApprovalStore — desarrollo, pruebas y una sola instancia.
  * FirestoreApprovalStore (core/firestore_store.py) — Cloud Run multi-instancia.
"""

from __future__ import annotations

import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol, runtime_checkable

from .models import now_iso

PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
EXPIRED = "expired"
DECISIONS = (APPROVED, REJECTED)


def _default_ttl_hours() -> float:
    return float(os.getenv("APPROVAL_TTL_HOURS", "72"))


@dataclass
class ApprovalRequest:
    conversation_id: str
    action: str
    resource: str
    manager: str
    ticket_number: str = ""
    requester: str = ""
    manager_email: str = ""
    # ID de Entra ID del manager: el bot de Teams solo acepta la decisión de
    # este usuario (ver api/teams.py). Vacío = sin restricción (modo demo).
    manager_aad_id: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: str = PENDING
    created_at: str = field(default_factory=now_iso)
    expires_at: str = ""
    decided_at: str = ""
    decided_by: str = ""
    comment: str = ""
    delivery: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.expires_at:
            created = datetime.fromisoformat(self.created_at)
            self.expires_at = (created + timedelta(hours=_default_ttl_hours())).isoformat()

    def is_expired(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        return now >= datetime.fromisoformat(self.expires_at)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> ApprovalRequest:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def apply_decision(
    approval: ApprovalRequest, decision: str, decided_by: str, comment: str, now: datetime | None = None
) -> bool:
    """Aplica la decisión sobre `approval` si sigue pendiente. Devuelve True
    solo si esta llamada cambió el estado. Lógica compartida por todos los
    backends; cada uno la ejecuta dentro de su propia sección atómica."""
    if decision not in DECISIONS:
        raise ValueError(f"Decisión inválida: {decision!r}")
    if approval.status != PENDING:
        return False
    now = now or datetime.now(UTC)
    approval.decided_at = now.isoformat()
    if approval.is_expired(now):
        approval.status = EXPIRED
        return False
    approval.status = decision
    approval.decided_by = decided_by
    approval.comment = comment
    return True


@runtime_checkable
class ApprovalStorage(Protocol):
    def create(self, approval: ApprovalRequest) -> ApprovalRequest: ...
    def get(self, approval_id: str) -> ApprovalRequest | None: ...
    def update(self, approval: ApprovalRequest) -> None: ...
    def decide(
        self, approval_id: str, decision: str, decided_by: str, comment: str = ""
    ) -> tuple[ApprovalRequest | None, bool]: ...
    def list_pending(self) -> list[ApprovalRequest]: ...


class InMemoryApprovalStore:
    def __init__(self) -> None:
        self._items: dict[str, ApprovalRequest] = {}
        self._lock = threading.Lock()

    def create(self, approval: ApprovalRequest) -> ApprovalRequest:
        with self._lock:
            self._items[approval.id] = approval
        return approval

    def get(self, approval_id: str) -> ApprovalRequest | None:
        return self._items.get(approval_id)

    def update(self, approval: ApprovalRequest) -> None:
        with self._lock:
            self._items[approval.id] = approval

    def decide(
        self, approval_id: str, decision: str, decided_by: str, comment: str = ""
    ) -> tuple[ApprovalRequest | None, bool]:
        with self._lock:
            approval = self._items.get(approval_id)
            if approval is None:
                return None, False
            return approval, apply_decision(approval, decision, decided_by, comment)

    def list_pending(self) -> list[ApprovalRequest]:
        return [a for a in self._items.values() if a.status == PENDING]

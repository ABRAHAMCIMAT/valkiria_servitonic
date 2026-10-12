"""
Almacenamiento en Firestore (Fase 2, I4) — estado durable para Cloud Run.

Con varias instancias de Cloud Run, el estado en memoria de ConversationStore
se pierde cuando el usuario cae en otra instancia o la instancia se recicla.
Estas clases implementan los mismos contratos (`ConversationStorage`,
`ApprovalStorage`) sobre Firestore, así que server.py no cambia: se activan
con STORAGE_BACKEND=firestore (adapters/factory.py).

  FIRESTORE_DATABASE      base de datos (por defecto "(default)")
  FIRESTORE_TTL_DAYS      días hasta que la política TTL borra una
                          conversación (campo `expire_at`, ver Terraform)
  GCP_PROJECT             proyecto; en Cloud Run se detecta solo

La autenticación es la de la cuenta de servicio de Cloud Run (ADC); en local,
`gcloud auth application-default login`.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from .approvals import ApprovalRequest, apply_decision
from .models import Conversation, now_iso


def _default_client() -> Any:
    from google.cloud import firestore  # import diferido: dependencia solo en GCP

    return firestore.Client(
        project=os.getenv("GCP_PROJECT") or None,
        database=os.getenv("FIRESTORE_DATABASE", "(default)"),
    )


def _default_transactional(client: Any) -> Callable[[Callable[[Any], Any]], Any]:
    """Ejecuta `fn(transaction)` dentro de una transacción de Firestore
    (con los reintentos por contención que hace el SDK)."""
    from google.cloud import firestore

    def run(fn: Callable[[Any], Any]) -> Any:
        return firestore.transactional(fn)(client.transaction())

    return run


def _expire_at() -> datetime:
    return datetime.now(UTC) + timedelta(days=float(os.getenv("FIRESTORE_TTL_DAYS", "90")))


class FirestoreConversationStore:
    def __init__(self, client: Any | None = None, collection: str = "conversations"):
        self._client = client or _default_client()
        self._col = self._client.collection(collection)

    def create(self, user_message: str) -> Conversation:
        conv = Conversation(user_message=user_message)
        self.update(conv)
        return conv

    def get(self, conv_id: str) -> Conversation | None:
        snap = self._col.document(conv_id).get()
        if not snap.exists:
            return None
        return Conversation.from_dict(snap.to_dict())

    def update(self, conv: Conversation) -> None:
        doc = conv.to_dict()
        doc["updated_at"] = now_iso()
        doc["expire_at"] = _expire_at()
        self._col.document(conv.id).set(doc)

    def list(self, limit: int = 200) -> list[Conversation]:
        convs = [Conversation.from_dict(s.to_dict()) for s in self._col.limit(limit).stream()]
        return sorted(convs, key=lambda c: c.created_at)


class FirestoreApprovalStore:
    def __init__(
        self,
        client: Any | None = None,
        collection: str = "approvals",
        transactional: Callable[[Callable[[Any], Any]], Any] | None = None,
    ):
        self._client = client or _default_client()
        self._col = self._client.collection(collection)
        self._transactional = transactional or _default_transactional(self._client)

    def create(self, approval: ApprovalRequest) -> ApprovalRequest:
        self.update(approval)
        return approval

    def get(self, approval_id: str) -> ApprovalRequest | None:
        snap = self._col.document(approval_id).get()
        return ApprovalRequest.from_dict(snap.to_dict()) if snap.exists else None

    def update(self, approval: ApprovalRequest) -> None:
        self._col.document(approval.id).set(approval.to_dict())

    def decide(
        self, approval_id: str, decision: str, decided_by: str, comment: str = ""
    ) -> tuple[ApprovalRequest | None, bool]:
        """Leer-decidir-escribir en una transacción: dos clics simultáneos en
        instancias distintas no pueden aprobar dos veces."""
        ref = self._col.document(approval_id)

        def _txn(transaction: Any) -> tuple[ApprovalRequest | None, bool]:
            snap = ref.get(transaction=transaction)
            if not snap.exists:
                return None, False
            approval = ApprovalRequest.from_dict(snap.to_dict())
            before = approval.status
            changed = apply_decision(approval, decision, decided_by, comment)
            if approval.status != before:
                transaction.set(ref, approval.to_dict())
            return approval, changed

        result: tuple[ApprovalRequest | None, bool] = self._transactional(_txn)
        return result

    def list_pending(self) -> list[ApprovalRequest]:
        query = self._col.where("status", "==", "pending")
        return [ApprovalRequest.from_dict(s.to_dict()) for s in query.stream()]

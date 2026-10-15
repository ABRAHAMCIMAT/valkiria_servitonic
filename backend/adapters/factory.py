"""
Selección de implementaciones por variable de entorno (Fase 2, I1/I4).

Es el único lugar que conoce las clases concretas; server.py y los agentes
trabajan con las interfaces (adapters/ports.py, core/storage.py,
core/approvals.py). Cambiar de proveedor = cambiar una variable y desplegar
una revisión nueva, sin tocar código:

  TICKETING_PROVIDER = servicenow (compatibilidad) | servicetonic (PoC)
  NOTIFY_CHANNEL     = teams (único canal del PoC)
  STORAGE_BACKEND    = file (por defecto) | firestore
"""

from __future__ import annotations

import os

from .. import config
from ..core.approvals import ApprovalStorage, InMemoryApprovalStore
from ..core.state import ConversationStore
from ..core.storage import ConversationStorage
from .ports import NotifierPort, TicketingPort
from .servicenow import ServiceNowAdapter


def build_ticketing() -> TicketingPort:
    provider = os.getenv("TICKETING_PROVIDER", "servicenow").lower()
    if provider == "servicenow":
        return ServiceNowAdapter()
    if provider == "servicetonic":
        from .servicetonic import ServiceTonicAdapter

        return ServiceTonicAdapter()
    raise RuntimeError(f"TICKETING_PROVIDER desconocido: {provider!r}")


def build_notifier() -> NotifierPort:
    channel = os.getenv("NOTIFY_CHANNEL", "teams").lower()
    if channel == "teams":
        from .teams import TeamsNotifier

        return TeamsNotifier()
    raise RuntimeError(f"NOTIFY_CHANNEL={channel!r} no está soportado por el PoC; use 'teams'.")


def _storage_backend() -> str:
    backend = os.getenv("STORAGE_BACKEND", "file").lower()
    if backend not in ("file", "firestore"):
        raise RuntimeError(f"STORAGE_BACKEND desconocido: {backend!r}")
    return backend


def build_conversation_store() -> ConversationStorage:
    if _storage_backend() == "firestore":
        from ..core.firestore_store import FirestoreConversationStore

        return FirestoreConversationStore()
    return ConversationStore(persist_path=config.CONV_STORE)


def build_approval_store() -> ApprovalStorage:
    if _storage_backend() == "firestore":
        from ..core.firestore_store import FirestoreApprovalStore

        return FirestoreApprovalStore()
    return InMemoryApprovalStore()

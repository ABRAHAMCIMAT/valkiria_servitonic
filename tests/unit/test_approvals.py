"""Registro de aprobaciones y serialización de conversaciones (Fase 2, I4/I7)."""

from datetime import UTC, datetime, timedelta

import pytest


def _approval(**kw):
    from backend.core.approvals import ApprovalRequest

    base = {"conversation_id": "c1", "action": "request_hardware", "resource": "laptop", "manager": "María"}
    return ApprovalRequest(**{**base, **kw})


def test_expiry_defaults_to_ttl(monkeypatch):
    monkeypatch.setenv("APPROVAL_TTL_HOURS", "2")
    a = _approval()
    delta = datetime.fromisoformat(a.expires_at) - datetime.fromisoformat(a.created_at)
    assert delta == timedelta(hours=2)


def test_first_decision_wins():
    from backend.core.approvals import APPROVED, InMemoryApprovalStore

    store = InMemoryApprovalStore()
    a = store.create(_approval())
    approval, changed = store.decide(a.id, "approved", "María", "ok")
    assert changed and approval.status == APPROVED and approval.decided_by == "María"
    again, changed_again = store.decide(a.id, "rejected", "Otro")
    assert not changed_again and again.status == APPROVED and again.decided_by == "María"
    assert store.list_pending() == []


def test_decision_after_expiry_marks_expired():
    from backend.core.approvals import EXPIRED, InMemoryApprovalStore

    store = InMemoryApprovalStore()
    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    a = store.create(_approval(expires_at=past))
    approval, changed = store.decide(a.id, "approved", "María")
    assert not changed and approval.status == EXPIRED and approval.decided_by == ""


def test_unknown_approval_and_invalid_decision():
    from backend.core.approvals import InMemoryApprovalStore

    store = InMemoryApprovalStore()
    assert store.decide("nope", "approved", "x") == (None, False)
    a = store.create(_approval())
    with pytest.raises(ValueError):
        store.decide(a.id, "maybe", "x")


def test_approval_roundtrip():
    from backend.core.approvals import ApprovalRequest

    a = _approval(manager_email="maria@corp.com", delivery={"channel": "teams"})
    assert ApprovalRequest.from_dict(a.to_dict()) == a


def test_conversation_roundtrip(coordinator):
    from backend.core.models import Conversation

    conv = coordinator.handle("Quiero una laptop nueva", caller="Carlos Carballo")
    restored = Conversation.from_dict(conv.to_dict())
    assert restored.to_dict() == conv.to_dict()
    assert restored.ticket.priority == conv.ticket.priority
    assert restored.classification.intent == conv.classification.intent

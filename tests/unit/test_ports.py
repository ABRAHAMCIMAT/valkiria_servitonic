"""Puertos de sistemas externos y fábrica (Fase 2, I1)."""

import pytest


def test_servicenow_adapter_conforms_to_ticketing_port():
    from backend.adapters.ports import TicketingPort
    from backend.adapters.servicenow import ServiceNowAdapter

    assert isinstance(ServiceNowAdapter(), TicketingPort)


@pytest.mark.parametrize("cls_path", ["notifications.NotificationAdapter", "teams.TeamsNotifier"])
def test_notifiers_conform_to_notifier_port(cls_path):
    import importlib

    from backend.adapters.ports import NotifierPort

    module, cls = cls_path.split(".")
    notifier = getattr(importlib.import_module(f"backend.adapters.{module}"), cls)()
    assert isinstance(notifier, NotifierPort)


def test_list_tickets_filters_by_caller_newest_first():
    from backend.adapters.servicenow import ServiceNowAdapter
    from backend.core.models import Ticket

    a = ServiceNowAdapter()
    t1 = a.create_incident(Ticket(short_description="uno", caller="ana"))
    a.create_incident(Ticket(short_description="otro", caller="luis"))
    t3 = a.create_incident(Ticket(short_description="dos", caller="ana"))
    assert [t.number for t in a.list_tickets("ana")] == [t3.number, t1.number]
    assert a.list_tickets("nadie") == []
    assert len(a.list_tickets("ana", limit=1)) == 1


def test_status_query_only_sees_own_tickets(coordinator):
    coordinator.handle("No puedo entrar al CRM", caller="ana")
    conv = coordinator.handle("¿cuál es el estado de mi ticket?", caller="luis")
    tracking = [m for m in conv.messages if m.agent == "seguimiento"]
    assert "No encontré tickets" in tracking[0].content


def test_ticket_carries_impact_and_urgency_from_classification(coordinator):
    conv = coordinator.handle("No puedo entrar al CRM")
    assert conv.ticket is not None
    assert (conv.ticket.impact, conv.ticket.urgency) == (2, 2)


# -- fábrica -------------------------------------------------------------------
def test_factory_defaults(monkeypatch):
    from backend.adapters import factory
    from backend.adapters.servicenow import ServiceNowAdapter
    from backend.adapters.teams import TeamsNotifier
    from backend.core.approvals import InMemoryApprovalStore
    from backend.core.state import ConversationStore

    monkeypatch.delenv("TICKETING_PROVIDER", raising=False)
    monkeypatch.delenv("NOTIFY_CHANNEL", raising=False)
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    assert isinstance(factory.build_ticketing(), ServiceNowAdapter)
    assert isinstance(factory.build_notifier(), TeamsNotifier)
    assert isinstance(factory.build_conversation_store(), ConversationStore)
    assert isinstance(factory.build_approval_store(), InMemoryApprovalStore)


def test_factory_slack_channel_uses_legacy_adapter(monkeypatch):
    from backend.adapters import factory
    from backend.adapters.notifications import NotificationAdapter

    monkeypatch.setenv("NOTIFY_CHANNEL", "slack")
    assert isinstance(factory.build_notifier(), NotificationAdapter)


@pytest.mark.parametrize(
    ("var", "value", "builder"),
    [
        ("TICKETING_PROVIDER", "servicetonic", "build_ticketing"),
        ("TICKETING_PROVIDER", "otro", "build_ticketing"),
        ("STORAGE_BACKEND", "redis", "build_conversation_store"),
    ],
)
def test_factory_rejects_unavailable_options(monkeypatch, var, value, builder):
    from backend.adapters import factory

    monkeypatch.setenv(var, value)
    with pytest.raises(RuntimeError):
        getattr(factory, builder)()

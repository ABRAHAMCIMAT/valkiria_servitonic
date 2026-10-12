"""Notificaciones de Teams: tarjetas, modos de entrega y cliente del bot (Fase 2, I7). Sin red."""

import json
from urllib.parse import parse_qs

import httpx
import pytest


@pytest.fixture(autouse=True)
def _no_teams_env(monkeypatch):
    for var in (
        "TEAMS_WORKFLOW_URL",
        "TEAMS_WEBHOOK_URL",
        "TEAMS_BOT_APP_ID",
        "TEAMS_BOT_APP_PASSWORD",
        "TEAMS_TENANT_ID",
        "TEAMS_SERVICE_URL",
    ):
        monkeypatch.delenv(var, raising=False)


def _approval(**kw):
    from backend.core.approvals import ApprovalRequest

    base = {
        "conversation_id": "c1",
        "action": "request_hardware",
        "resource": "nuevo hardware",
        "manager": "María González",
        "manager_email": "maria@corp.com",
        "ticket_number": "INC0000001",
        "requester": "Carlos Carballo",
    }
    return ApprovalRequest(**{**base, **kw})


# -- tarjetas --------------------------------------------------------------------
def test_pending_approval_card_has_execute_actions():
    from backend.adapters import teams_cards

    a = _approval()
    card = teams_cards.approval_card(a)
    verbs = [act["verb"] for act in card["actions"]]
    assert verbs == ["approve", "reject"]
    assert all(
        act["type"] == "Action.Execute" and act["data"] == {"approval_id": a.id} for act in card["actions"]
    )
    assert card["version"] == "1.5"


def test_decided_card_has_no_actions_and_shows_approver():
    from backend.adapters import teams_cards

    card = teams_cards.approval_card(_approval(status="approved", decided_by="María González", comment="ok"))
    assert "actions" not in card
    text = json.dumps(card, ensure_ascii=False)
    assert "Aprobada por María González" in text and "Comentario: ok" in text


def test_non_interactive_card_has_no_buttons():
    from backend.adapters import teams_cards

    assert "actions" not in teams_cards.approval_card(_approval(), interactive=False)


# -- TeamsNotifier ---------------------------------------------------------------
def test_demo_mode_sends_nothing():
    from backend.adapters.teams import TeamsNotifier

    n = TeamsNotifier(client=httpx.Client(transport=httpx.MockTransport(lambda r: pytest.fail("sin red"))))
    assert n.mode == "demo" and not n.live
    r = n.send_approval_request("María", "laptop", "INC1", approval=_approval())
    assert r["success"] and r["delivered"] == "demo" and r["channel"] == "teams"


def test_production_requires_teams_configuration(monkeypatch):
    import backend.config
    from backend.adapters.teams import TeamsNotifier

    monkeypatch.setattr(backend.config, "IS_PRODUCTION", True)
    with pytest.raises(RuntimeError, match="teams"):
        TeamsNotifier()


def test_workflow_mode_posts_adaptive_card(monkeypatch):
    from backend.adapters.teams import TeamsNotifier

    monkeypatch.setenv("TEAMS_WORKFLOW_URL", "https://workflow.test/hook")
    posted = []

    def handler(request):
        posted.append(json.loads(request.content))
        return httpx.Response(202)

    n = TeamsNotifier(client=httpx.Client(transport=httpx.MockTransport(handler)))
    r = n.send_ticket_update("carlos", "INC1", "Resuelto", "listo")
    assert r["success"] and r["delivered"] == "workflow"
    att = posted[0]["attachments"][0]
    assert posted[0]["type"] == "message"
    assert att["contentType"] == "application/vnd.microsoft.card.adaptive"

    r = n.send_approval_request("María", "laptop", "INC1", approval=_approval())
    assert r["interactive"] is False and "actions" not in posted[1]["attachments"][0]["content"]


def test_workflow_failure_is_reported_not_raised(monkeypatch):
    from backend.adapters.teams import TeamsNotifier

    monkeypatch.setenv("TEAMS_WORKFLOW_URL", "https://workflow.test/hook")
    n = TeamsNotifier(client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(400))))
    r = n.send("a", "s", "b")
    assert r["success"] is False and "error" in r


class _FakeBot:
    configured = True

    def __init__(self, fail=False):
        self.fail = fail
        self.sent = []

    def resolve_user_id(self, email):
        if self.fail:
            from backend.llmops.errors import ProviderError

            raise ProviderError("Graph 404")
        return "aad-maria"

    def send_card_to_user(self, aad_object_id, card):
        self.sent.append((aad_object_id, card))
        return {"conversation_id": "a:1", "activity_id": "act-1"}


def test_bot_mode_sends_interactive_card_and_records_manager_id():
    from backend.adapters.teams import TeamsNotifier

    bot = _FakeBot()
    n = TeamsNotifier(bot=bot)
    a = _approval()
    r = n.send_approval_request("María", "laptop", "INC1", approval=a)
    assert r["delivered"] == "bot" and r["interactive"] and r["activity_id"] == "act-1"
    assert a.manager_aad_id == "aad-maria"
    assert bot.sent[0][0] == "aad-maria" and bot.sent[0][1]["actions"]


def test_bot_failure_falls_back_to_workflow(monkeypatch):
    from backend.adapters.teams import TeamsNotifier

    monkeypatch.setenv("TEAMS_WORKFLOW_URL", "https://workflow.test/hook")
    n = TeamsNotifier(
        bot=_FakeBot(fail=True),
        client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(202))),
    )
    r = n.send_approval_request("María", "laptop", "INC1", approval=_approval())
    assert r["delivered"] == "workflow" and r["interactive"] is False


# -- TeamsBotClient ----------------------------------------------------------------
def test_bot_client_token_graph_and_proactive_message():
    from backend.adapters.teams_bot import BotConfig, TeamsBotClient

    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        url = str(request.url)
        if url.startswith("https://login.microsoftonline.com/tenant-1/"):
            scope = parse_qs(request.content.decode())["scope"][0]
            return httpx.Response(200, json={"access_token": f"tok:{scope}", "expires_in": 3600})
        if url.startswith("https://graph.microsoft.com/v1.0/users/"):
            assert request.headers["Authorization"] == "Bearer tok:https://graph.microsoft.com/.default"
            return httpx.Response(200, json={"id": "aad-123"})
        if url == "https://smba.test/teams/v3/conversations":
            body = json.loads(request.content)
            assert body["members"] == [{"id": "aad-123"}] and body["tenantId"] == "tenant-1"
            assert body["bot"]["id"] == "28:app-1"
            return httpx.Response(200, json={"id": "a:conv/1"})
        if url == "https://smba.test/teams/v3/conversations/a%3Aconv%2F1/activities":
            assert request.headers["Authorization"] == "Bearer tok:https://api.botframework.com/.default"
            return httpx.Response(200, json={"id": "act-9"})
        return httpx.Response(404)

    client = TeamsBotClient(
        BotConfig(
            app_id="app-1", app_password="s", tenant_id="tenant-1", service_url="https://smba.test/teams/"
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert client.resolve_user_id("maria@corp.com") == "aad-123"
    ids = client.send_card_to_user("aad-123", {"type": "AdaptiveCard"})
    assert ids == {"conversation_id": "a:conv/1", "activity_id": "act-9"}
    token_calls = [c for c in calls if "login.microsoftonline.com" in str(c.url)]
    assert len(token_calls) == 2  # uno por scope, luego cacheados

    client.send_card_to_user("aad-123", {"type": "AdaptiveCard"})
    assert len([c for c in calls if "login.microsoftonline.com" in str(c.url)]) == 2


def test_bot_config_from_env(monkeypatch):
    from backend.adapters.teams_bot import DEFAULT_SERVICE_URL, BotConfig

    assert not BotConfig.from_env().configured
    monkeypatch.setenv("TEAMS_BOT_APP_ID", "a")
    monkeypatch.setenv("TEAMS_BOT_APP_PASSWORD", "b")
    monkeypatch.setenv("TEAMS_TENANT_ID", "c")
    cfg = BotConfig.from_env()
    assert cfg.configured and cfg.service_url == DEFAULT_SERVICE_URL
    monkeypatch.setenv("TEAMS_SERVICE_URL", "https://smba.trafficmanager.net/amer")
    assert BotConfig.from_env().service_url.endswith("/amer/")

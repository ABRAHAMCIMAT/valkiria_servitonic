"""Aprobaciones de punta a punta (Fase 2, I7): coordinador, API y bot de Teams."""

import importlib
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

APP_ID = "app-1"
SERVICE_URL = "https://smba.trafficmanager.net/teams/"


# -- coordinador -------------------------------------------------------------------
def _pending(coordinator, caller="Carlos Carballo"):
    conv = coordinator.handle("Quiero una laptop nueva", caller=caller)
    approval_id = next(m.data["approval_id"] for m in conv.messages if "approval_id" in m.data)
    return conv, coordinator.approvals.get(approval_id)


def test_pending_approval_is_registered(coordinator):
    conv, approval = _pending(coordinator)
    assert conv.status == "awaiting_approval"
    assert approval.conversation_id == conv.id
    assert approval.manager == "María González" and approval.manager_email == "maria@corp.com"
    assert approval.requester == "Carlos Carballo" and approval.ticket_number == conv.ticket.number
    assert approval.delivery["success"] is True


def test_resume_approved_executes_and_resolves(coordinator):
    conv, approval = _pending(coordinator)
    approval, _ = coordinator.approvals.decide(approval.id, "approved", "María González")
    coordinator.resume_approval(conv, approval)
    assert conv.status == "resolved"
    assert conv.ticket.state == "Resolved" and "María González" in conv.ticket.resolution_notes
    assert "ejecucion" in [m.agent for m in conv.messages[-3:]]


def test_resume_rejected_closes_ticket_with_reason(coordinator):
    conv, approval = _pending(coordinator)
    approval, _ = coordinator.approvals.decide(approval.id, "rejected", "María González", "sin presupuesto")
    coordinator.resume_approval(conv, approval)
    assert conv.status == "rejected"
    assert conv.ticket.state == "Closed" and "sin presupuesto" in conv.ticket.resolution_notes


def test_resume_expired_escalates(coordinator):
    conv, approval = _pending(coordinator)
    approval.expires_at = "2000-01-01T00:00:00+00:00"
    approval, changed = coordinator.approvals.decide(approval.id, "approved", "María González")
    assert not changed and approval.status == "expired"
    coordinator.resume_approval(conv, approval)
    assert conv.status == "escalated"


def test_resume_without_decision_is_an_error(coordinator):
    conv, approval = _pending(coordinator)
    with pytest.raises(ValueError):
        coordinator.resume_approval(conv, approval)


# -- API REST ------------------------------------------------------------------------
def _chat_pending(client):
    body = client.post(
        "/api/chat", json={"message": "Quiero una laptop nueva", "caller": "Carlos Carballo"}
    ).json()
    approval_id = next(m["data"]["approval_id"] for m in body["messages"] if "approval_id" in m["data"])
    return body["id"], approval_id


def test_api_decision_resumes_conversation(client):
    conv_id, approval_id = _chat_pending(client)
    pending = client.get("/api/approvals").json()
    assert [a["id"] for a in pending] == [approval_id]

    r = client.post(
        f"/api/approvals/{approval_id}/decision",
        json={"decision": "approved", "decided_by": "María González", "comment": "ok"},
    )
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert client.get(f"/api/conversations/{conv_id}").json()["status"] == "resolved"
    assert client.get("/api/approvals").json() == []

    again = client.post(
        f"/api/approvals/{approval_id}/decision", json={"decision": "rejected", "decided_by": "Otro"}
    )
    assert again.status_code == 409
    assert client.get(f"/api/conversations/{conv_id}").json()["status"] == "resolved"


def test_api_decision_validation_and_rbac(client, user_key):
    _, approval_id = _chat_pending(client)
    assert (
        client.post(
            f"/api/approvals/{approval_id}/decision", json={"decision": "maybe", "decided_by": "x"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/approvals/nope/decision", json={"decision": "approved", "decided_by": "x"}
        ).status_code
        == 404
    )
    r = client.post(
        f"/api/approvals/{approval_id}/decision",
        json={"decision": "approved", "decided_by": "x"},
        headers={"X-API-Key": user_key},
    )
    assert r.status_code == 403


def test_teams_endpoint_disabled_without_bot(anon_client):
    assert anon_client.post("/api/teams/messages", json={}).status_code == 503


# -- bot de Teams (JWT de Bot Framework) ---------------------------------------------------
@pytest.fixture(scope="module")
def signing_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _FakeJwks:
    def __init__(self, public_key):
        self._key = public_key

    def get_signing_key_from_jwt(self, token):
        return type("K", (), {"key": self._key})()


def _token(signing_key, **overrides):
    now = int(time.time())
    claims = {
        "iss": "https://api.botframework.com",
        "aud": APP_ID,
        "exp": now + 600,
        "nbf": now - 10,
        "serviceurl": SERVICE_URL,
        **overrides,
    }
    return jwt.encode(claims, signing_key, algorithm="RS256", headers={"kid": "k1"})


@pytest.fixture
def bot_server(monkeypatch, signing_key):
    monkeypatch.setenv("TEAMS_BOT_APP_ID", APP_ID)
    monkeypatch.setenv("NOTIFY_CHANNEL", "teams")
    import backend.config

    importlib.reload(backend.config)
    import backend.server

    importlib.reload(backend.server)
    from backend.security.botframework import BotFrameworkAuth

    backend.server.bot_auth = BotFrameworkAuth(APP_ID, jwks_client=_FakeJwks(signing_key.public_key()))
    return backend.server


def _invoke(approval_id, verb="approve", aad="aad-maria", comment="listo"):
    return {
        "type": "invoke",
        "name": "adaptiveCard/action",
        "serviceUrl": SERVICE_URL,
        "from": {"aadObjectId": aad, "name": "María González"},
        "value": {
            "action": {
                "type": "Action.Execute",
                "verb": verb,
                "data": {"approval_id": approval_id, "comment": comment},
            }
        },
    }


def test_teams_invoke_approves_and_returns_updated_card(bot_server, signing_key, admin_key):
    from fastapi.testclient import TestClient

    client = TestClient(bot_server.app)
    client.headers.update({"X-API-Key": admin_key})
    conv_id, approval_id = _chat_pending(client)

    bot = TestClient(bot_server.app)
    r = bot.post(
        "/api/teams/messages",
        json=_invoke(approval_id),
        headers={"Authorization": f"Bearer {_token(signing_key)}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["statusCode"] == 200 and body["type"] == "application/vnd.microsoft.card.adaptive"
    assert "actions" not in body["value"]
    assert client.get(f"/api/conversations/{conv_id}").json()["status"] == "resolved"
    assert bot_server.approvals.get(approval_id).comment == "listo"


def test_teams_invoke_from_wrong_user_is_refused(bot_server, signing_key, admin_key):
    from fastapi.testclient import TestClient

    client = TestClient(bot_server.app)
    client.headers.update({"X-API-Key": admin_key})
    conv_id, approval_id = _chat_pending(client)
    approval = bot_server.approvals.get(approval_id)
    approval.manager_aad_id = "aad-maria"
    bot_server.approvals.update(approval)

    r = TestClient(bot_server.app).post(
        "/api/teams/messages",
        json=_invoke(approval_id, aad="aad-intruso"),
        headers={"Authorization": f"Bearer {_token(signing_key)}"},
    )
    assert r.status_code == 200 and "Solo María González" in str(r.json()["value"])
    assert bot_server.approvals.get(approval_id).status == "pending"
    assert client.get(f"/api/conversations/{conv_id}").json()["status"] == "awaiting_approval"


@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "otra-app"},
        {"iss": "https://evil.example.com"},
        {"exp": int(time.time()) - 3600},
        {"serviceurl": "https://evil.example.com/"},
    ],
)
def test_teams_endpoint_rejects_invalid_tokens(bot_server, signing_key, overrides):
    from fastapi.testclient import TestClient

    r = TestClient(bot_server.app).post(
        "/api/teams/messages",
        json=_invoke("x"),
        headers={"Authorization": f"Bearer {_token(signing_key, **overrides)}"},
    )
    assert r.status_code == 401


def test_teams_endpoint_rejects_missing_or_foreign_signature(bot_server):
    from fastapi.testclient import TestClient

    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    bot = TestClient(bot_server.app)
    assert bot.post("/api/teams/messages", json=_invoke("x")).status_code == 401
    r = bot.post(
        "/api/teams/messages", json=_invoke("x"), headers={"Authorization": f"Bearer {_token(other)}"}
    )
    assert r.status_code == 401


def test_teams_non_invoke_activities_are_acknowledged(bot_server, signing_key):
    from fastapi.testclient import TestClient

    r = TestClient(bot_server.app).post(
        "/api/teams/messages",
        json={"type": "conversationUpdate", "serviceUrl": SERVICE_URL},
        headers={"Authorization": f"Bearer {_token(signing_key)}"},
    )
    assert r.status_code == 200

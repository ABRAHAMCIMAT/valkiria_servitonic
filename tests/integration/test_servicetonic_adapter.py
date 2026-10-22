"""Contrato HTTP simulado del adaptador ServiceTonic del PoC."""

import json

import httpx
import pytest

from backend.core.models import Priority, Ticket

pytestmark = pytest.mark.integration


@pytest.fixture
def servicetonic_env(monkeypatch):
    monkeypatch.setenv("SERVICETONIC_BASE_URL", "https://example.test/ServiceTonic")
    monkeypatch.setenv("SERVICETONIC_PROJECT_ID", "7")
    monkeypatch.setenv("SERVICETONIC_USERNAME", "svc_valkiria")
    monkeypatch.setenv("SERVICETONIC_PASSWORD", "secret")
    monkeypatch.setenv("SERVICETONIC_TEAM", "Service Desk")
    monkeypatch.setenv("POC_MANAGER_NAME", "Manager PoC")
    monkeypatch.setenv("POC_MANAGER_EMAIL", "manager@example.com")
    monkeypatch.setenv(
        "SERVICETONIC_FIELD_MAP",
        json.dumps(
            {
                "number": "ticketNumber",
                "title": "title",
                "description": "description",
                "state": "status",
                "priority": "priority",
                "caller": "contact",
            }
        ),
    )


def make_adapter(handler):
    from backend.adapters.servicetonic import ServiceTonicAdapter

    client = httpx.Client(
        base_url="https://example.test/ServiceTonic/", transport=httpx.MockTransport(handler)
    )
    return ServiceTonicAdapter(client=client)


def test_authenticates_and_creates_ticket(servicetonic_env):
    requests = []

    def handler(request: httpx.Request):
        requests.append(request)
        if request.url.path.endswith("/auth"):
            return httpx.Response(200, json="token-123")
        payload = json.loads(request.url.params["rsTicket"])
        assert payload["idProject"] == 7
        assert payload["team"] == "Service Desk"
        assert payload["contact"]["identContact"] == "user@example.com"
        return httpx.Response(200, json=42)

    adapter = make_adapter(handler)
    ticket = adapter.create_incident(
        Ticket(
            short_description="Acceso bloqueado",
            description="No puedo entrar",
            priority=Priority.P2,
            caller="user@example.com",
        )
    )
    assert ticket.number == "42"
    assert ticket.metadata["servicetonic_id"] == "42"
    assert requests[-1].headers["Authorization"] == "token-123"


def test_lists_and_maps_tickets_without_exposing_dynamic_fields(servicetonic_env):
    def handler(request: httpx.Request):
        if request.url.path.endswith("/auth"):
            return httpx.Response(200, text="token-123")
        return httpx.Response(
            200,
            json=[
                {
                    "idTicket": 99,
                    "team": "Service Desk",
                    "contact": {"identContact": "user@example.com"},
                    "fieldList": [
                        {"fieldName": "title", "value": "VPN"},
                        {"fieldName": "status", "value": "Open"},
                        {"fieldName": "priority", "value": "P3"},
                    ],
                }
            ],
        )

    tickets = make_adapter(handler).list_tickets("user@example.com", limit=1)
    assert len(tickets) == 1
    assert tickets[0].number == "99"
    assert tickets[0].short_description == "VPN"
    assert tickets[0].priority == Priority.P3


def test_updates_ticket_using_internal_id(servicetonic_env):
    seen_payload = {}

    def handler(request: httpx.Request):
        if request.url.path.endswith("/auth"):
            return httpx.Response(200, json={"token": "token-123"})
        seen_payload.update(json.loads(request.url.params["rsTicket"]))
        return httpx.Response(200, json=99)

    ticket = Ticket(number="99", state="Open", metadata={"servicetonic_id": 99})
    result = make_adapter(handler).update_incident(ticket, {"state": "Resolved"})
    assert result.state == "Resolved"
    assert {f["fieldName"]: f["value"] for f in seen_payload["fieldList"]}["status"] == "Resolved"


def test_self_service_never_reports_false_success(servicetonic_env):
    adapter = make_adapter(lambda request: httpx.Response(500))
    assert adapter.unlock_account("user")["success"] is False
    assert adapter.reset_password("user")["success"] is False
    assert adapter.assign_license("office", "user")["success"] is False
    assert adapter.get_manager("user@example.com") == {
        "manager": "Manager PoC",
        "email": "manager@example.com",
    }


def test_rejects_missing_or_invalid_configuration(monkeypatch, servicetonic_env):
    from backend.adapters.servicetonic import ServiceTonicAdapter

    monkeypatch.delenv("SERVICETONIC_BASE_URL")
    with pytest.raises(RuntimeError, match="SERVICETONIC_BASE_URL"):
        ServiceTonicAdapter()

    monkeypatch.setenv("SERVICETONIC_BASE_URL", "https://example.test/ServiceTonic")
    monkeypatch.setenv("SERVICETONIC_FIELD_MAP", "not-json")
    with pytest.raises(RuntimeError, match="JSON válido"):
        ServiceTonicAdapter()

    monkeypatch.setenv("SERVICETONIC_FIELD_MAP", "[]")
    with pytest.raises(RuntimeError, match="debe mapear"):
        ServiceTonicAdapter()


def test_rejects_empty_or_unknown_auth_token():
    from backend.adapters.servicetonic import _token_from_response
    from backend.llmops.errors import ProviderError

    with pytest.raises(ProviderError, match="token vacío"):
        _token_from_response(httpx.Response(200, text=""))
    with pytest.raises(ProviderError, match="no reconocido"):
        _token_from_response(httpx.Response(200, json={"unexpected": True}))


def test_reauthenticates_once_after_unauthorized(servicetonic_env):
    auth_count = 0
    list_count = 0

    def handler(request: httpx.Request):
        nonlocal auth_count, list_count
        if request.url.path.endswith("/auth"):
            auth_count += 1
            return httpx.Response(200, json=f"token-{auth_count}")
        list_count += 1
        if list_count == 1:
            return httpx.Response(401)
        assert request.headers["Authorization"] == "token-2"
        return httpx.Response(204)

    assert make_adapter(handler).list_tickets("user@example.com") == []
    assert auth_count == 2
    assert list_count == 2


def test_authentication_failure_is_typed(servicetonic_env):
    from backend.llmops.errors import ProviderError

    adapter = make_adapter(lambda request: httpx.Response(401))
    with pytest.raises(ProviderError, match="credenciales"):
        adapter.list_tickets("user@example.com")


def test_get_ticket_by_internal_id(servicetonic_env):
    def handler(request: httpx.Request):
        if request.url.path.endswith("/auth"):
            return httpx.Response(200, text="token")
        assert request.url.params["getHistory"] == "true"
        return httpx.Response(
            200,
            json={
                "idTicket": 55,
                "team": "Service Desk",
                "fieldList": [{"fieldName": "title", "value": "Ticket conocido"}],
            },
        )

    ticket = make_adapter(handler).get_incident("55")
    assert ticket is not None
    assert ticket.number == "55"
    assert ticket.short_description == "Ticket conocido"


def test_create_accepts_object_response_and_invalid_ticket_id_is_rejected(servicetonic_env):
    from backend.llmops.errors import ProviderError

    def handler(request: httpx.Request):
        if request.url.path.endswith("/auth"):
            return httpx.Response(200, text="token")
        return httpx.Response(200, json={"idTicket": 77})

    adapter = make_adapter(handler)
    created = adapter.create_incident(Ticket(short_description="Prueba"))
    assert created.number == "77"

    invalid = Ticket(number="not-numeric")
    with pytest.raises(ProviderError, match="ID interno"):
        adapter.update_incident(invalid, {"state": "Resolved"})


# -- Comportamiento comprobado contra Valtre (docs/integraciones/SERVICETONIC_HALLAZGOS.md) --


def _routes(responses):
    """Handler que autentica y responde según (método, sufijo de ruta); registra las peticiones."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request):
        seen.append(request)
        if request.url.path.endswith("/auth"):
            return httpx.Response(200, text="token")
        for (method, suffix), response in responses.items():
            if request.method == method and request.url.path.endswith(suffix):
                return response
        return httpx.Response(404, text="ruta no simulada")

    return handler, seen


def test_writes_send_a_multipart_body_with_one_part(servicetonic_env):
    handler, seen = _routes({("POST", "/tickets"): httpx.Response(200, text="5")})
    make_adapter(handler).create_incident(Ticket(short_description="x", caller="user@example.com"))
    write = seen[-1]
    assert write.headers["Content-Type"].startswith("multipart/form-data; boundary=")
    assert b'name="files"' in write.content  # sin partes, Valtre responde 400 Missing start boundary
    assert "rsTicket" in write.url.params


def test_value_map_translates_state_and_priority_both_ways(servicetonic_env, monkeypatch):
    monkeypatch.setenv(
        "SERVICETONIC_VALUE_MAP",
        json.dumps({"priority": {"P2": "Alta"}, "state": {"New": "Nuevo", "In Progress": "Abierta"}}),
    )
    handler, seen = _routes(
        {
            ("POST", "/tickets"): httpx.Response(200, text="5"),
            ("POST", "/tickets/list"): httpx.Response(
                200,
                json=[
                    {
                        "idTicket": 5,
                        "fieldList": [
                            {"fieldName": "status", "value": "Abierta"},
                            {"fieldName": "priority", "value": "Alta"},
                        ],
                    }
                ],
            ),
        }
    )
    adapter = make_adapter(handler)
    adapter.create_incident(Ticket(short_description="x", priority=Priority.P2, state="New"))
    sent = {f["fieldName"]: f["value"] for f in json.loads(seen[-1].url.params["rsTicket"])["fieldList"]}
    assert sent["priority"] == "Alta" and sent["status"] == "Nuevo"

    [ticket] = adapter.list_tickets("user@example.com", limit=1)
    assert ticket.priority == Priority.P2 and ticket.state == "In Progress"


def test_invalid_value_map_is_rejected(servicetonic_env, monkeypatch):
    from backend.adapters.servicetonic import ServiceTonicAdapter

    monkeypatch.setenv("SERVICETONIC_VALUE_MAP", '{"priority": "Alta"}')
    with pytest.raises(RuntimeError, match="VALUE_MAP"):
        ServiceTonicAdapter()


def test_notes_become_actions(servicetonic_env):
    handler, seen = _routes(
        {
            ("PUT", "/tickets/9"): httpx.Response(200, text="9"),
            ("POST", "/tickets/9/actions"): httpx.Response(200, text="1"),
        }
    )
    ticket = Ticket(number="9", metadata={"servicetonic_id": 9})
    make_adapter(handler).update_incident(
        ticket, {"state": "Resolved", "work_notes": "Resumen L2", "resolution_notes": "Listo"}
    )
    actions = [json.loads(r.url.params["rsAction"]) for r in seen if r.url.path.endswith("/actions")]
    assert actions == [
        {"description": "Resumen L2", "isPublic": False, "isSolution": False},
        {"description": "Listo", "isPublic": True, "isSolution": True},
    ]
    assert ticket.work_notes == ["Resumen L2"]  # se acumula, no se sustituye la lista


def test_unknown_ticket_err012_returns_none(servicetonic_env):
    handler, _ = _routes({("GET", "/tickets/404"): httpx.Response(400, text="ERR012-Expected ticket")})
    assert make_adapter(handler).get_incident("404") is None


def test_other_client_errors_keep_the_server_message(servicetonic_env):
    from backend.llmops.errors import ProviderError

    handler, _ = _routes({("POST", "/tickets"): httpx.Response(400, text="Team does not exist")})
    with pytest.raises(ProviderError, match="Team does not exist"):
        make_adapter(handler).create_incident(Ticket(short_description="x"))


def test_long_texts_are_truncated_to_fit_the_url(servicetonic_env):
    from urllib.parse import quote

    from backend.adapters.servicetonic import MAX_TEXT_URL_CHARS, fit_for_url

    assert fit_for_url("No puedo entrar al CRM") == "No puedo entrar al CRM"
    handler, seen = _routes({("POST", "/tickets"): httpx.Response(200, text="5")})
    make_adapter(handler).create_incident(Ticket(short_description="x", description="ñ" * 50_000))
    sent = {f["fieldName"]: f["value"] for f in json.loads(seen[-1].url.params["rsTicket"])["fieldList"]}
    assert len(quote(sent["description"], safe="")) <= MAX_TEXT_URL_CHARS
    assert sent["description"].endswith("[…recortado]")

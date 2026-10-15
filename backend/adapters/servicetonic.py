"""Adaptador REST de ServiceTonic para el PoC local.

Implementa el contrato legado `TicketingPort` mientras I1 termina de neutralizar
los nombres. La API usa un token propio y campos dinámicos definidos por cada
servicio ServiceTonic.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import UTC, datetime
from typing import Any

import httpx

from ..core.models import Priority, Ticket
from ..llmops.errors import ProviderError, RetryableError, retry
from ..llmops.logging import get_logger

log = get_logger("adapter.servicetonic")


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} es obligatoria para TICKETING_PROVIDER='servicetonic'.")
    return value


def _encoded_password(password: str) -> str:
    # El protocolo ServiceTonic exige SHA-1 binario + Base64. No se usa como
    # almacenamiento de contraseña; TLS protege el transporte.  # NOSONAR
    digest = hashlib.sha1(password.encode("utf-8"), usedforsecurity=False).digest()  # noqa: S324
    return base64.b64encode(digest).decode("ascii")


def _token_from_response(response: httpx.Response) -> str:
    text = response.text.strip()
    if not text:
        raise ProviderError("ServiceTonic devolvió un token vacío.")
    try:
        payload = response.json()
    except ValueError:
        return text.strip('"')
    if isinstance(payload, str):
        return payload.strip()
    if isinstance(payload, dict):
        for key in ("token", "authorization", "authorizationToken", "authToken", "result", "value"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
    raise ProviderError("Formato de token ServiceTonic no reconocido.")


class ServiceTonicAdapter:
    live = True

    def __init__(self, client: httpx.Client | None = None):
        self.base_url = _required("SERVICETONIC_BASE_URL").rstrip("/") + "/"
        self.project_id = int(_required("SERVICETONIC_PROJECT_ID"))
        self.username = _required("SERVICETONIC_USERNAME")
        self.password = _required("SERVICETONIC_PASSWORD")
        self.team = os.getenv("SERVICETONIC_TEAM", "").strip()
        self.manager_name = os.getenv("POC_MANAGER_NAME", "").strip()
        self.manager_email = os.getenv("POC_MANAGER_EMAIL", "").strip()
        self.auth_prefix = os.getenv("SERVICETONIC_AUTH_PREFIX", "")
        self._client = client or httpx.Client(base_url=self.base_url, timeout=30.0)
        self._token = ""
        self._field_map = self._load_field_map()

    @staticmethod
    def _load_field_map() -> dict[str, str]:
        raw = os.getenv("SERVICETONIC_FIELD_MAP", "{}").strip() or "{}"
        try:
            mapping = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("SERVICETONIC_FIELD_MAP debe ser un objeto JSON válido.") from exc
        if not isinstance(mapping, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()
        ):
            raise RuntimeError("SERVICETONIC_FIELD_MAP debe mapear nombres de dominio a campos ServiceTonic.")
        return mapping

    def _authenticate(self) -> str:
        response = self._client.post(
            "strest/v1/auth",
            json={
                "idProject": self.project_id,
                "username": self.username,
                "password": _encoded_password(self.password),
            },
        )
        if response.status_code == 401:
            raise ProviderError("ServiceTonic rechazó las credenciales del agente técnico.")
        response.raise_for_status()
        self._token = _token_from_response(response)
        return self._token

    def _headers(self) -> dict[str, str]:
        token = self._token or self._authenticate()
        return {"Authorization": f"{self.auth_prefix}{token}", "Accept": "application/json"}

    def _request(self, method: str, path: str, *, retry_auth: bool = True, **kwargs) -> httpx.Response:
        def call() -> httpx.Response:
            try:
                response = self._client.request(method, path, headers=self._headers(), **kwargs)
            except httpx.TransportError as exc:
                raise RetryableError(f"Error de red hacia ServiceTonic: {exc}") from exc
            if response.status_code == 401 and retry_auth:
                self._token = ""
                return self._request(method, path, retry_auth=False, **kwargs)
            if response.status_code == 429 or response.status_code >= 500:
                raise RetryableError(f"ServiceTonic devolvió HTTP {response.status_code}")
            if response.status_code >= 400:
                raise ProviderError(f"ServiceTonic devolvió HTTP {response.status_code}")
            return response

        return retry(call, max_attempts=3, base_delay=0.5, max_delay=8.0, logger=log)

    def _field_list(self, ticket: Ticket, updates: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        values: dict[str, Any] = {
            "number": ticket.number,
            "title": ticket.short_description,
            "description": ticket.description,
            "state": ticket.state,
            "priority": ticket.priority.value if isinstance(ticket.priority, Priority) else ticket.priority,
            "category": ticket.category,
            "subcategory": ticket.subcategory,
            "assignment_group": ticket.assignment_group,
            "resolution_notes": ticket.resolution_notes,
        }
        values.update(updates or {})
        return [
            {"fieldName": remote, "value": value}
            for local, remote in self._field_map.items()
            if (value := values.get(local)) not in (None, "", [])
        ]

    def _ticket_payload(self, ticket: Ticket, updates: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.team:
            raise RuntimeError("SERVICETONIC_TEAM es obligatoria para crear o actualizar tickets.")
        payload: dict[str, Any] = {
            "idProject": self.project_id,
            "team": self.team,
            "username": self.username,
            "fieldList": self._field_list(ticket, updates),
        }
        if ticket.caller:
            payload["contact"] = {"identContact": ticket.caller}
        return payload

    @staticmethod
    def _incident_id(ticket: Ticket) -> int:
        value = ticket.metadata.get("servicetonic_id") or ticket.number
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ProviderError("El ticket no contiene un ID interno ServiceTonic válido.") from exc

    def create_incident(self, ticket: Ticket) -> Ticket:
        payload = self._ticket_payload(ticket)
        response = self._request(
            "POST",
            f"strest/v1/services/{self.project_id}/tickets",
            params={"rsTicket": json.dumps(payload, ensure_ascii=False)},
        )
        raw_id = response.text.strip().strip('"')
        try:
            data = response.json()
        except ValueError:
            data = raw_id
        if isinstance(data, dict):
            raw_id = str(data.get("idTicket") or data.get("id") or data.get("result") or raw_id)
        elif data not in (None, ""):
            raw_id = str(data)
        ticket.number = raw_id
        ticket.metadata["servicetonic_id"] = raw_id
        return ticket

    def update_incident(self, ticket: Ticket, fields: dict) -> Ticket:
        incident_id = self._incident_id(ticket)
        payload = self._ticket_payload(ticket, fields)
        self._request(
            "PUT",
            f"strest/v1/services/{self.project_id}/tickets/{incident_id}",
            params={"rsTicket": json.dumps(payload, ensure_ascii=False)},
        )
        for key, value in fields.items():
            if hasattr(ticket, key):
                setattr(ticket, key, value)
        ticket.updated_at = datetime.now(UTC).isoformat()
        return ticket

    def get_incident(self, number: str) -> Ticket | None:
        try:
            incident_id = int(number)
        except ValueError:
            matches = self._list(
                {
                    "fieldName": self._field_map.get("number", "idTicket"),
                    "filter": "EQUALS",
                    "value1": number,
                },
                1,
            )
            return matches[0] if matches else None
        response = self._request(
            "GET",
            f"strest/v1/services/{self.project_id}/tickets/{incident_id}",
            params={"getHistory": "true"},
        )
        return self._to_ticket(response.json())

    def _list(self, criterion: dict[str, Any] | None, limit: int) -> list[Ticket]:
        query = {
            "logic": "AND",
            "initResult": 0,
            "maxResults": limit,
            "fieldList": [],
            "criterionList": [criterion] if criterion else [],
            "orderList": [],
        }
        response = self._request("POST", f"strest/v1/services/{self.project_id}/tickets/list", json=query)
        if response.status_code == 204:
            return []
        payload = response.json()
        records = payload if isinstance(payload, list) else payload.get("tickets", payload.get("result", []))
        return [self._to_ticket(record) for record in records]

    def list_tickets(self, caller: str, limit: int = 5) -> list[Ticket]:
        field = self._field_map.get("caller", "contact")
        criterion = {"fieldName": field, "filter": "EQUALS", "value1": caller} if caller else None
        return self._list(criterion, limit)

    def _to_ticket(self, record: dict[str, Any]) -> Ticket:
        fields = {
            item.get("fieldName"): item.get("value", item.get("textValue"))
            for item in record.get("fieldList", [])
            if item.get("fieldName")
        }
        reverse = {remote: local for local, remote in self._field_map.items()}
        values = {reverse[key]: value for key, value in fields.items() if key in reverse}
        incident_id = record.get("idTicket") or values.get("number") or ""
        priority = values.get("priority", Priority.P4)
        if priority not in Priority._value2member_map_:
            priority = Priority.P4
        contact = record.get("contact") or {}
        return Ticket(
            number=str(incident_id),
            short_description=str(values.get("title", "")),
            description=str(values.get("description", "")),
            state=str(values.get("state", "New")),
            priority=Priority(priority),
            category=str(values.get("category", "")),
            subcategory=str(values.get("subcategory", "")),
            assignment_group=str(record.get("team") or values.get("assignment_group", "")),
            caller=str(contact.get("identContact", "")),
            metadata={"servicetonic_id": incident_id, "provider": "servicetonic"},
        )

    def search_kb(self, query: str, top_k: int = 3) -> list[dict]:
        return []

    def get_manager(self, employee: str) -> dict | None:
        if not self.manager_email:
            return None
        return {"manager": self.manager_name or self.manager_email, "email": self.manager_email}

    @staticmethod
    def _not_implemented(action: str) -> dict:
        return {
            "success": False,
            "action": action,
            "message": "El PoC registra la solicitud como ticket; no ejecuta acciones de autoservicio.",
        }

    def unlock_account(self, target: str) -> dict:
        return self._not_implemented("unlock_account")

    def reset_password(self, target: str) -> dict:
        return self._not_implemented("reset_password")

    def assign_license(self, software: str, user: str) -> dict:
        return self._not_implemented("assign_license")

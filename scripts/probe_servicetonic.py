#!/usr/bin/env python3
"""Prueba contractual de solo lectura para ServiceTonic.

No imprime credenciales, tokens ni registros. Solo reporta códigos HTTP y la
forma general de las respuestas para demostrar conectividad y contrato.
"""

from __future__ import annotations

import base64
import hashlib
import os
import sys
from typing import Any

import httpx


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Falta la variable requerida {name}")
    return value


def encoded_password(password: str) -> str:
    digest = hashlib.sha1(password.encode("utf-8"), usedforsecurity=False).digest()  # noqa: S324
    return base64.b64encode(digest).decode("ascii")


def extract_token(response: httpx.Response) -> str:
    text = response.text.strip()
    if not text:
        raise RuntimeError("ServiceTonic devolvió un token vacío")
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
    raise RuntimeError("No se reconoció el formato del token de autenticación")


def response_shape(response: httpx.Response) -> str:
    if response.status_code == 204:
        return "sin contenido"
    try:
        payload: Any = response.json()
    except ValueError:
        return f"respuesta no JSON ({response.headers.get('content-type', 'sin content-type')})"
    if isinstance(payload, list):
        return f"lista con {len(payload)} elemento(s)"
    if isinstance(payload, dict):
        return f"objeto JSON con {len(payload)} campo(s)"
    return f"JSON tipo {type(payload).__name__}"


def main() -> int:
    base_url = required("SERVICETONIC_BASE_URL").rstrip("/") + "/"
    project_id = int(required("SERVICETONIC_PROJECT_ID"))
    username = required("SERVICETONIC_USERNAME")
    password = required("SERVICETONIC_PASSWORD")
    prefix = os.getenv("SERVICETONIC_AUTH_PREFIX", "")
    ticket_id = os.getenv("SERVICETONIC_TEST_TICKET_ID", "").strip()

    with httpx.Client(base_url=base_url, timeout=30.0, follow_redirects=False) as client:
        auth = client.post(
            "strest/v1/auth",
            json={
                "idProject": project_id,
                "username": username,
                "password": encoded_password(password),
            },
        )
        print(f"auth_status={auth.status_code}")
        auth.raise_for_status()
        token = extract_token(auth)
        headers = {"Authorization": f"{prefix}{token}"}

        query = {
            "logic": "AND",
            "initResult": 0,
            "maxResults": 1,
            "fieldList": [],
            "criterionList": [],
            "orderList": [],
        }
        for resource in ("contacts", "tickets"):
            response = client.post(
                f"strest/v1/services/{project_id}/{resource}/list",
                headers=headers,
                json=query,
            )
            print(f"{resource}_status={response.status_code}")
            if response.status_code not in (200, 204):
                response.raise_for_status()
            print(f"{resource}_shape={response_shape(response)}")

        if ticket_id:
            response = client.get(
                f"strest/v1/services/{project_id}/tickets/{int(ticket_id)}",
                headers=headers,
                params={"getHistory": "false"},
            )
            print(f"ticket_status={response.status_code}")
            response.raise_for_status()
            print(f"ticket_shape={response_shape(response)}")

    print("result=read-only contract probe passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, httpx.HTTPError) as exc:
        print(f"result=failed ({type(exc).__name__})", file=sys.stderr)
        raise SystemExit(1) from exc

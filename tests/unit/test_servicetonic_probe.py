"""Pruebas del probe contractual de solo lectura de ServiceTonic."""

import base64
import hashlib

import httpx
import pytest

from scripts.probe_servicetonic import encoded_password, extract_token, response_shape


def test_encoded_password_matches_protocol_sha1_base64():
    expected = base64.b64encode(hashlib.sha1(b"secret", usedforsecurity=False).digest()).decode()
    assert encoded_password("secret") == expected


@pytest.mark.parametrize(
    "content,content_type,expected",
    [
        (b'"plain-token"', "application/json", "plain-token"),
        (b'{"token":"object-token"}', "application/json", "object-token"),
        (b"raw-token", "text/plain", "raw-token"),
    ],
)
def test_extract_token_supports_documented_and_common_shapes(content, content_type, expected):
    response = httpx.Response(200, content=content, headers={"content-type": content_type})
    assert extract_token(response) == expected


def test_extract_token_rejects_empty_response():
    with pytest.raises(RuntimeError, match="token vacío"):
        extract_token(httpx.Response(200, text=""))


def test_response_shape_does_not_expose_record_values():
    response = httpx.Response(200, json=[{"email": "persona@example.com"}])
    shape = response_shape(response)
    assert shape == "lista con 1 elemento(s)"
    assert "persona@example.com" not in shape


def test_response_shape_handles_no_content():
    assert response_shape(httpx.Response(204)) == "sin contenido"

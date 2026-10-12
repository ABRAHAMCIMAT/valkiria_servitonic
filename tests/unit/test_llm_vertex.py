"""Proveedor Vertex AI (Gemini) y tokens de Google Cloud (Fase 2, I2). Sin red."""

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest


def test_vertex_base_url_regional_and_global():
    from backend.core.llm import vertex_base_url

    assert vertex_base_url("p1", "us-central1") == (
        "https://us-central1-aiplatform.googleapis.com/v1/projects/p1/locations/us-central1/endpoints/openapi"
    )
    assert vertex_base_url("p1", "global").startswith("https://aiplatform.googleapis.com/")


def test_from_env_vertex(monkeypatch):
    from backend.core.llm import VERTEX_DEFAULT_MODEL, LLMConfig

    monkeypatch.setenv("LLM_PROVIDER", "vertex")
    monkeypatch.setenv("GCP_PROJECT", "snow-ma-dev")
    monkeypatch.setenv("VERTEX_LOCATION", "us-east4")
    # Valores de Jan que docker-compose define siempre: no deben filtrarse
    monkeypatch.setenv("LLM_BASE_URL", "http://host.docker.internal:1337/v1")
    monkeypatch.setenv("LLM_MODEL", "gpt-oss:latest")
    monkeypatch.setenv("LLM_API_KEY", "no-se-usa")
    cfg = LLMConfig.from_env()
    assert cfg.provider == "vertex"
    assert "projects/snow-ma-dev/locations/us-east4" in cfg.base_url
    assert cfg.model == VERTEX_DEFAULT_MODEL
    assert cfg.api_key == ""


def test_from_env_vertex_model_override(monkeypatch):
    from backend.core.llm import LLMConfig

    monkeypatch.setenv("LLM_PROVIDER", "vertex")
    monkeypatch.setenv("GCP_PROJECT", "p")
    monkeypatch.setenv("VERTEX_MODEL", "google/gemini-2.5-pro")
    assert LLMConfig.from_env().model == "google/gemini-2.5-pro"


def test_from_env_vertex_requires_project(monkeypatch):
    import backend.core.gcp_auth as gcp_auth
    from backend.core.llm import LLMConfig

    monkeypatch.setenv("LLM_PROVIDER", "vertex")
    monkeypatch.delenv("GCP_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.setattr(gcp_auth, "default_project", lambda: "")
    with pytest.raises(RuntimeError, match="GCP_PROJECT"):
        LLMConfig.from_env()


def _llm_with_transport(handler, token_provider=None):
    from backend.core.llm import LLMConfig, OpenAICompatLLM

    llm = OpenAICompatLLM(
        LLMConfig(provider="vertex", base_url="https://vertex.test/openapi", model="google/gemini-2.5-flash"),
        token_provider=token_provider,
    )
    llm._client = httpx.Client(transport=httpx.MockTransport(handler))
    return llm


def test_requests_use_fresh_token_each_call():
    seen = []
    tokens = iter(["tok-1", "tok-2"])

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers["Authorization"])
        assert json.loads(request.content)["model"] == "google/gemini-2.5-flash"
        return httpx.Response(200, json={"choices": [{"message": {"content": "hola"}}]})

    llm = _llm_with_transport(handler, token_provider=lambda: next(tokens))
    assert llm.complete([{"role": "user", "content": "hi"}]) == "hola"
    llm.complete([{"role": "user", "content": "hi"}])
    assert seen == ["Bearer tok-1", "Bearer tok-2"]


def test_blocked_response_is_provider_error():
    from backend.llmops.errors import ProviderError

    def handler(request):
        return httpx.Response(
            200, json={"choices": [{"message": {"content": None}, "finish_reason": "content_filter"}]}
        )

    llm = _llm_with_transport(handler, token_provider=lambda: "t")
    with pytest.raises(ProviderError, match="content_filter"):
        llm.complete([{"role": "user", "content": "x"}])


def test_unauthorized_is_provider_error():
    from backend.llmops.errors import ProviderError

    llm = _llm_with_transport(lambda r: httpx.Response(401, json={}), token_provider=lambda: "t")
    with pytest.raises(ProviderError):
        llm.complete([{"role": "user", "content": "x"}])


def test_llm_facade_selects_vertex_strategy(monkeypatch):
    import backend.core.gcp_auth as gcp_auth
    from backend.core.llm import LLM, LLMConfig, OpenAICompatLLM

    monkeypatch.setattr(gcp_auth, "_adc_credentials", lambda: pytest.fail("no debe pedir credenciales aún"))
    llm = LLM(LLMConfig(provider="vertex", base_url="https://x", model="m"))
    assert isinstance(llm._impl, OpenAICompatLLM)
    assert llm._impl._token_provider is not None


# -- GoogleTokenProvider -------------------------------------------------------
class _FakeCreds:
    def __init__(self, lifetimes):
        self._lifetimes = iter(lifetimes)
        self.token = None
        self.expiry = None
        self.refreshes = 0

    def refresh(self, request):
        self.refreshes += 1
        self.token = f"tok-{self.refreshes}"
        # google-auth usa datetimes UTC sin zona horaria
        self.expiry = (datetime.now(UTC) + next(self._lifetimes)).replace(tzinfo=None)


def test_token_is_cached_until_close_to_expiry():
    from backend.core.gcp_auth import GoogleTokenProvider

    creds = _FakeCreds([timedelta(hours=1), timedelta(minutes=2), timedelta(hours=1)])
    provider = GoogleTokenProvider(credentials_factory=lambda: creds)
    assert provider.token() == "tok-1"
    assert provider.token() == "tok-1"  # cacheado: faltan ~60 min
    assert creds.refreshes == 1

    creds.expiry = (datetime.now(UTC) + timedelta(minutes=2)).replace(tzinfo=None)
    assert provider.token() == "tok-2"  # dentro del margen de 5 min: renueva

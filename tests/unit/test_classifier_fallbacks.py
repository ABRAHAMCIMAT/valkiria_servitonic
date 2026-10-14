"""Cobertura de las rutas de degradación determinista del clasificador."""

import pytest

from backend.agents.classifier import ClassifierAgent
from backend.core.llm import LLMConfig, MockLLM
from backend.core.models import Intent, Priority


class BrokenLLM(MockLLM):
    def chat_json(self, *args, **kwargs):
        raise RuntimeError("proveedor no disponible")


@pytest.fixture
def classifier():
    return ClassifierAgent(BrokenLLM(LLMConfig(provider="mock")))


@pytest.mark.parametrize(
    "message,intent,subcategory",
    [
        ("Necesito restablecer mi contraseña", Intent.SERVICE_REQUEST, "Password Reset"),
        ("Necesito una licencia de software", Intent.SERVICE_REQUEST, "Software License"),
        ("Quiero una laptop nueva", Intent.APPROVAL, "Hardware"),
        ("¿Cuál es el estado de mi ticket?", Intent.STATUS, ""),
        ("¿Cómo configuro la VPN paso a paso?", Intent.KNOWLEDGE, ""),
        ("Buenos días", Intent.GENERAL, ""),
    ],
)
def test_heuristic_fallback_categories(classifier, message, intent, subcategory):
    result = classifier.classify(message)
    assert result.intent == intent
    assert result.subcategory == subcategory


@pytest.mark.parametrize(
    "impact,urgency,expected",
    [
        (1, 1, Priority.P1),
        (2, 2, Priority.P2),
        (3, 2, Priority.P3),
        (3, 3, Priority.P4),
    ],
)
def test_priority_is_derived_when_provider_value_is_invalid(classifier, impact, urgency, expected):
    assert classifier._parse_priority("invalid", impact, urgency) == expected


def test_unknown_intent_degrades_to_general(classifier):
    assert classifier._parse_intent("not-in-catalog") == Intent.GENERAL


def test_invalid_provider_payload_degrades_to_heuristic():
    class InvalidPayloadLLM(MockLLM):
        def chat_json(self, *args, **kwargs):
            return {"intent": "invented"}

    classifier = ClassifierAgent(InvalidPayloadLLM(LLMConfig(provider="mock")))
    result = classifier.classify("Necesito una licencia")
    assert result.intent == Intent.SERVICE_REQUEST
    assert result.priority == Priority.P4

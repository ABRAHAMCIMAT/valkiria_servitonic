"""
API Server — punto de entrada del sistema multiagente.

Expone tres interfaces:
  1. REST API propia (/api/chat, /api/conversations, /api/health, /api/dashboard)
     para el frontend web incluido y el dashboard de observabilidad.
  2. Endpoint compatible con OpenAI (/v1/chat/completions) para que Jan
     (o cualquier cliente OpenAI) pueda conectarse como proveedor.
  3. Dashboard de métricas en 4 dimensiones (Negocio, Rendimiento, Costos,
     Orquestación) alimentado por telemetría JSON estandarizada.

Fase 0 (LLMOps): todos los endpoints requieren credencial (API key + rol),
CORS restringido por lista blanca, rate limiting por credencial/IP, redacción
de PII en logs y audit trail de acciones sensibles.

Ejecutar:  python -m backend.server   (puerto 8000 por defecto)
"""

from __future__ import annotations

import json
import os
import uuid

from fastapi import Depends, FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config
from .adapters import teams_cards
from .adapters.factory import (
    build_approval_store,
    build_conversation_store,
    build_notifier,
    build_ticketing,
)
from .agents.coordinator import CoordinatorAgent
from .agents.escalation import EscalationAgent
from .core.approvals import DECISIONS, EXPIRED, ApprovalRequest, ApprovalStorage
from .core.llm import LLM
from .core.storage import ConversationStorage
from .llmops.errors import AgentError, LLMOpsError, ProviderError, ValidationError
from .llmops.guardrails import default_guardrails
from .llmops.logging import get_logger, setup_logging
from .llmops.test_matrix import MAX_BATCH_SIZE, generate_batch, list_targets
from .observability.dashboard_api import build_dashboard_payload
from .observability.metrics import MetricsEngine
from .observability.telemetry import get_telemetry
from .observability.traced_coordinator import TracedCoordinator
from .security import (
    ROLE_ADMIN,
    ROLE_AGENT,
    ROLE_USER,
    Principal,
    get_audit_log,
    preview,
    rate_limit_dependency,
    require_auth,
    require_role,
)
from .security.botframework import BotFrameworkAuth

app = FastAPI(title="ServiceNow Multi-Agent System", version="2.2.0")

# --- Configuración centralizada (Fase 0) -----------------------------------
# Rutas de datos relativas y configurables; CORS por lista blanca.
config.ensure_dirs()
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"), log_file=config.LOG_FILE)
log = get_logger("server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,  # lista blanca, nunca "*"
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

audit = get_audit_log()


# --- manejo de errores tipados (LLMOps) -------------------------------------
# Traduce la jerarquía de excepciones de llmops/errors.py a respuestas HTTP
# coherentes, en vez de dejar que FastAPI devuelva un 500 genérico sin
# distinguir "el proveedor externo falló" de "hay un bug en un agente".
@app.exception_handler(ProviderError)
async def provider_error_handler(request: Request, exc: ProviderError):
    log.error("error del proveedor externo (LLM o ServiceNow)", extra={"error": str(exc)})
    return JSONResponse(
        {"error": "El proveedor externo (LLM o ServiceNow) no está disponible en este momento."},
        status_code=502,
    )


@app.exception_handler(AgentError)
async def agent_error_handler(request: Request, exc: AgentError):
    log.error("error inesperado en un agente", extra={"error": str(exc)})
    return JSONResponse(
        {"error": "Ocurrió un error interno al procesar tu solicitud. Intenta de nuevo."},
        status_code=500,
    )


@app.exception_handler(LLMOpsError)
async def llmops_error_handler(request: Request, exc: LLMOpsError):
    log.error(
        "error LLMOps no manejado específicamente", extra={"error": str(exc), "type": type(exc).__name__}
    )
    return JSONResponse({"error": str(exc)}, status_code=500)


# --- singletons ------------------------------------------------------------
# Fase 2: las clases concretas las elige adapters/factory.py por variable de
# entorno (TICKETING_PROVIDER, NOTIFY_CHANNEL, STORAGE_BACKEND); aquí solo se
# trabaja con las interfaces.
llm = LLM()
snow = build_ticketing()
notifier = build_notifier()
approvals: ApprovalStorage = build_approval_store()
coordinator = CoordinatorAgent(llm, snow, notifier, approvals)
escalator = EscalationAgent(llm, snow)
store: ConversationStorage = build_conversation_store()

# Bot de Teams: solo si está registrado en Entra ID (ver adapters/teams_bot.py)
_bot_app_id = os.getenv("TEAMS_BOT_APP_ID", "")
bot_auth = BotFrameworkAuth(_bot_app_id) if _bot_app_id else None

# --- observability ---------------------------------------------------------
telemetry = get_telemetry()
traced = TracedCoordinator(coordinator, telemetry)
metrics_engine = MetricsEngine()


class ChatRequest(BaseModel):
    message: str
    caller: str = "Carlos Carballo"
    conversation_id: str | None = None


class EscalateRequest(BaseModel):
    conversation_id: str


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    decided_by: str = Field(min_length=1, max_length=200)
    comment: str = Field(default="", max_length=1000)


class TestMatrixRequest(BaseModel):
    target: str
    count: int = Field(default=15, ge=1, le=MAX_BATCH_SIZE)


# --- Dashboard static files ------------------------------------------------
_dashboard_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard")
if os.path.isdir(_dashboard_dir):
    app.mount("/dashboard", StaticFiles(directory=_dashboard_dir, html=True), name="dashboard")


# --- Health -----------------------------------------------------------------
@app.get("/api/health")
def health():
    """Liveness público: sin datos de configuración sensibles."""
    return {"status": "ok"}


@app.get("/api/health/detail")
def health_detail(principal: Principal = Depends(require_role(ROLE_ADMIN))):
    """Detalle de configuración — solo admin."""
    return {
        "status": "ok",
        "llm_provider": llm.config.provider,
        "llm_model": llm.config.model,
        "ticketing_provider": os.getenv("TICKETING_PROVIDER", "servicenow").lower(),
        "servicenow_mode": "live" if snow.live else "demo",
        "notification_channel": notifier.channel,
        "notification_mode": getattr(notifier, "mode", "live" if notifier.live else "demo"),
        "storage_backend": os.getenv("STORAGE_BACKEND", "file").lower(),
        "observability": "enabled",
        "langfuse": "enabled" if telemetry.langfuse else "disabled",
        "app_env": config.APP_ENV,
    }


# --- REST API (frontend) ---------------------------------------------------
@app.post("/api/chat", dependencies=[Depends(rate_limit_dependency)])
def chat(req: ChatRequest, principal: Principal = Depends(require_auth)):
    # Guardrail de entrada (LLMOps)
    try:
        req.message = default_guardrails.validate_input(req.message)
    except ValidationError as e:
        audit.record(
            action="chat.rejected",
            actor=principal.key_id,
            outcome="rejected",
            metadata={"reason": "guardrail"},
        )
        return JSONResponse({"error": str(e)}, status_code=400)
    # Fase 0: nunca se registra el mensaje crudo del usuario (PII)
    # 'message' es clave reservada de LogRecord: se usa message_preview.
    # preview() omite el contenido salvo LOG_USER_CONTENT=true (privacidad primero).
    log.info("chat recibido", extra={"caller": req.caller, "message_preview": preview(req.message, 120)})
    audit.record(
        action="chat.received",
        actor=principal.key_id,
        target=req.conversation_id or "",
        metadata={"caller": req.caller},
    )
    conv = traced.handle(req.message, caller=req.caller)
    store.update(conv)
    return conv.to_dict()


@app.get("/api/conversations", dependencies=[Depends(rate_limit_dependency)])
def list_conversations(principal: Principal = Depends(require_role(ROLE_AGENT))):
    return [c.to_dict() for c in store.list()]


@app.get("/api/conversations/{conv_id}", dependencies=[Depends(rate_limit_dependency)])
def get_conversation(conv_id: str, principal: Principal = Depends(require_role(ROLE_AGENT))):
    conv = store.get(conv_id)
    if not conv:
        return JSONResponse({"error": "not found"}, status_code=404)
    return conv.to_dict()


@app.post("/api/escalate", dependencies=[Depends(rate_limit_dependency)])
def escalate(req: EscalateRequest, principal: Principal = Depends(require_role(ROLE_AGENT))):
    conv = store.get(req.conversation_id)
    if not conv:
        return JSONResponse({"error": "not found"}, status_code=404)
    result = escalator.escalate(conv)
    conv.status = "escalated"
    conv.add("escalacion", result["message"], data=result)
    store.update(conv)
    audit.record(
        action="escalate",
        actor=principal.key_id,
        target=req.conversation_id,
        metadata={"team": result.get("team", "") if isinstance(result, dict) else ""},
    )
    return result


# --- Aprobaciones (Fase 2, I7) ----------------------------------------------
def _resolve_approval(
    approval_id: str, decision: str, decided_by: str, comment: str, actor: str
) -> tuple[ApprovalRequest | None, bool]:
    """Camino único para resolver una aprobación, venga de Teams o de la API.
    `approvals.decide` es atómico: solo la primera decisión reanuda la
    conversación; las repetidas o tardías devuelven el estado ya registrado."""
    approval, changed = approvals.decide(approval_id, decision, decided_by, comment)
    if approval is None:
        return None, False
    conv = store.get(approval.conversation_id)
    resumable = changed or approval.status == EXPIRED
    if conv and conv.status == "awaiting_approval" and resumable:
        coordinator.resume_approval(conv, approval)
        store.update(conv)
    telemetry.approval(
        approval.conversation_id,
        approval.resource,
        approval.manager,
        notifier.channel,
        status=approval.status,
    )
    audit.record(
        action=f"approval.{decision}",
        actor=actor,
        target=approval.id,
        outcome="ok" if changed else f"ignored:{approval.status}",
        metadata={"conversation_id": approval.conversation_id, "ticket": approval.ticket_number},
    )
    return approval, changed


@app.get("/api/approvals", dependencies=[Depends(rate_limit_dependency)])
def list_approvals(principal: Principal = Depends(require_role(ROLE_AGENT))):
    return [a.to_dict() for a in approvals.list_pending()]


@app.post("/api/approvals/{approval_id}/decision", dependencies=[Depends(rate_limit_dependency)])
def decide_approval(
    approval_id: str,
    req: ApprovalDecisionRequest,
    principal: Principal = Depends(require_role(ROLE_AGENT)),
):
    """Registra la decisión de una aprobación sin bot de Teams (modo
    Workflows, plan B con Power Automate, o un agente de mesa de ayuda)."""
    approval, changed = _resolve_approval(
        approval_id, req.decision, req.decided_by, req.comment, actor=principal.key_id
    )
    if approval is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    if not changed:
        return JSONResponse(
            {
                "error": f"La aprobación ya no está pendiente ({approval.status}).",
                "approval": approval.to_dict(),
            },
            status_code=409,
        )
    return approval.to_dict()


def _invoke_response(card: dict) -> dict:
    return {"statusCode": 200, "type": teams_cards.CARD_CONTENT_TYPE, "value": card}


@app.post("/api/teams/messages", dependencies=[Depends(rate_limit_dependency)])
async def teams_messages(request: Request, authorization: str | None = Header(default=None)):
    """Endpoint de mensajería del bot de Teams (Azure Bot → Cloud Run).
    No usa API keys: lo autentica el JWT firmado por Bot Framework."""
    if bot_auth is None:
        return JSONResponse({"error": "Bot de Teams no configurado."}, status_code=503)
    activity = await request.json()
    bot_auth.verify(authorization, activity.get("serviceUrl"))

    if activity.get("type") != "invoke" or activity.get("name") != "adaptiveCard/action":
        # conversationUpdate, mensajes de texto, etc.: no se procesan por ahora
        return JSONResponse({}, status_code=200)

    action = (activity.get("value") or {}).get("action") or {}
    verb = str(action.get("verb", ""))
    data = action.get("data") or {}
    decision = {teams_cards.VERB_APPROVE: "approved", teams_cards.VERB_REJECT: "rejected"}.get(verb)
    approval = approvals.get(str(data.get("approval_id", "")))
    if decision not in DECISIONS or approval is None:
        return _invoke_response(teams_cards.error_card("Solicitud de aprobación no encontrada."))

    sender = activity.get("from") or {}
    if approval.manager_aad_id and sender.get("aadObjectId") != approval.manager_aad_id:
        audit.record(
            action=f"approval.{decision}",
            actor=f"teams:{sender.get('aadObjectId', '')}",
            target=approval.id,
            outcome="forbidden",
        )
        return _invoke_response(
            teams_cards.error_card(f"Solo {approval.manager} puede responder esta aprobación.")
        )

    resolved, _ = _resolve_approval(
        approval.id,
        decision,
        sender.get("name") or approval.manager,
        str(data.get("comment", ""))[:1000],
        actor=f"teams:{sender.get('aadObjectId', '')}",
    )
    return _invoke_response(teams_cards.approval_card(resolved or approval))


# --- Generador de matrices de pruebas (HU-004) ------------------------------
@app.get("/api/test-matrix/targets", dependencies=[Depends(rate_limit_dependency)])
def test_matrix_targets(principal: Principal = Depends(require_role(ROLE_AGENT))):
    """Objetivos (agentes/endpoints) disponibles para generar casos de prueba."""
    return {"targets": list_targets()}


@app.post("/api/test-matrix", dependencies=[Depends(rate_limit_dependency)])
def test_matrix(req: TestMatrixRequest, principal: Principal = Depends(require_role(ROLE_AGENT))):
    """Genera un lote de hasta MAX_BATCH_SIZE casos de prueba (positivos,
    negativos, de borde/límite) para el agente/endpoint indicado en `target`.
    Los errores del proveedor LLM ya quedan cubiertos por el
    @app.exception_handler(ProviderError) registrado arriba."""
    try:
        batch = generate_batch(llm, req.target, count=req.count)
    except KeyError as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    audit.record(
        action="test_matrix.generate",
        actor=principal.key_id,
        target=req.target,
        metadata={"count": req.count, "generated": batch["generated"]},
    )
    return batch


# --- Dashboard API ---------------------------------------------------------
@app.get("/api/dashboard", dependencies=[Depends(rate_limit_dependency)])
def dashboard(principal: Principal = Depends(require_role(ROLE_AGENT))):
    """Four-dimension metrics for the observability dashboard."""
    return build_dashboard_payload(metrics_engine)


@app.get("/api/dashboard/events", dependencies=[Depends(rate_limit_dependency)])
def dashboard_events(principal: Principal = Depends(require_role(ROLE_ADMIN))):
    """Raw standardized telemetry events (for debugging / Langfuse export)."""
    return telemetry.events()


# --- OpenAI-compatible endpoint (for Jan) ----------------------------------
class OpenAIRequest(BaseModel):
    model: str = "servicenow-multiagent"
    messages: list[dict]
    stream: bool = False


@app.post("/v1/chat/completions", dependencies=[Depends(rate_limit_dependency)])
async def openai_compat(req: OpenAIRequest, principal: Principal = Depends(require_role(ROLE_USER))):
    # Extract the last user message
    user_msg = ""
    for m in req.messages:
        if m.get("role") == "user":
            user_msg = m.get("content", "")

    try:
        user_msg = default_guardrails.validate_input(user_msg)
    except ValidationError as e:
        audit.record(
            action="chat.rejected",
            actor=principal.key_id,
            outcome="rejected",
            metadata={"reason": "guardrail", "source": "openai"},
        )
        return JSONResponse({"error": {"message": str(e), "type": "invalid_request_error"}}, status_code=400)

    audit.record(
        action="chat.received", actor=principal.key_id, metadata={"source": "openai", "caller": "jan"}
    )
    conv = traced.handle(user_msg)
    store.update(conv)

    # Build a coherent assistant reply from the agent trace
    reply = _build_reply(conv)

    if req.stream:

        async def gen():
            for chunk in _chunk_text(reply):
                yield f"data: {json.dumps({'choices': [{'delta': {'content': chunk}}]})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "model": req.model,
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": reply}, "finish_reason": "stop"}
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _build_reply(conv) -> str:
    parts = []
    for m in conv.messages:
        if m.role == "assistant" and m.content:
            parts.append(m.content)
    return "\n\n".join(parts) if parts else "He procesado tu solicitud."


def _chunk_text(text: str, size: int = 40):
    for i in range(0, len(text), size):
        yield text[i : i + size]


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    print(f"ServiceNow Multi-Agent API en http://localhost:{port}")
    print(f"  LLM: {llm.config.provider} ({llm.config.model})")
    print(f"  ServiceNow: {'LIVE' if snow.live else 'DEMO'}")
    print(f"  Notificaciones: {notifier.channel} ({getattr(notifier, 'mode', '')})")
    print(f"  Observabilidad: telemetría JSON + Langfuse ({'ON' if telemetry.langfuse else 'OFF'})")
    print("  Seguridad: auth + RBAC + rate limit + redacción PII + audit trail")
    print(f"  CORS: {config.CORS_ORIGINS}")
    print(f"  Dashboard: http://localhost:{port}/dashboard")
    print(f"  Endpoint OpenAI-compatible (para Jan): http://localhost:{port}/v1/chat/completions")
    # El contenedor debe escuchar en todas sus interfaces para que Cloud Run
    # pueda enrutar tráfico. La exposición externa sigue controlada por IAM,
    # CORS, autenticación de aplicación y la configuración de ingress.
    uvicorn.run(app, host="0.0.0.0", port=port)  # nosec B104

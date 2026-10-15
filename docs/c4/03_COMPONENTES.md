# Nivel 3 — Componentes

```mermaid
C4Component
    title Valkiria API — Componentes
    Container_Boundary(api, "Docker local / FastAPI") {
        Component(server, "API", "backend/server.py", "Endpoints, auth, callbacks y estáticos")
        Component(coord, "Coordinador", "backend/agents/coordinator.py", "Orquestación")
        Component(agents, "Agentes", "backend/agents", "Clasificación, diagnóstico, políticas, ejecución, KB, métricas y escalación")
        Component(ticketing, "ServiceTonic Adapter", "backend/adapters", "Tickets, notas, KB y contactos")
        Component(teams, "Teams Adapter/Bot", "backend/adapters/teams*.py", "Cards, Graph y Bot Framework")
        Component(llm, "LLM Facade", "backend/core/llm.py", "Mock determinista para el PoC")
        Component(stores, "Stores", "backend/core", "Archivo/memoria local")
        Component(sec, "Security", "backend/security", "RBAC, rate limit, redacción, JWT y auditoría")
        Component(obs, "Observability", "backend/observability", "Trazas, métricas y dashboard")
        Component(llmops, "LLMOps", "backend/llmops", "Prompts, evals, errores y guardrails")
    }

    Rel(server, coord, "handle/resume")
    Rel(coord, agents, "orquesta")
    Rel(agents, ticketing, "opera tickets/KB")
    Rel(coord, teams, "solicita aprobación")
    Rel(agents, llm, "clasifica/sintetiza")
    Rel(server, stores, "persiste")
    Rel(server, sec, "protege")
    Rel(coord, obs, "emite")
    Rel(agents, llmops, "valida/evalúa")
```

## Nota de implementación

El contrato objetivo es neutral y ServiceTonic es el único proveedor
productivo. Cualquier identificador heredado que persista en código es deuda
técnica del incremento I1 y no define la arquitectura funcional.

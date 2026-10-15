# Nivel 4 — Código y secuencias

## Flujo de ticket

```mermaid
sequenceDiagram
    actor U as Usuario
    participant API as Docker local / FastAPI
    participant C as Coordinador
    participant V as Mock LLM
    participant ST as ServiceTonic
    participant FS as Firestore

    U->>API: POST /api/chat
    API->>C: handle(message)
    C->>V: clasificar y estructurar
    V-->>C: intención/categoría/prioridad
    C->>ST: crear o actualizar ticket
    ST-->>C: ticket y estado
    C->>FS: guardar conversación
    C-->>API: respuesta
    API-->>U: resultado y número de ticket
```

## Flujo de aprobación Teams

```mermaid
sequenceDiagram
    actor U as Usuario
    participant C as Coordinador
    participant FS as Firestore
    participant T as Microsoft Teams
    actor M as Manager
    participant ST as ServiceTonic

    U->>C: solicitud que requiere aprobación
    C->>FS: crear ApprovalRequest
    C->>T: Adaptive Card 1:1
    T->>M: Aprobar / Rechazar
    M->>T: decisión y comentario
    T->>C: POST /api/teams/messages
    C->>FS: decisión atómica
    C->>ST: estado/nota/acción
    C-->>U: conversación reanudada
```

## Estados principales

```text
in_progress → awaiting_approval → resolved
                              └→ rejected
in_progress → escalated
```

## Contratos objetivo

- `TicketingPort`: crear, leer, listar y actualizar tickets; notas; KB; manager.
- `NotifierPort`: avisos y aprobaciones Teams.
- `ConversationStorage`: persistencia de conversaciones.
- `ApprovalStorage`: persistencia y decisión idempotente.
- `LLM`: proveedor mock determinista durante el PoC.

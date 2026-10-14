# Nivel 1 — Contexto

```mermaid
C4Context
    title Valkiria ServiceTonic — Contexto
    Person(usuario, "Usuario", "Reporta incidencias, solicita servicios y consulta conocimiento")
    Person(manager, "Manager", "Aprueba o rechaza solicitudes en Teams")
    Person(soporte, "Soporte N2/N3", "Recibe escalaciones con contexto")

    System(valkiria, "Valkiria ServiceTonic", "Asistente multiagente de soporte TI")
    System_Ext(servicetonic, "ServiceTonic", "Ticketing, SLA, KB, historial y reporting")
    System_Ext(teams, "Microsoft Teams", "Notificaciones y aprobaciones interactivas")
    System_Ext(gcp, "Google Cloud", "Cloud Run, Vertex AI, Firestore, observabilidad y secretos")
    System_Ext(jan, "Jan", "Cliente/proveedor LLM opcional para desarrollo local")

    Rel(usuario, valkiria, "Conversa", "HTTPS")
    Rel(valkiria, servicetonic, "Gestiona tickets y conocimiento", "REST")
    Rel(valkiria, teams, "Envía tarjetas y recibe decisiones", "Bot Framework/Graph")
    Rel(valkiria, gcp, "Ejecuta, persiste y observa", "Servicios administrados")
    Rel(manager, teams, "Aprueba/rechaza", "Adaptive Card")
    Rel(valkiria, soporte, "Escala con resumen", "Ticket ServiceTonic")
    Rel(jan, valkiria, "Consume /v1/chat/completions", "OpenAI-compatible")
```

## Sistemas externos

| Sistema | Uso | Estado |
|---|---|---|
| ServiceTonic | Sistema único de registro y conocimiento | API/sandbox pendientes |
| Microsoft Teams | Canal único de aprobación | Código listo; tenant pendiente |
| Google Cloud | Plataforma completa de producción | IaC listo; proyectos pendientes |
| Jan | Desarrollo local opcional | Soportado |

# Nivel 2 — Contenedores

```mermaid
C4Container
    title Valkiria ServiceTonic — Contenedores
    Person(usuario, "Usuario")
    Person(manager, "Manager")

    System_Boundary(local, "Equipo local / Docker") {
        Container(api, "Valkiria API", "Docker / FastAPI", "Chat, agentes, callbacks y dashboard")
        ContainerDb(state, "Estado PoC", "Archivo + memoria", "Conversaciones y aprobaciones de una instancia")
        Container(llm, "Mock LLM", "Python", "Clasificación determinista")
        ContainerDb(logs, "Observabilidad local", "JSONL", "Logs, auditoría y telemetría")
    }

    System_Ext(servicetonic, "ServiceTonic")
    System_Ext(teams, "Microsoft Teams")

    Rel(usuario, api, "Conversa", "HTTPS")
    Rel(api, servicetonic, "Tickets, KB, SLA", "REST")
    Rel(api, teams, "Adaptive Cards", "Bot/Graph")
    Rel(manager, teams, "Decide")
    Rel(api, state, "Lee/escribe")
    Rel(api, llm, "Inferencia")
    Rel(api, logs, "Emite JSON saneado")
```

## Despliegue local

Docker Compose mantiene un modo mock reproducible. Producción usa servicios
administrados de Google Cloud y no depende del filesystem local.

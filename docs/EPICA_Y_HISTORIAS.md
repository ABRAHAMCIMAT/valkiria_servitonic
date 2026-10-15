# Épica e historias de usuario — Valkiria ServiceTonic

## Épica

> Alcance PoC vigente: despliegue local, tickets ServiceTonic y aprobaciones
> Microsoft Teams. Los criterios Google Cloud quedan diferidos.

**Como** usuario y equipo de soporte, **quiero** resolver incidencias,
solicitudes y consultas mediante una conversación integrada con ServiceTonic,
Microsoft Teams y Google Cloud, **para** reducir tiempos de resolución y
mantener trazabilidad, seguridad y control operacional.

## Criterios de aceptación del PoC

- ServiceTonic es el sistema único de registro de tickets.
- Teams gestiona notificaciones y aprobaciones interactivas.
- Docker local ejecuta la aplicación de forma reproducible.
- El LLM mock permite una demostración determinista sin nube.
- Los secretos permanecen únicamente en `.env.poc`, fuera de Git.
- CI exige pruebas, cobertura >90 %, análisis estático y seguridad.

## Historias

| ID | Historia | Estado |
|---|---|---|
| HU-001 | Conversación en lenguaje natural | ✅ Código listo |
| HU-002 | Clasificación, prioridad y SLA | ✅ Código listo |
| HU-003 | Crear ticket en ServiceTonic | 🔴 Adaptador pendiente |
| HU-004 | Diagnóstico de causa raíz | 🟡 Demo listo; fuentes reales pendientes |
| HU-005 | Aplicar políticas | ✅ Código listo |
| HU-006 | Desbloqueo de cuenta | 🔴 Ejecutor real pendiente |
| HU-007 | Restablecimiento seguro de contraseña | 🔴 SSPR/Graph pendiente |
| HU-008 | Asignación de licencia | 🔴 Graph y aprobación pendiente |
| HU-009 | Respuesta RAG desde KB ServiceTonic | 🔴 API/KB pendiente |
| HU-010 | Aprobación en Microsoft Teams | 🟡 Código listo; tenant pendiente |
| HU-011 | Seguimiento proactivo de ticket | 🔴 Webhook/polling pendiente |
| HU-012 | Escalación con resumen ejecutivo | ✅ Código listo |
| HU-013 | Integración OpenAI-compatible/Jan | ✅ Desarrollo local |
| HU-014 | Modo mock sin credenciales | ✅ |
| HU-015 | Proveedor LLM configurable | ✅ Jan/OpenAI/Vertex/Mock |
| HU-016 | Telemetría estandarizada | ✅ Código listo |
| HU-017 | Dashboard de cuatro dimensiones | ✅ Código listo |
| HU-018 | Dashboard integrado | ✅ Código listo |
| HU-019 | Agente de métricas | ✅ Código listo |
| HU-020 | Logging estructurado | ✅ Código listo |
| HU-021 | Errores y reintentos | ✅ Código listo |
| HU-022 | Guardrails | ✅ Código listo |
| HU-023 | Versionado de prompts | ✅ Código listo |
| HU-024 | Evaluación de agentes | 🟡 Local lista; Vertex real pendiente |
| HU-025 | Langfuse opcional | ✅ Código listo |
| HU-026 | Patrones de diseño | ✅ Registry/Strategy |
| HU-027 | Documentación en español | ✅ |
| HU-028 | Generación de matrices de pruebas | ✅ |

## Definition of Done productiva

1. Ticket real creado, consultado y actualizado en ServiceTonic.
2. Aprobación real completada desde Teams.
3. Conversación y aprobación se mantienen durante la sesión local.
4. Logs locales no contienen PII o secretos crudos.
5. Evidencia del flujo completo aprobada por el equipo del PoC.

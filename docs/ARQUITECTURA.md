# Arquitectura de Valkiria ServiceTonic

> Arquitectura objetivo actualizada el 14 de octubre de 2026. ServiceTonic es
> el sistema único de ticketing; Microsoft Teams es el canal único de
> aprobaciones; Google Cloud es la plataforma de ejecución y operación.

## Visión general

Valkiria recibe solicitudes de soporte en lenguaje natural, las clasifica,
consulta conocimiento, crea o actualiza tickets en
[ServiceTonic](https://www.servicetonic.com/es/ticketing-aplicacion/), aplica
políticas, solicita aprobaciones en Microsoft Teams y escala a soporte humano
con contexto. La plataforma se despliega en Google Cloud sin llaves JSON.

```mermaid
flowchart LR
    U[Usuario] --> CR[Cloud Run · API Valkiria]
    T[Microsoft Teams] <--> CR
    CR <--> ST[ServiceTonic · Ticketing/KB/SLA]
    CR --> V[Vertex AI · Gemini]
    CR <--> FS[Firestore]
    CR --> CL[Cloud Logging]
    CL --> BQ[BigQuery]
    SM[Secret Manager] --> CR
    GH[GitHub Actions] -->|WIF| AR[Artifact Registry]
    AR --> CR
    SCH[Cloud Scheduler] --> CR
```

## Stack tecnológico de Google Cloud

| Servicio | Responsabilidad |
|---|---|
| Cloud Run | API FastAPI, frontend y dashboard |
| Vertex AI | Gemini para clasificación, síntesis y evaluaciones |
| Firestore | Conversaciones y aprobaciones multiinstancia |
| Secret Manager | API keys, token ServiceTonic y secreto del bot |
| Artifact Registry | Imágenes de contenedor |
| Cloud Logging | Logs estructurados y auditoría |
| BigQuery | Histórico de telemetría, costos y KPIs |
| Cloud Monitoring | Alertas, latencia, errores y disponibilidad |
| Cloud Scheduler | Recordatorios y expiración de aprobaciones |
| IAM + WIF | Identidad de runtime y despliegue sin llaves JSON |
| Cloud Armor + Load Balancing | Protección perimetral prevista para producción |

## Componentes de aplicación

| Componente | Responsabilidad |
|---|---|
| FastAPI | REST, endpoint OpenAI-compatible, health y dashboard |
| Coordinador | Orquesta clasificación, diagnóstico, políticas y ejecución |
| Clasificador | Intención, categoría, grupo, impacto, urgencia y prioridad |
| Diagnóstico | Determina causa raíz y acción recomendada |
| Políticas | Decide autoservicio o aprobación |
| Ejecución | Ejecuta acciones autorizadas o genera trabajo técnico |
| Conocimiento | Recupera artículos de ServiceTonic y sintetiza respuestas |
| Escalación | Entrega resumen ejecutivo a Nivel 2/3 |
| Métricas | Responde consultas operativas y alimenta el dashboard |

## Integraciones oficiales

### ServiceTonic

Sistema de registro para tickets, estados, prioridades, SLA, categorías,
historial, base de conocimiento y seguimiento. La API y los catálogos exactos
deben confirmarse con el proveedor antes de implementar el adaptador productivo.

### Microsoft Teams

Canal único de notificaciones y aprobaciones. Las Adaptive Cards permiten
aprobar o rechazar y el callback reanuda la conversación de forma idempotente.

### Google Cloud

Plataforma única de cómputo, IA, persistencia, secretos, observabilidad,
automatización y seguridad. GitHub Actions se autentica mediante Workload
Identity Federation.

## Principios

- Puertos antes que adaptadores.
- Configuración por entorno y mínimo privilegio.
- Sin secretos en código, variables planas o estado Terraform.
- Modo mock determinista para pruebas sin red.
- Despliegues sin tráfico, smoke test y promoción posterior.
- PII y secretos saneados antes de Logging/BigQuery.
- Ninguna acción reporta éxito sin confirmación del sistema ejecutor.

Ver también [modelo C4](c4/00_INDICE.md), [seguridad](SEGURIDAD.md) y
[despliegue GCP](DESPLIEGUE_GCP.md).

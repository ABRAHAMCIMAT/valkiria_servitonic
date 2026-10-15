# Plan incremental — ServiceTonic, Microsoft Teams y Google Cloud

> Estado actualizado al 14 de octubre de 2026. ServiceTonic es el sistema de
> ticketing objetivo; Teams es el canal de aprobación; Google Cloud es la
> plataforma completa de operación.

## Objetivo

Desplegar Valkiria en Google Cloud, integrar ServiceTonic como sistema de
registro y completar aprobaciones interactivas en Teams.

## Estado de incrementos

| Incremento | Estado | Pendiente principal |
|---|---|---|
| I0 — Prerrequisitos | 🟡 | OpenAPI confirmado; faltan credenciales/catálogos, proyecto GCP y Entra ID |
| I1 — Puertos | 🟡 | Completar nombres/contrato neutrales y adaptador demo |
| I2 — Vertex AI | 🟡 | Evaluaciones reales con Gemini |
| I3 — Cloud Run | 🟡 | Ejecutar bootstrap y aplicar Terraform |
| I4 — Firestore/observabilidad | 🟡 | Validación multiinstancia, Logging y BigQuery |
| I5 — Tickets ServiceTonic | 🟡 | Implementar adaptador y validar contra Valtre |
| I6 — KB/contactos/acciones | 🔴 | RAG, Graph y ejecutores reales |
| I7 — Teams | 🟡 | Crear bot/app, instalar y probar en tenant |
| I8 — Producción | ⚪ | Hardening, carga, piloto y corte |

## I0 — Prerrequisitos

### ServiceTonic

- OpenAPI/Postman o documentación de Web Services REST.
- Sandbox y usuario técnico de mínimo privilegio.
- Autenticación, paginación y límites.
- Catálogos de estados, prioridades, categorías, grupos y SLA.
- Tickets, notas, KB, contactos, manager y webhooks.
- Datos de prueba y pruebas contractuales.

Fuente funcional pública:
[aplicación de ticketing ServiceTonic](https://www.servicetonic.com/es/ticketing-aplicacion/).
La página confirma ticketing omnicanal, automatización, SLA, reporting,
base de conocimiento e integraciones; los endpoints exactos deben venir del
proveedor.

### Google Cloud

- Proyectos dev/prod y facturación.
- Buckets de estado Terraform.
- WIF y cuentas de servicio.
- Cuotas Vertex y presupuesto.
- Regiones y residencia de datos.

### Microsoft

- Registro Entra ID y Azure Bot.
- Permisos Graph mínimos.
- Instalación de app personalizada Teams.
- Usuarios/managers de prueba.

## I1 — Contratos

- `TicketingPort`: tickets, notas, KB, manager y acciones.
- `NotifierPort`: Teams informativo e interactivo.
- Fábrica por variables de entorno.
- Estados internos neutrales.
- Modo mock sin dependencia de proveedores.

## I2 — Vertex AI

- Gemini mediante endpoint OpenAI-compatible.
- ADC en desarrollo y cuenta runtime en Cloud Run.
- Renovación automática de token.
- Comparación de precisión, JSON válido, p95 y costo.

## I3–I4 — Stack Google Cloud

| Servicio | Uso |
|---|---|
| Cloud Run | API y frontend |
| Artifact Registry | Imágenes |
| Vertex AI | Gemini y embeddings |
| Firestore | Conversaciones/aprobaciones |
| Secret Manager | Secretos externos |
| Cloud Logging | Aplicación y auditoría |
| BigQuery | Telemetría histórica |
| Cloud Monitoring | Alertas/SLO |
| Cloud Scheduler | Recordatorios y jobs |
| IAM/WIF | Identidad sin llaves |
| Cloud Armor/LB | Protección productiva |

## I5 — ServiceTonic tickets

1. Lectura en modo sombra.
2. Mapeo configurable de estados/catálogos.
3. Creación idempotente por `conversation_id`.
4. Actualización, notas internas/públicas y resolución.
5. Pruebas simuladas y contractuales contra sandbox.

## I6 — Conocimiento, contactos y acciones

- KB vía API o sincronización programada.
- Embeddings Vertex y búsqueda vectorial en Firestore si es necesario.
- Manager desde ServiceTonic o Microsoft Graph.
- Acciones reales vía Graph/runbook; si no hay ejecutor, crear ticket.
- Nunca reportar éxito sin confirmación.

## I7 — Microsoft Teams

- Workflows para avisos.
- Azure Bot + Adaptive Cards para aprobar/rechazar.
- JWT, audiencia, issuer y `serviceUrl` validados.
- Aprobador comparado con `aadObjectId` del manager.
- Decisión idempotente y reanudación de conversación.
- Recordatorio y escalación mediante Cloud Scheduler.

## I8 — Producción

- Cloud Armor, dominio y TLS administrado.
- IAM/secretos revisados y rotados.
- Pruebas de carga y cuotas.
- Dashboard/alertas/SLO.
- Revisión de PII y residencia.
- Revisión candidata sin tráfico, piloto, promoción y rollback.

## Definition of Done

- ServiceTonic procesa tickets reales de extremo a extremo.
- Teams completa aprobaciones reales.
- Vertex cumple la línea base.
- Firestore funciona entre instancias.
- Logging/BigQuery no contienen PII ni secretos crudos.
- CI y Quality Gate permanecen en verde.
- Piloto y rollback aprobados.

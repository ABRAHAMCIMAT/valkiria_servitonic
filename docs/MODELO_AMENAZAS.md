# Modelo de amenazas — GCP, ServiceTonic y Microsoft 365

> Alcance: API multiagente desplegada en Cloud Run y sus integraciones.
> Método: STRIDE simplificado. Revisar antes de cada corte a producción y al
> incorporar un proveedor o flujo de datos nuevo.

## Activos y fronteras de confianza

| Activo | Frontera |
|---|---|
| API keys, tokens ServiceTonic y secreto del bot | Secret Manager → Cloud Run |
| Conversaciones, aprobaciones y datos personales | Usuario → API → Firestore |
| Prompts, respuestas y telemetría | API → Vertex AI / Cloud Logging / BigQuery |
| Tickets y artículos de conocimiento | API → ServiceTonic |
| Identidad del manager y decisiones | API → Graph / Bot Framework / Teams |
| Artefactos y despliegues | GitHub Actions → WIF → Artifact Registry / Cloud Run |

## Amenazas y controles

| ID | Amenaza | Control actual | Riesgo/acción pendiente |
|---|---|---|---|
| T01 | Suplantación mediante API key robada | Hash en auditoría, Secret Manager, RBAC | Rotación periódica; migrar usuarios finales a OIDC |
| T02 | Elevación de privilegio entre roles | Jerarquía explícita y pruebas 401/403 | Ejecutar `security_smoke.py` en cada entorno |
| T03 | Exfiltración por logs | Supresión del mensaje y saneamiento recursivo | Verificar canarios en Cloud Logging y BigQuery |
| T04 | Inyección de prompt | Guardrails de entrada y validación de salida | Mantener pruebas adversariales por modelo |
| T05 | Abuso/denegación de servicio | Rate limit, concurrencia Cloud Run | El contador sigue siendo por instancia; evaluar almacén global |
| T06 | Alteración o repetición de aprobaciones | JWT Bot Framework, manager AAD, decisión atómica | Validar en tenant real y automatizar expiración |
| T07 | Webhook o actividad falsa de Teams | Firma, issuer, audience y `serviceUrl` validados | Rotar secreto/certificado y alertar vencimiento |
| T08 | Acceso excesivo de la cuenta runtime | Roles funcionales y secretos por recurso | Revisar IAM tras cada cambio de `secret_env` |
| T09 | Despliegue desde repositorio/ref no autorizado | WIF limitado a repo, environment y main/tags | Proteger environments y tags en GitHub |
| T10 | Fuga de datos hacia Vertex | Redacción y proyecto controlado | Confirmar residencia, retención y contrato de datos |
| T11 | Fuga o manipulación en ServiceTonic | TLS, usuario técnico y permisos mínimos | Confirmar API, allowlist, auditoría y límites en I0 |
| T12 | Artículo interno expuesto por RAG | Aún no implementado | Filtrar visibilidad antes de indexar o responder |
| T13 | Acción de autoservicio falsa o no autorizada | Política y aprobación | No reportar éxito sin confirmación del ejecutor |
| T14 | Pérdida/manipulación de auditoría | Sink separado y retención de 365 días | Restringir lectura/borrado y probar consulta/retención |
| T15 | Dependencia vulnerable | Dependabot y `pip-audit` | Bloquear CI ante vulnerabilidades corregibles |

## Flujos de PII

| Destino | Datos mínimos previstos | Restricción |
|---|---|---|
| Vertex AI | Problema redactado y contexto necesario | No enviar credenciales ni campos innecesarios |
| ServiceTonic | Identidad, descripción, categoría y ticket | Usuario técnico con mínimo privilegio |
| Microsoft Graph/Teams | Correo/ID del manager y detalle mínimo de aprobación | No incluir conversación completa en tarjetas |
| Firestore | Conversación y estado de aprobación | TTL, IAM y separación por entorno |
| Logging/BigQuery | IDs, métricas y contenido saneado | Nunca guardar claves ni texto crudo del usuario |

## Evidencia exigida para cerrar Fase 0

1. `make security` en verde.
2. Suite completa y cobertura en verde.
3. `make security-live BASE_URL=... ALLOWED_ORIGIN=...` en dev y producción.
4. Consulta de Cloud Logging/BigQuery sin los canarios de PII y secretos.
5. Export de IAM revisado por un segundo responsable.
6. Registro de una rotación exitosa y de su rollback.

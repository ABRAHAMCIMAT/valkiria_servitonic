# Fase 0 — Seguridad base

> Estado: 🟡 código completo; evidencia cloud pendiente.

## Objetivo

Proteger la API y los datos que circulan entre Valkiria, ServiceTonic,
Microsoft Teams y Google Cloud.

## Implementado

- API keys y roles `user`, `agent`, `admin`.
- CORS explícito y fail-fast.
- Rate limiting.
- Guardrails de entrada/salida.
- Auditoría estructurada.
- Redacción recursiva de PII y secretos.
- Validación JWT de Bot Framework.
- Secret Manager e IAM por secreto definidos en Terraform.
- WIF restringido a repositorio, environment y referencias autorizadas.
- Smoke test automatizado y workflows de rotación/evidencia.

## Evidencia local

- 508 pruebas aprobadas.
- 91.19 % de cobertura.
- 12/12 verificaciones del smoke test.
- Bandit sin hallazgos medios/altos.
- `pip-audit` sin vulnerabilidades conocidas.

## Pendiente de cierre

- Crear y desplegar entorno dev en Google Cloud.
- Ejecutar smoke test contra dev y prod.
- Validar canarios en Cloud Logging y BigQuery.
- Revisar IAM efectivo y ausencia de llaves JSON.
- Rotar API keys, token ServiceTonic y secreto Teams.
- Obtener aprobación de un segundo responsable.

## Criterio de cierre

Todos los workflows de seguridad deben estar en verde y sus artefactos de
evidencia aprobados antes del piloto productivo.

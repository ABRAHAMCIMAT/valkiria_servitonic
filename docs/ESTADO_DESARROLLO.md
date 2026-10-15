# Estado consolidado del desarrollo

> Corte: **14 de octubre de 2026** · Repositorio:
> `ABRAHAMCIMAT/valkiria_servitonic` · Rama activa: `main`.

## Resumen ejecutivo

Valkiria es un sistema multiagente de soporte TI con API FastAPI, endpoint
OpenAI-compatible, seguridad RBAC, observabilidad, dashboard, pruebas
automatizadas e infraestructura como código para Google Cloud. La aplicación
funciona en modo demo y su código de integración con Vertex AI, Firestore y
Teams está implementado. Todavía no existe infraestructura GCP real ni
integración ServiceTonic, por lo que no está lista para producción.

## Indicadores verificables

| Indicador | Estado |
|---|---:|
| Pruebas automatizadas | **508 aprobadas** |
| Cobertura total | **91.19 %** |
| Umbral de cobertura | **> 90 %** |
| Ruff | Verde |
| Mypy | Verde, 49 archivos |
| Bandit | Sin hallazgos medios/altos |
| `pip-audit` | Sin vulnerabilidades conocidas |
| Smoke test de seguridad local | **12/12** |
| SonarCloud | Configurado en GitHub Actions; requiere Quality Gate externo |
| Dependabot | Python, Actions, Docker y Terraform |

## Estado incremental

| Incremento | Estado real | Resultado/pending |
|---|---|---|
| Fase 0 — Seguridad | 🟡 85 % | Código completo; falta evidencia dev/prod, IAM efectivo y rotaciones reales |
| Fase 1 — CI y pruebas | ✅ | CI, Docker, Sonar, Dependabot, 508 pruebas, cobertura >90 % |
| I0 — Descubrimiento | 🟡 | OpenAPI ServiceTonic confirmado; faltan credenciales/catálogos, GCP y Entra ID |
| I1 — Puertos | 🟡 | Protocolos/fábrica listos; quedan referencias `self.snow` y contrato legado |
| I2 — Vertex AI | 🟡 | Proveedor y tokens listos; falta evaluación real con Gemini |
| I3 — Cloud Run | 🟡 | Terraform/WIF/workflow listos; sin infraestructura aplicada |
| I4 — Firestore/Logging | 🟡 | Código e IaC listos; falta validación multiinstancia y sinks reales |
| I5 — ServiceTonic tickets | 🟡 | API viable; faltan `idProject`, agente técnico, campos y adaptador |
| I6 — KB/Graph/autoservicio | 🔴 | No iniciado; depende de I5 y decisiones de integración |
| I7 — Teams | 🟡 | Bot, tarjetas y callbacks listos; falta tenant y prueba real |
| I8 — Producción | ⚪ | Hardening, carga, piloto, corte y limpieza pendientes |

## Capacidades desarrolladas

- Orquestación multiagente y clasificación de intenciones.
- Contrato de ticketing y demo local; ServiceTonic productivo pendiente.
- Aprobaciones persistibles e idempotentes.
- Escalación automática con resumen ejecutivo.
- API REST, streaming y endpoint OpenAI-compatible.
- API keys, RBAC, CORS, rate limiting, guardrails y auditoría.
- Redacción recursiva de PII y secretos.
- Telemetría, métricas de cuatro dimensiones y dashboard.
- Docker, CI, análisis estático, seguridad y cobertura.
- Vertex AI con credenciales ADC y renovación de tokens.
- Firestore, Cloud Logging, BigQuery, WIF y Cloud Run definidos en Terraform.
- Teams Workflows/Azure Bot y Adaptive Cards.
- Workflows de auditoría GCP y rotación de secretos.

## Riesgos abiertos

1. Las acciones LIVE de autoservicio no deben habilitarse hasta contar con un
   ejecutor real y confirmación registrada en ServiceTonic.
2. El contrato OpenAPI está validado, pero faltan campos/catálogos específicos de Valtre.
3. No se han ejecutado evaluaciones comparativas reales con Vertex AI.
4. No existen aún proyectos GCP, datos de Cloud Logging ni BigQuery reales.
5. El rate limit es por instancia, no global.
6. Recordatorios/escalado automático de aprobaciones expiradas siguen
   pendientes.

## Siguiente camino crítico

1. Crear proyecto GCP dev, facturación, bucket de estado y WIF.
2. Cargar API keys iniciales y aplicar Terraform dev.
3. Desplegar Cloud Run y ejecutar auditoría/canarios.
4. Validar Vertex AI, Firestore, Logging y BigQuery.
5. Configurar Entra ID/Teams y ejecutar aprobación real.
6. Obtener API/sandbox de ServiceTonic e implementar I5–I6.
7. Ejecutar I8 y piloto de producción.

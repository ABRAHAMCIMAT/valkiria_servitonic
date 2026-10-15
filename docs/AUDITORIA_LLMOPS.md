# Auditoría LLMOps vigente

> Corte: 14 de octubre de 2026. Arquitectura objetivo: ServiceTonic + Microsoft
> Teams + stack administrado de Google Cloud.

## Resumen

El repositorio tiene una base sólida de aplicación, seguridad, pruebas,
observabilidad e infraestructura como código. La madurez del código se estima
en **75/100**; la madurez operativa es menor porque todavía no existen los
proyectos GCP ni las credenciales externas.

| Componente | Estado | Evidencia/pending |
|---|---|---|
| Seguridad | 🟡 Alto | RBAC, CORS, rate limit, auditoría y redacción listos; falta evidencia cloud |
| Calidad | ✅ Alto | 527 pruebas, 91.16 %, Ruff, Mypy, Sonar y Dependabot |
| Despliegue | 🟡 Medio | Docker/Terraform/WIF listos; GCP sin materializar |
| Observabilidad | 🟡 Medio-alto | Telemetría/dashboard listos; sinks y alertas sin validar |
| Gestión de modelos | 🟡 Medio | Vertex implementado; evaluación real pendiente |
| Datos/RAG | 🔴 Bajo | Falta KB real de ServiceTonic y búsqueda productiva |
| Integraciones | 🔴 Bajo | ServiceTonic y tenant Teams sin credenciales reales |

## Hallazgos cerrados

- Autenticación y roles en todos los endpoints sensibles.
- CORS explícito y fail-fast en producción.
- Redacción recursiva de PII y secretos.
- Auditoría estructurada.
- Docker y CI reproducibles.
- Cobertura superior a 90 %.
- Reintentos y errores tipados.
- WIF sin llaves JSON.
- Rotación y auditoría GCP automatizadas.

## Hallazgos abiertos

1. Implementar y probar el adaptador ServiceTonic con API real.
2. Validar KB, contactos, manager, catálogos, estados, SLA y webhooks.
3. Crear proyectos GCP y aplicar Terraform.
4. Ejecutar evaluaciones de Gemini contra línea base.
5. Validar Firestore multiinstancia, Logging, BigQuery y alertas.
6. Registrar Azure Bot e instalar la app de Teams.
7. Automatizar recordatorios y escalación de aprobaciones expiradas.
8. Implementar rate limit global.
9. Ejecutar carga, piloto, hardening y rollback productivo.

## Riesgos prioritarios

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Campos/catálogos Valtre sin confirmar | Alto | Agente técnico, inventario y pruebas contractuales de OpenAPI v1 |
| Acciones de autoservicio sin ejecutor real | Alto | Convertir en ticket hasta confirmar ejecución |
| PII en proveedores externos | Alto | Minimización, saneamiento, IAM y residencia de datos |
| Tenant Teams no autorizado | Alto | Aprobación administrativa y plan de instalación |
| Costos/cuotas Vertex | Medio | Presupuesto, alertas y evaluación costo/calidad |
| Estado cloud no probado | Alto | Dev antes de prod y workflow de evidencia |

## Próxima revisión

Repetir la auditoría después de desplegar dev y adjuntar evidencia de smoke
tests, canarios, IAM, claves de servicio, rotaciones y aprobaciones Teams.

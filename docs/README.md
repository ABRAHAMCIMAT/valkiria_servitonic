# Documentación de Valkiria ServiceTonic

> Estado consolidado al **14 de octubre de 2026**. Rama operativa: `main`.

Este directorio es la fuente de verdad documental del proyecto. Los planes
detallados conservan decisiones y criterios originales; el estado vigente se
consulta primero en [ESTADO_DESARROLLO.md](ESTADO_DESARROLLO.md).

## Lectura recomendada

1. [Estado del desarrollo](ESTADO_DESARROLLO.md)
2. [Arquitectura](ARQUITECTURA.md) y [modelo C4](c4/00_INDICE.md)
3. [Calidad](CALIDAD.md) y [pruebas](TESTING.md)
4. [Seguridad](SEGURIDAD.md) y [modelo de amenazas](MODELO_AMENAZAS.md)
5. [Despliegue local](DESPLIEGUE.md) o [despliegue GCP](DESPLIEGUE_GCP.md)
6. [Plan incremental GCP/ServiceTonic/Teams](PLAN_FASE2_GOOGLE_CLOUD.md)

## Estado por área

| Área | Estado | Documento |
|---|---|---|
| Seguridad de aplicación | Código completo; evidencia cloud pendiente | [PLAN_FASE0_SEGURIDAD.md](PLAN_FASE0_SEGURIDAD.md) |
| CI, pruebas y calidad | Completo; 508 pruebas y 91.19 % de cobertura | [CALIDAD.md](CALIDAD.md) |
| SonarCloud y Dependabot | Configurados en CI | [CALIDAD.md](CALIDAD.md) |
| Google Cloud | IaC y workflows listos; proyectos aún no creados | [DESPLIEGUE_GCP.md](DESPLIEGUE_GCP.md) |
| Vertex AI | Código listo; evaluación real pendiente | [PLAN_FASE2_GOOGLE_CLOUD.md](PLAN_FASE2_GOOGLE_CLOUD.md) |
| Firestore/Logging/BigQuery | Código e IaC listos; sin aplicar | [DESPLIEGUE_GCP.md](DESPLIEGUE_GCP.md) |
| Microsoft Teams | Código listo; tenant/bot no configurados | [integraciones/TEAMS.md](integraciones/TEAMS.md) |
| ServiceTonic | OpenAPI/servidor confirmados; faltan credenciales, `idProject` y catálogos | [integraciones/SERVICETONIC_API.md](integraciones/SERVICETONIC_API.md) |
| Producción | No iniciada | [PLAN_FASE2_GOOGLE_CLOUD.md](PLAN_FASE2_GOOGLE_CLOUD.md) |

## Convención de estados

- ✅ Completo y validado.
- 🟡 Código listo o parcial; falta validación externa.
- 🔴 Bloqueado por dependencia externa.
- ⚪ No iniciado.

## Documentos históricos

`AUDITORIA_LLMOPS.md`, `PLAN_FASE0_SEGURIDAD.md` y
`PLAN_FASE1_CICD_TESTING.md` contienen la línea base y el razonamiento que dio
origen a las implementaciones. Sus cifras originales no deben interpretarse
como el estado actual sin leer el bloque de actualización al inicio.

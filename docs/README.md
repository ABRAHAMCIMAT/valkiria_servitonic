# Documentación de Valkiria ServiceTonic

> Estado consolidado al **15 de octubre de 2026**. Rama operativa: `main`.

Este directorio es la fuente de verdad documental del proyecto. Los planes
detallados conservan decisiones y criterios originales; el estado vigente se
consulta primero en [ESTADO_DESARROLLO.md](ESTADO_DESARROLLO.md).

## Alcance vigente

El objetivo inmediato es un **PoC desplegado localmente** con dos integraciones:

1. ServiceTonic para tickets.
2. Microsoft Teams para aprobaciones.

Ver [POC_LOCAL.md](POC_LOCAL.md). El stack Google Cloud queda como roadmap
posterior y no forma parte de los criterios de aceptación del PoC.

## Lectura recomendada

1. [PoC local](POC_LOCAL.md)
2. [Estado del desarrollo](ESTADO_DESARROLLO.md)
3. [Arquitectura](ARQUITECTURA.md) y [modelo C4](c4/00_INDICE.md)
4. [Calidad](CALIDAD.md) y [pruebas](TESTING.md)
5. [Seguridad](SEGURIDAD.md) y [modelo de amenazas](MODELO_AMENAZAS.md)
6. [Despliegue local](DESPLIEGUE.md)

## Estado por área

| Área | Estado | Documento |
|---|---|---|
| Seguridad de aplicación | Código completo; evidencia local PoC pendiente | [PLAN_FASE0_SEGURIDAD.md](PLAN_FASE0_SEGURIDAD.md) |
| CI, pruebas y calidad | Completo; 527 pruebas y 91.16 % de cobertura | [CALIDAD.md](CALIDAD.md) |
| SonarCloud y Dependabot | Configurados en CI | [CALIDAD.md](CALIDAD.md) |
| PoC local | Configuración Docker lista; credenciales y prueba E2E pendientes | [POC_LOCAL.md](POC_LOCAL.md) |
| Google Cloud | Diferido fuera del PoC | [DESPLIEGUE_GCP.md](DESPLIEGUE_GCP.md) |
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

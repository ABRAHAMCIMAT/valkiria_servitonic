# Calidad de software

> Estado 15/10/2026: ✅ puerta local validada con 515 pruebas y 91.19 % de
> cobertura. SonarCloud está integrado al workflow; su Quality Gate se
> administra en la organización externa.

## Puertas automáticas

Cada cambio en `main` o pull request debe superar:

1. Ruff lint y formato.
2. Mypy.
3. Pytest en Python 3.11 y 3.12.
4. Cobertura total estrictamente superior a **90 %**.
5. Bandit sin hallazgos medios/altos y `pip-audit` sin vulnerabilidades.
6. SonarCloud Quality Gate.
7. Build, tamaño, usuario no-root y smoke test de Docker.

## Configuración inicial de SonarCloud

1. Importar `ABRAHAMCIMAT/valkiria_servitonic` en la organización
   `abrahamcimat` de SonarCloud.
2. Desactivar *Automatic Analysis*; el análisis lo ejecuta GitHub Actions.
3. Crear un token de análisis y guardarlo en GitHub como secreto
   `SONAR_TOKEN`.
   Guardarlo también como *Dependabot secret* con el mismo nombre para que los
   pull requests de actualización puedan ejecutar el Quality Gate.
4. Crear o asignar un Quality Gate con estas condiciones sobre **código nuevo**:

| Métrica | Condición |
|---|---|
| Coverage | mayor que 90 % |
| Duplicated Lines | menor que 3 % |
| Reliability Rating | A |
| Security Rating | A |
| Maintainability Rating | A |
| Security Hotspots Reviewed | 100 % |

El repositorio analiza `backend/` y `scripts/`. Los scripts CLI se analizan
para bugs, vulnerabilidades y mantenibilidad, pero se excluyen de cobertura
porque no forman parte del runtime importable. Las pruebas se excluyen de la
detección de duplicación.

La cobertura global también está protegida localmente por `coverage.py`; Sonar
evita que código nuevo reduzca la calidad aunque la media histórica permanezca
alta.

### Solución de `Falta el secreto SONAR_TOKEN`

- Debe existir exactamente como `SONAR_TOKEN` en **Settings → Secrets and
  variables → Actions → Repository secrets**; una variable o un secreto de
  environment no es visible para el job actual.
- Los secretos se cargan al iniciar el job. Si se creó después de un fallo,
  hay que ejecutar **Re-run failed jobs** o provocar una nueva ejecución.
- GitHub no entrega secretos a pull requests procedentes de forks. El análisis
  de PR requiere que la rama pertenezca a este mismo repositorio.
- El valor debe ser un token vigente generado en **SonarCloud → My Account →
  Security**, con permiso de análisis sobre el proyecto.
- Mientras el token no esté disponible, el job se omite con advertencia para
  no bloquear CI. Después de validar el primer análisis, crear la variable de
  repositorio `SONAR_REQUIRED=true`; desde ese momento un token ausente vuelve
  a bloquear `main` y los PR.

Para considerar Sonar completamente configurado deben existir simultáneamente:

```text
Repository secret:   SONAR_TOKEN=<token vigente>
Repository variable: SONAR_REQUIRED=true
```

Además, el proyecto de SonarCloud debe estar vinculado al repositorio privado
y tener **Automatic Analysis desactivado**.

## Dependabot

Dependabot revisa semanalmente Python, GitHub Actions, Docker y proveedores de
Terraform. Las actualizaciones minor/patch compatibles se agrupan para reducir
ruido; cada PR debe pasar todas las puertas antes de fusionarse.

## Branch protection recomendada

Marcar como requerido únicamente `Estado CI`, que ya agrega lint, tipos,
pruebas, seguridad, Sonar y Docker. Puede requerirse además el check externo
de SonarCloud si la vinculación del proyecto lo publica de forma estable.

No marcar como requeridos los workflows manuales:

- `ServiceTonic solo lectura` (`servicetonic-test`).
- `Verificar seguridad GCP` (`dev`/`prod`).
- `Rotar secretos GCP`.

Esos jobs usan environments con aprobación y, si se convierten en checks de
branch protection, dejarán los PR en estado pendiente indefinidamente.

## Comandos locales

```bash
make lint
make typecheck
make cov
make security
```

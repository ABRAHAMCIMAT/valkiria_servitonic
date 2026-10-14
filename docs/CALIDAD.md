# Calidad de software

> Estado 14/10/2026: ✅ puerta local validada con 508 pruebas y 91.19 % de
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

La cobertura global también está protegida localmente por `coverage.py`; Sonar
evita que código nuevo reduzca la calidad aunque la media histórica permanezca
alta.

## Dependabot

Dependabot revisa semanalmente Python, GitHub Actions, Docker y proveedores de
Terraform. Las actualizaciones minor/patch compatibles se agrupan para reducir
ruido; cada PR debe pasar todas las puertas antes de fusionarse.

## Comandos locales

```bash
make lint
make typecheck
make cov
make security
```

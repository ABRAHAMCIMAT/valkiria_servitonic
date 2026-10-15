# Fase 1 — Contenedores, CI/CD y calidad

> Estado: ✅ completada.

## Resultado

- Docker multi-stage y usuario no-root.
- Docker Compose para desarrollo.
- GitHub Actions en Python 3.11/3.12.
- 527 pruebas unitarias, integración y E2E.
- Cobertura 91.16 %, umbral estricto >90 %.
- Ruff, Mypy, Bandit y `pip-audit`.
- SonarCloud Quality Gate.
- Dependabot para Python, Actions, Docker y Terraform.
- Smoke test de imagen y API.

## Puertas obligatorias

1. Lint y formato.
2. Tipos estáticos.
3. Suite completa y cobertura.
4. Seguridad de código/dependencias.
5. SonarCloud.
6. Build y smoke test Docker.

Ver [CALIDAD.md](CALIDAD.md) y [TESTING.md](TESTING.md).

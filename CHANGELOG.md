# Changelog

Formato [Keep a Changelog](https://keepachangelog.com/es/1.1.0/) y
[SemVer](https://semver.org/lang/es/).

## [1.0.0] - 2026-11-11

Primera versión lista para desplegar y mantener.

### Añadido

- CI completo: lint, mypy strict, tests 3.12/3.13 con cobertura, `pip-audit` y
  publicación de las imágenes web y worker en GHCR.
- Healthcheck del contenedor web contra `/health`.
- Dependabot (pip, actions, Docker), plantillas de issue y checklist de PR.
- Documentación: configuración, despliegue, troubleshooting, seguridad y
  contribución.
- Tests del worker RQ con Redis mockeado (cobertura 46 % → 92 %).

### Cambiado

- Web y worker corren como **uid 10001**, con `init: true` y
  `no-new-privileges`.
- `.dockerignore` excluye `.git`, tests, datos y cachés del contexto de build.
- Compose referencia las imágenes publicadas y declara healthcheck del web.
- Cobertura global 82 % (gate 75 %).

### Corregido

- El CI instalaba contra el Python del runner (PEP 668) y no escuchaba `dev`:
  no se ejecutaba o fallaba antes de los tests.
- El job de Docker usaba `targets: web,worker`, que no es una entrada válida de
  `build-push-action`; ahora se construyen ambas imágenes.
- El `.env.example` documentaba `LLAMA_WEB_TOKEN`, pero el código solo leía
  `WEB_TOKEN`: quien seguía la plantilla dejaba la web sin login. Se aceptan
  ambos alias.

### Seguridad

- `pip-audit` limpio sobre las dependencias de ejecución.
- Contenedores sin root y `no-new-privileges`.
- Política de reporte y rotación de secretos en `SECURITY.md`.

## [0.2.0] - 2026-10-12

- Gestión de modelos GGUF, perfiles y descubrimiento de binarios.
- Arranque/parada de `llama-server` desde la web con logs y métricas.
- Descargas en background con Redis/RQ.
- Playground y generación de comandos `curl`.

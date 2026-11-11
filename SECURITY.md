# Política de seguridad

## Versiones soportadas

| Versión | Soporte |
|---|---|
| 1.x | Sí |
| < 1.0 | No |

## Cómo reportar

Usa **GitHub Security Advisories** o un issue privado. Incluye versión/commit,
componente, pasos de reproducción e impacto. No adjuntes tokens reales.

Respuesta objetivo: acuse en 72 h y parche/mitigación en 14 días.

## Alcance

- bypass de `WEB_TOKEN` / sesión;
- exposición no autorizada de la API o de la UI;
- ejecución arbitraria a través de rutas de binarios o modelos;
- lectura de `data/app.db`, `runtime_settings.json` o logs por terceros;
- SSRF vía URL de descarga de modelos;
- dependencias con CVE en ejecución.

Fuera de alcance: acceso físico, seguridad de `llama-server`/Redis upstream sin
vector propio, y despliegues que exponen la web a internet sin token ni proxy.

## Recomendaciones

- Define `WEB_TOKEN` si la web sale de `127.0.0.1`.
- No expongas Redis (6379) ni la web a internet; usa VPN o reverse proxy con TLS.
- Ejecuta los contenedores sin root (uid 10001) y con `no-new-privileges`.
- Rota `WEB_TOKEN` y `HUGGING_FACE_TOKEN` si se filtraron.
- Mantén dependencias al día: Dependabot + `pip-audit` en CI.

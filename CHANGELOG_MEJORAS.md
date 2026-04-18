# Mejoras aplicadas

## Enfoque actual

El proyecto quedó orientado a Linux nativo y operación persistente con `systemd`.

## Cambios principales

- Se eliminó el enfoque principal en Docker de la documentación.
- Se separó bootstrap de arranque estable para producción.
- Se agregaron scripts nativos:
  - `scripts/bootstrap_native_linux.sh`
  - `scripts/start_web.sh`
  - `scripts/start_worker.sh`
  - `scripts/install_systemd.sh`
- Se agregaron plantillas de servicios `systemd`.
- `run_local_web.sh` y `run_local_worker.sh` ahora delegan a los scripts nativos estables.
- Se dejó claro que la UI gestiona `llama-server`, mientras `systemd` mantiene viva la web y el worker.

## Resultado práctico

Ahora el flujo queda así:

1. El host Linux levanta la UI con systemd.
2. Desde la web eliges binario y modelo.
3. La web inicia `llama-server`.
4. El endpoint queda consumible por otra máquina de la LAN.

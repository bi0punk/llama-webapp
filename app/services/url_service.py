from __future__ import annotations

from app.runtime_settings import RuntimeSettings
from app.system_info import default_public_host


def loopback_base_url(settings: RuntimeSettings) -> str:
    return f"http://127.0.0.1:{settings.server_port}"


def advertised_base_url(settings: RuntimeSettings) -> str:
    host = settings.public_host or default_public_host()
    port = settings.public_port or settings.server_port
    return f"http://{host}:{port}"

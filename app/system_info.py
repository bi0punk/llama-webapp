from __future__ import annotations

import os
import socket
from typing import Any


def cpu_count() -> int:
    return max(1, os.cpu_count() or 1)


def _socket_ip() -> str | None:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        return None
    return None


def local_ip_candidates() -> list[str]:
    results: list[str] = []
    preferred = _socket_ip()
    if preferred:
        results.append(preferred)

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, family=socket.AF_INET):
            ip = info[4][0]
            if ip and not ip.startswith("127.") and ip not in results:
                results.append(ip)
    except Exception:
        pass

    return results


def default_public_host() -> str:
    candidates = local_ip_candidates()
    return candidates[0] if candidates else "127.0.0.1"


def system_snapshot() -> dict[str, Any]:
    return {
        "cpu_count": cpu_count(),
        "hostname": socket.gethostname(),
        "local_ip_candidates": local_ip_candidates(),
    }

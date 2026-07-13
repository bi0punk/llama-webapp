from __future__ import annotations

# ---------------------------------------------------------------------------
# DEPRECATED — this module is kept for backward compatibility.
# All consumers should import directly from the new service/repository modules.
# ---------------------------------------------------------------------------
from app.queue import queue, redis_conn  # noqa: F401
from app.repositories.job_repo import get_jobs  # noqa: F401
from app.repositories.model_repo import get_models_page, serialize_model  # noqa: F401
from app.repositories.registry_repo import load_registry  # noqa: F401
from app.runtime_settings import load_runtime_settings  # noqa: F401
from app.services.curl_service import build_curl_examples  # noqa: F401
from app.services.model_service import enqueue_download, import_local_models  # noqa: F401
from app.services.profile_service import get_model_profile, precompute_profiles  # noqa: F401
from app.services.url_service import advertised_base_url, loopback_base_url  # noqa: F401
from app.templates import templates  # noqa: F401

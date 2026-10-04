"""Health checks used by Docker, the ECS load balancer and the demo."""

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import get_engine
from app.core.kv import get_kv
from app.core.storage import get_storage

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/health/dependencies")
def dependencies() -> dict:
    """Report reachability of each dependency. Never includes hosts or credentials."""
    settings = get_settings()
    checks: dict[str, dict] = {}

    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = {"ok": True, "backend": get_engine().dialect.name}
    except Exception:
        checks["database"] = {"ok": False, "backend": get_engine().dialect.name}

    kv = get_kv()
    checks["cache"] = {"ok": kv.ping(), "backend": "redis" if settings.redis_url else "memory"}

    storage = get_storage()
    checks["storage"] = {"ok": storage.ping(), "backend": storage.name}

    from app.providers.registry import provider_status

    checks["ai"] = provider_status()

    overall = all(c.get("ok", True) for c in (checks["database"], checks["cache"], checks["storage"]))
    return {"status": "ok" if overall else "degraded", "checks": checks}

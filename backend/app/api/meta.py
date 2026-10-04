"""Public client configuration and demo-mode helpers."""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.deps import current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.models import User
from app.providers.registry import provider_status
from app.schemas.requests import DemoReset

router = APIRouter(tags=["meta"])


@router.get("/config")
def client_config() -> dict:
    s = get_settings()
    return {
        "app_name": s.app_name,
        "currency": s.currency,
        "locale": s.locale,
        "timezone": s.timezone,
        "languages": s.extraction_language_list,
        "demo_mode": s.demo_mode,
        "confidence": {"high": s.confidence_high, "review": s.confidence_review},
        "providers": provider_status(),
        "limits": {"photo_mb": s.max_photo_bytes // (1024 * 1024), "voice_mb": s.max_voice_bytes // (1024 * 1024)},
    }


def _manifest() -> list[dict]:
    path = Path(get_settings().samples_dir) / "manifest.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))["samples"]


def _require_demo() -> None:
    if not get_settings().demo_mode:
        raise HTTPException(404, "Not found")


@router.get("/demo/samples")
def demo_samples() -> list[dict]:
    _require_demo()
    return [{k: v for k, v in s.items() if k != "file"} for s in _manifest()]


@router.get("/demo/samples/{sample_id}/file")
def demo_sample_file(sample_id: str):
    _require_demo()
    sample = next((s for s in _manifest() if s["id"] == sample_id), None)
    if sample is None:
        raise HTTPException(404, "Sample not found.")
    root = Path(get_settings().samples_dir).resolve()
    path = (root / sample["file"]).resolve()
    if root not in path.parents or not path.exists():
        raise HTTPException(404, "Sample not found.")
    return FileResponse(path, media_type=sample["mime_type"], filename=path.name)


@router.post("/demo/reset")
def demo_reset(body: DemoReset, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    _require_demo()
    if not user.is_demo:
        raise HTTPException(403, "Only the demo account can be reset.")
    from app.demo.seed import reset_demo_user

    return reset_demo_user(db, user, with_history=body.with_history)

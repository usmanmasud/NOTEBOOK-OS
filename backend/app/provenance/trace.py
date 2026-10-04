"""Provenance: answers "where did this number come from?" for every record."""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.analytics.metrics import Rec
from app.core.config import get_settings
from app.models import Record, RecordStatus
from app.validation.rules import confidence_level


def _num(value):
    return float(value) if value is not None else None


def provenance(record: Record) -> dict:
    upload = record.upload
    page = record.source_page
    bbox = None
    if record.bbox_x is not None:
        bbox = {"x": record.bbox_x, "y": record.bbox_y, "width": record.bbox_width, "height": record.bbox_height}
    return {
        "upload_id": record.upload_id,
        "upload_type": upload.type.value if upload else None,
        "uploaded_at": upload.created_at.isoformat() if upload else None,
        "original_filename": upload.original_filename if upload else None,
        "page_id": page.id if page else None,
        "page_number": page.page_number if page else None,
        "reference": record.source_reference,
        "original_text": record.original_text,
        "bbox": bbox,
        "has_image": bool(page and page.image_url),
        "read_by": (upload.pipeline_info or {}).get("read_provider") if upload else None,
        "read_is_demo_fixture": (upload.pipeline_info or {}).get("read_is_demo_fixture", False) if upload else False,
        "interpreted_by": (upload.pipeline_info or {}).get("interpreter") if upload else None,
    }


def record_out(record: Record) -> dict:
    from app.services.records import human_fields

    settings = get_settings()
    return {
        "id": record.id,
        "upload_id": record.upload_id,
        "date": record.date.isoformat() if record.date else None,
        "type": record.type.value if record.type else None,
        "item": record.item,
        "quantity": _num(record.quantity),
        "amount": _num(record.amount),
        "person": record.person,
        "notes": record.notes,
        "confidence": round(record.confidence, 2),
        "confidence_level": confidence_level(record.confidence, settings),
        "field_confidence": record.field_confidence or {},
        "validation_issues": record.validation_issues or [],
        "human_fields": sorted(human_fields(record)) if record.ai_original is not None else [],
        "manual_entry": record.ai_original is None,
        "ai_original": record.ai_original,
        "edited": record.edited,
        "status": record.status.value,
        "confirmed_at": record.confirmed_at.isoformat() if record.confirmed_at else None,
        "source": provenance(record),
    }


def confirmed_records(db: Session, user_id: str) -> list[Record]:
    """The only records that count as official business data."""
    stmt = (
        select(Record)
        .options(joinedload(Record.upload), joinedload(Record.source_page))
        .where(Record.user_id == user_id, Record.status == RecordStatus.CONFIRMED)
        .order_by(Record.date.desc(), Record.created_at.desc())
    )
    return list(db.scalars(stmt).unique())


def to_rec(record: Record) -> Rec:
    return Rec(
        id=record.id,
        type=record.type.value if record.type else "OTHER",
        amount=record.amount,
        date=record.date,
        person=record.person,
        item=record.item,
        quantity=record.quantity,
    )

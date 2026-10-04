"""Human-in-the-loop operations: edit, confirm, reject and manual entry.

Only an explicit human action can set a record to CONFIRMED.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import log_event
from app.extraction.normalize import parse_iso_date
from app.extraction.types import FIELDS
from app.models import Person, Record, RecordStatus, RecordType, Upload, UploadStatus, utcnow
from app.validation.rules import has_errors, needs_review, validate_record


class RecordValidationError(Exception):
    def __init__(self, message: str, records: list[dict]) -> None:
        super().__init__(message)
        self.message = message
        self.records = records


def record_fields(record: Record) -> dict:
    return {
        "date": record.date,
        "type": record.type.value if record.type else None,
        "item": record.item,
        "quantity": record.quantity,
        "amount": record.amount,
        "person": record.person,
        "notes": record.notes,
    }


def _as_comparable(field: str, value):
    if value is None:
        return None
    if field in ("amount", "quantity"):
        return Decimal(str(value)).normalize()
    if field == "date":
        return parse_iso_date(value)
    return str(value)


def human_fields(record: Record) -> set[str]:
    """Fields whose value now differs from what the AI proposed (all fields for manual entries)."""
    if record.ai_original is None:
        return set(FIELDS)
    current = record_fields(record)
    return {
        f for f in FIELDS
        if _as_comparable(f, current[f]) != _as_comparable(f, record.ai_original.get(f))
    }


def revalidate(record: Record) -> None:
    settings = get_settings()
    edited = human_fields(record)
    record.edited = record.ai_original is not None and bool(edited)
    record.validation_issues = validate_record(
        record_fields(record),
        record.field_confidence or {},
        record.confidence,
        record.original_text,
        edited,
        settings,
        date.today(),
    )
    review = needs_review(record.validation_issues, record.confidence, settings) and not (
        record.ai_original is None and not record.validation_issues
    )
    record.status = RecordStatus.NEEDS_REVIEW if review else RecordStatus.AI_EXTRACTED


def apply_changes(record: Record, changes: dict) -> None:
    for field, value in changes.items():
        if field == "type":
            record.type = RecordType(value) if value else None
        elif field in ("amount", "quantity"):
            setattr(record, field, Decimal(str(value)) if value is not None else None)
        elif field in ("item", "person", "notes"):
            value = (value or "").strip() or None
            setattr(record, field, value)
        elif field == "date":
            record.date = value


def update_record(db: Session, record: Record, changes: dict) -> Record:
    was_confirmed = record.status == RecordStatus.CONFIRMED
    apply_changes(record, changes)
    revalidate(record)  # a corrected record must be confirmed again
    record.confirmed_at = None
    if was_confirmed and record.upload.status == UploadStatus.CONFIRMED:
        record.upload.status = UploadStatus.REVIEW
    db.commit()
    log_event("record_edited", record_id=record.id, fields=sorted(changes), was_confirmed=was_confirmed)
    return record


def _upsert_person(db: Session, user_id: str, name: str | None) -> str | None:
    if not name:
        return None
    normalized = " ".join(name.lower().split())
    person = db.scalar(select(Person).where(Person.user_id == user_id, Person.normalized_name == normalized))
    if person is None:
        person = Person(user_id=user_id, name=name.strip(), normalized_name=normalized)
        db.add(person)
        db.flush()
    return person.id


def _error_summary(record: Record) -> dict:
    return {
        "id": record.id,
        "source_reference": record.source_reference,
        "issues": [i for i in record.validation_issues or [] if i["severity"] == "error"],
    }


def confirm_record(db: Session, record: Record) -> Record:
    revalidate(record)
    if has_errors(record.validation_issues):
        db.commit()
        raise RecordValidationError("Fix the highlighted fields before confirming.", [_error_summary(record)])
    _mark_confirmed(db, record)
    _refresh_upload_status(record.upload)
    db.commit()
    log_event("human_confirmation", record_id=record.id, upload_id=record.upload_id, count=1)
    return record


def _mark_confirmed(db: Session, record: Record) -> None:
    record.status = RecordStatus.CONFIRMED
    record.confirmed_at = utcnow()
    record.person_id = _upsert_person(db, record.user_id, record.person)


def reject_record(db: Session, record: Record) -> Record:
    record.status = RecordStatus.REJECTED
    record.confirmed_at = None
    _refresh_upload_status(record.upload)
    db.commit()
    log_event("record_rejected", record_id=record.id)
    return record


def confirm_upload(db: Session, upload: Upload, record_ids: list[str] | None = None) -> list[Record]:
    if upload.status not in (UploadStatus.REVIEW, UploadStatus.CONFIRMED, UploadStatus.FAILED):
        raise RecordValidationError("This upload is still being processed.", [])
    targets = [
        r for r in upload.records
        if r.status != RecordStatus.REJECTED and (record_ids is None or r.id in record_ids)
    ]
    if record_ids is not None and len(targets) != len(set(record_ids)):
        raise RecordValidationError("Some records were not found in this upload.", [])
    for r in targets:
        if r.status != RecordStatus.CONFIRMED:
            revalidate(r)
    blocked = [r for r in targets if r.status != RecordStatus.CONFIRMED and has_errors(r.validation_issues)]
    if blocked:
        db.commit()
        raise RecordValidationError(
            f"{len(blocked)} record(s) need fixing before confirming.", [_error_summary(r) for r in blocked]
        )
    for r in targets:
        if r.status != RecordStatus.CONFIRMED:
            _mark_confirmed(db, r)
    _refresh_upload_status(upload)
    db.commit()
    log_event("human_confirmation", upload_id=upload.id, count=len(targets))
    return targets


def _refresh_upload_status(upload: Upload) -> None:
    active = [r for r in upload.records if r.status != RecordStatus.REJECTED]
    if active and all(r.status == RecordStatus.CONFIRMED for r in active):
        upload.status = UploadStatus.CONFIRMED
    elif upload.status == UploadStatus.CONFIRMED:
        upload.status = UploadStatus.REVIEW


def add_manual_record(db: Session, upload: Upload, values: dict) -> Record:
    """Typed entry by the trader, e.g. when automatic reading is unavailable."""
    record = Record(
        user_id=upload.user_id,
        upload_id=upload.id,
        source_page_id=upload.pages[0].id if upload.pages else None,
        confidence=1.0,
        field_confidence={},
        ai_original=None,
        source_reference="manual-entry",
        original_text=None,
    )
    apply_changes(record, values)
    db.add(record)
    record.upload = upload
    revalidate(record)
    if upload.status == UploadStatus.FAILED:
        upload.status = UploadStatus.REVIEW
    elif upload.status == UploadStatus.CONFIRMED:
        upload.status = UploadStatus.REVIEW
    db.commit()
    log_event("manual_record_added", upload_id=upload.id, record_id=record.id)
    return record

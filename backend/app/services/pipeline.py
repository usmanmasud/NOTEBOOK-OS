"""Runs an upload through READ -> UNDERSTAND -> VALIDATE.

Runs as a background task: the upload request returns immediately with status
PROCESSING and the client polls `GET /api/uploads/{id}` until REVIEW or FAILED.
The SUMMARIZE stage (metrics) is separate and only ever reads CONFIRMED records.
"""

import logging
from datetime import date

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import session_factory
from app.core.logging import log_event
from app.core.storage import get_storage
from app.extraction.interpret import interpret
from app.extraction.types import SourceLine
from app.models import Record, RecordStatus, RecordType, SourcePage, Upload, UploadStatus, UploadType, utcnow
from app.providers import registry
from app.providers.base import ProviderUnavailable, ReadPage, ReadResult, TextLine
from app.validation.rules import check_written_totals, needs_review, validate_record

logger = logging.getLogger(__name__)

GENERIC_FAILURE = "Processing failed. You can retry, or enter the transactions manually."


def _read(upload: Upload) -> ReadResult:
    if upload.type == UploadType.TEXT:
        rows = [r for r in (upload.raw_text or "").splitlines() if r.strip()]
        lines = [TextLine(index=i, text=t.strip(), confidence=1.0) for i, t in enumerate(rows)]
        return ReadResult(pages=[ReadPage(page_number=1, lines=lines)], provider="typed")
    data = get_storage().get(upload.file_url or "")
    if upload.type == UploadType.PHOTO:
        return registry.read_image(data, upload.mime_type or "")
    return registry.transcribe(data, upload.mime_type or "")


def run_pipeline(db: Session, upload: Upload) -> None:
    settings = get_settings()
    upload.status = UploadStatus.PROCESSING
    upload.error_message = None
    db.commit()
    log_event("processing_started", upload_id=upload.id, type=upload.type.value)

    # ---- READ ------------------------------------------------------------------
    read = _read(upload)
    log_event(
        "ocr_completed" if upload.type == UploadType.PHOTO else "read_completed",
        upload_id=upload.id,
        provider=read.provider,
        fixture=read.is_fixture,
        lines=sum(len(p.lines) for p in read.pages),
    )
    if upload.type != UploadType.TEXT:
        upload.raw_text = read.text

    pages: dict[int, SourcePage] = {}
    source_lines: list[SourceLine] = []
    for rp in read.pages:
        page = SourcePage(
            upload_id=upload.id,
            page_number=rp.page_number,
            image_url=upload.file_url if upload.type == UploadType.PHOTO else None,
            width=rp.width,
            height=rp.height,
            lines=[
                {
                    "index": ln.index,
                    "text": ln.text,
                    "confidence": round(ln.confidence, 3),
                    "bbox": ln.bbox.to_dict() if ln.bbox else None,
                }
                for ln in rp.lines
            ],
        )
        db.add(page)
        pages[rp.page_number] = page
        source_lines += [
            SourceLine(rp.page_number, ln.index, ln.text, ln.confidence, ln.bbox.to_dict() if ln.bbox else None)
            for ln in rp.lines
        ]
    db.flush()

    # ---- UNDERSTAND --------------------------------------------------------------
    reference = (upload.created_at or utcnow()).date()
    interpretation = interpret(source_lines, reference)
    log_event(
        "ai_extraction_completed",
        upload_id=upload.id,
        interpreter=interpretation.interpreter,
        fallback=bool(interpretation.fallback_reason),
        records=len(interpretation.candidates),
    )

    # ---- VALIDATE ------------------------------------------------------------------
    today = date.today()
    by_page: dict[int, list[dict]] = {}
    flagged = 0
    for cand in interpretation.candidates:
        issues = validate_record(
            cand.fields, cand.field_confidence, cand.confidence, cand.line.text, set(), settings, today
        )
        review = needs_review(issues, cand.confidence, settings)
        flagged += review
        by_page.setdefault(cand.line.page_number, []).append(cand.fields)
        bbox = cand.line.bbox or {}
        db.add(
            Record(
                user_id=upload.user_id,
                upload_id=upload.id,
                source_page_id=pages[cand.line.page_number].id if cand.line.page_number in pages else None,
                **_columns(cand.fields),
                confidence=cand.confidence,
                field_confidence=cand.field_confidence,
                validation_issues=issues,
                ai_original=_jsonable(cand.fields),
                status=RecordStatus.NEEDS_REVIEW if review else RecordStatus.AI_EXTRACTED,
                source_reference=cand.line.reference,
                line_index=cand.line.line_index,
                original_text=cand.line.text[:500],
                bbox_x=bbox.get("x"),
                bbox_y=bbox.get("y"),
                bbox_width=bbox.get("width"),
                bbox_height=bbox.get("height"),
            )
        )

    total_checks = check_written_totals(interpretation.totals, by_page)
    upload.pipeline_info = {
        "read_provider": read.provider,
        "read_is_demo_fixture": read.is_fixture,
        "interpreter": interpretation.interpreter,
        "interpreter_fallback_reason": interpretation.fallback_reason,
        "lines_read": len(source_lines),
        "records_extracted": len(interpretation.candidates),
        "records_flagged": flagged,
        "total_checks": [c.to_dict() for c in total_checks],
    }
    upload.status = UploadStatus.REVIEW
    upload.processed_at = utcnow()
    db.commit()
    log_event("validation_completed", upload_id=upload.id, records=len(interpretation.candidates), flagged=flagged)


def _columns(fields: dict) -> dict:
    out = dict(fields)
    out["type"] = RecordType(out["type"]) if out.get("type") else None
    return out


def _jsonable(fields: dict) -> dict:
    return {k: (str(v) if v is not None and not isinstance(v, (str, int, float)) else v) for k, v in fields.items()}


def clear_extraction(db: Session, upload: Upload) -> None:
    for record in list(upload.records):
        db.delete(record)
    for page in list(upload.pages):
        db.delete(page)
    db.flush()


def process_upload(upload_id: str) -> None:
    """Background-task entry point with its own DB session. Never raises."""
    db = session_factory()()
    try:
        upload = db.get(Upload, upload_id)
        if upload is None:
            return
        try:
            run_pipeline(db, upload)
        except ProviderUnavailable as exc:
            db.rollback()
            _fail(db, upload_id, exc.user_message)
            log_event("processing_failed", upload_id=upload_id, reason=exc.detail or "provider unavailable")
        except Exception:
            db.rollback()
            logger.exception("pipeline crashed for upload %s", upload_id)
            _fail(db, upload_id, GENERIC_FAILURE)
            log_event("processing_failed", upload_id=upload_id, reason="internal error")
    finally:
        db.close()


def _fail(db: Session, upload_id: str, message: str) -> None:
    upload = db.get(Upload, upload_id)
    if upload is None:
        return
    clear_extraction(db, upload)
    upload.status = UploadStatus.FAILED
    upload.error_message = message
    upload.processed_at = utcnow()
    db.commit()

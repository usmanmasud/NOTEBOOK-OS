from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import current_user, rate_limit
from app.core.config import get_settings
from app.core.db import get_db
from app.core.storage import StorageError, get_storage
from app.models import RecordStatus, Upload, UploadStatus, UploadType, User
from app.provenance.trace import record_out
from app.schemas.requests import ConfirmUpload, RecordFields, TextUpload
from app.services import records as record_service
from app.services import uploads as upload_service
from app.services.pipeline import clear_extraction, process_upload

router = APIRouter(prefix="/uploads", tags=["uploads"])


def owned_upload(upload_id: str, user: User, db: Session) -> Upload:
    upload = db.get(Upload, upload_id)
    if upload is None or upload.user_id != user.id:
        raise HTTPException(404, "Upload not found.")
    return upload


def upload_out(upload: Upload) -> dict:
    counts = {s.value: 0 for s in RecordStatus}
    for r in upload.records:
        counts[r.status.value] += 1
    return {
        "id": upload.id,
        "type": upload.type.value,
        "status": upload.status.value,
        "original_filename": upload.original_filename,
        "mime_type": upload.mime_type,
        "has_file": bool(upload.file_url),
        "raw_text": upload.raw_text,
        "error_message": upload.error_message,
        "pipeline": upload.pipeline_info or {},
        "created_at": upload.created_at.isoformat(),
        "processed_at": upload.processed_at.isoformat() if upload.processed_at else None,
        "record_counts": counts,
        "pages": [
            {
                "id": p.id,
                "page_number": p.page_number,
                "width": p.width,
                "height": p.height,
                "has_image": bool(p.image_url),
                "lines": p.lines or [],
            }
            for p in upload.pages
        ],
    }


def _limit_uploads(user: User) -> None:
    rate_limit("uploads", get_settings().rate_limit_uploads_per_minute, 60, user.id)


def _start(upload: Upload, background: BackgroundTasks, db: Session) -> dict:
    upload.status = UploadStatus.PROCESSING
    db.commit()
    background.add_task(process_upload, upload.id)
    return upload_out(upload)


async def _read_limited(file: UploadFile, limit: int) -> bytes:
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"The file is too large (max {limit // (1024 * 1024)} MB).")
    return data


@router.post("/photo", status_code=202)
async def upload_photo(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    _limit_uploads(user)
    data = await _read_limited(file, get_settings().max_photo_bytes)
    try:
        upload = upload_service.create_file_upload(db, user, UploadType.PHOTO, data, file.filename)
    except upload_service.UploadRejected as exc:
        raise HTTPException(exc.status_code, exc.message)
    except StorageError:
        raise HTTPException(503, "We could not save your photo right now. Please try again.")
    return _start(upload, background, db)


@router.post("/voice", status_code=202)
async def upload_voice(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    _limit_uploads(user)
    data = await _read_limited(file, get_settings().max_voice_bytes)
    try:
        upload = upload_service.create_file_upload(db, user, UploadType.VOICE, data, file.filename)
    except upload_service.UploadRejected as exc:
        raise HTTPException(exc.status_code, exc.message)
    except StorageError:
        raise HTTPException(503, "We could not save your recording right now. Please try again.")
    return _start(upload, background, db)


@router.post("/text", status_code=202)
def upload_text(
    body: TextUpload, background: BackgroundTasks, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    _limit_uploads(user)
    try:
        upload = upload_service.create_text_upload(db, user, body.text)
    except upload_service.UploadRejected as exc:
        raise HTTPException(exc.status_code, exc.message)
    return _start(upload, background, db)


@router.get("")
def list_uploads(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    uploads = db.scalars(
        select(Upload).where(Upload.user_id == user.id).order_by(Upload.created_at.desc()).limit(100)
    )
    return [
        {k: v for k, v in upload_out(u).items() if k not in ("pages", "raw_text")} for u in uploads
    ]


@router.get("/{upload_id}")
def get_upload(upload_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return upload_out(owned_upload(upload_id, user, db))


@router.get("/{upload_id}/file")
def get_upload_file(upload_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    upload = owned_upload(upload_id, user, db)
    if not upload.file_url:
        raise HTTPException(404, "This upload has no file.")
    try:
        data = get_storage().get(upload.file_url)
    except StorageError:
        raise HTTPException(404, "The original file is no longer available.")
    return Response(
        data,
        media_type=upload.mime_type or "application/octet-stream",
        headers={"Cache-Control": "private, max-age=300", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/{upload_id}/records")
def get_upload_records(upload_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    upload = owned_upload(upload_id, user, db)
    records = sorted(upload.records, key=lambda r: (r.source_reference == "manual-entry", r.line_index or 0, r.created_at))
    return [record_out(r) for r in records]


@router.post("/{upload_id}/records", status_code=201)
def add_record(
    upload_id: str, body: RecordFields, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    upload = owned_upload(upload_id, user, db)
    if upload.status in (UploadStatus.UPLOADED, UploadStatus.PROCESSING):
        raise HTTPException(409, "Wait for processing to finish before adding records.")
    return record_out(record_service.add_manual_record(db, upload, body.changes()))


@router.post("/{upload_id}/confirm")
def confirm_upload(
    upload_id: str,
    body: ConfirmUpload | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    upload = owned_upload(upload_id, user, db)
    try:
        confirmed = record_service.confirm_upload(db, upload, body.record_ids if body else None)
    except record_service.RecordValidationError as exc:
        raise HTTPException(422, {"message": exc.message, "records": exc.records})
    return {"confirmed": len(confirmed), "upload": upload_out(upload)}


@router.post("/{upload_id}/retry", status_code=202)
def retry_upload(
    upload_id: str, background: BackgroundTasks, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    upload = owned_upload(upload_id, user, db)
    if upload.status == UploadStatus.PROCESSING:
        raise HTTPException(409, "This upload is already being processed.")
    if any(r.status == RecordStatus.CONFIRMED for r in upload.records):
        raise HTTPException(409, "Some records are already confirmed. Edit them instead of re-processing.")
    clear_extraction(db, upload)
    return _start(upload, background, db)


@router.delete("/{upload_id}")
def delete_upload(upload_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    upload = owned_upload(upload_id, user, db)
    removed = upload_service.delete_upload(db, upload)
    return {"deleted": True, "records_removed": removed}


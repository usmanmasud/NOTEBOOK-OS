"""Upload intake: validate type and size from the file bytes, store, create the row."""

import hashlib
from pathlib import PurePath

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import log_event
from app.core.storage import get_storage
from app.models import Upload, UploadStatus, UploadType, User, new_id


class UploadRejected(Exception):
    def __init__(self, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def sniff_image(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def sniff_audio(data: bytes) -> str | None:
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "audio/wav"
    if data.startswith(b"ID3") or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "audio/mpeg"
    if data.startswith(b"OggS"):
        return "audio/ogg"
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return "audio/webm"
    if data[4:8] == b"ftyp":
        return "audio/mp4"
    return None


_EXT = {
    "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp",
    "audio/wav": "wav", "audio/mpeg": "mp3", "audio/ogg": "ogg", "audio/webm": "webm", "audio/mp4": "m4a",
}


def _safe_name(filename: str | None) -> str | None:
    if not filename:
        return None
    return PurePath(filename.replace("\\", "/")).name[:255] or None


def create_file_upload(db: Session, user: User, kind: UploadType, data: bytes, filename: str | None) -> Upload:
    settings = get_settings()
    if not data:
        raise UploadRejected("The file is empty.")
    if kind == UploadType.PHOTO:
        limit, mime = settings.max_photo_bytes, sniff_image(data)
        if mime is None:
            raise UploadRejected("Please upload a photo (JPEG, PNG or WebP).", 415)
    else:
        limit, mime = settings.max_voice_bytes, sniff_audio(data)
        if mime is None:
            raise UploadRejected("Please upload an audio recording (WAV, MP3, M4A, OGG or WebM).", 415)
    if len(data) > limit:
        raise UploadRejected(f"The file is too large (max {limit // (1024 * 1024)} MB).", 413)

    upload_id = new_id()
    key = f"uploads/{user.id}/{upload_id}.{_EXT[mime]}"
    get_storage().put(key, data, mime)
    upload = Upload(
        id=upload_id,
        user_id=user.id,
        type=kind,
        file_url=key,
        original_filename=_safe_name(filename),
        mime_type=mime,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        status=UploadStatus.UPLOADED,
    )
    db.add(upload)
    db.commit()
    log_event("upload_received", upload_id=upload.id, type=kind.value, bytes=len(data), mime=mime)
    return upload


def create_text_upload(db: Session, user: User, text: str) -> Upload:
    text = text.strip()
    if not text:
        raise UploadRejected("Type at least one transaction.")
    if len(text) > get_settings().max_text_chars:
        raise UploadRejected("That entry is too long.")
    upload = Upload(user_id=user.id, type=UploadType.TEXT, raw_text=text, status=UploadStatus.UPLOADED,
                    mime_type="text/plain", size_bytes=len(text.encode()))
    db.add(upload)
    db.commit()
    log_event("upload_received", upload_id=upload.id, type="TEXT", chars=len(text))
    return upload


def delete_upload(db: Session, upload: Upload) -> int:
    """Delete an upload, its stored file and every record extracted from it."""
    removed = len(upload.records)
    if upload.file_url:
        try:
            get_storage().delete(upload.file_url)
        except Exception:
            log_event("upload_file_delete_failed", upload_id=upload.id)
    db.delete(upload)
    db.commit()
    log_event("upload_deleted", upload_id=upload.id, records_removed=removed)
    return removed

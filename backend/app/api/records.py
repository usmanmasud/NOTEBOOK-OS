from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import current_user
from app.core.db import get_db
from app.models import Record, User
from app.provenance.trace import record_out
from app.schemas.requests import RecordFields
from app.services import records as record_service

router = APIRouter(prefix="/records", tags=["records"])


def owned_record(record_id: str, user: User, db: Session) -> Record:
    record = db.get(Record, record_id)
    if record is None or record.user_id != user.id:
        raise HTTPException(404, "Record not found.")
    return record


@router.get("/{record_id}")
def get_record(record_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return record_out(owned_record(record_id, user, db))


@router.patch("/{record_id}")
def update_record(
    record_id: str, body: RecordFields, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    record = owned_record(record_id, user, db)
    changes = body.changes()
    if not changes:
        raise HTTPException(422, "Nothing to change.")
    return record_out(record_service.update_record(db, record, changes))


@router.post("/{record_id}/confirm")
def confirm_record(record_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    record = owned_record(record_id, user, db)
    try:
        return record_out(record_service.confirm_record(db, record))
    except record_service.RecordValidationError as exc:
        raise HTTPException(422, {"message": exc.message, "records": exc.records})


@router.post("/{record_id}/reject")
def reject_record(record_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return record_out(record_service.reject_record(db, owned_record(record_id, user, db)))

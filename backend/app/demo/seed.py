"""Fictional demo account data.

`reset_demo_user(with_history=True)` processes the fictional Notebook C pages through
the real pipeline (using the offline demo reading) and confirms them, so the
dashboard has some earlier history before the live demo. These uploads are marked
`seeded_demo_history` and the UI labels them as such: they were confirmed by the
seeding script, not by a person.
"""

from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth.service import get_or_create_demo_user
from app.core.config import get_settings
from app.core.logging import log_event
from app.models import Person, Report, Upload, UploadType, User
from app.providers.demo import DemoOCRProvider
from app.services.pipeline import run_pipeline
from app.services.records import confirm_upload
from app.services.uploads import create_file_upload, delete_upload

HISTORY_PAGES = ["notebooks/notebook_c_page4.png", "notebooks/notebook_c_page5.png"]


def clear_user_data(db: Session, user: User) -> None:
    for upload in db.scalars(select(Upload).where(Upload.user_id == user.id)).all():
        delete_upload(db, upload)
    db.execute(delete(Report).where(Report.user_id == user.id))
    db.execute(delete(Person).where(Person.user_id == user.id))
    db.commit()


def reset_demo_user(db: Session, user: User, with_history: bool = True) -> dict:
    if not user.is_demo:
        raise ValueError("refusing to reset a non-demo account")
    clear_user_data(db, user)
    confirmed = 0
    if with_history:
        samples = Path(get_settings().samples_dir)
        ocr = DemoOCRProvider()
        for rel in HISTORY_PAGES:
            path = samples / rel
            if not path.exists():
                continue
            data = path.read_bytes()
            upload = create_file_upload(db, user, UploadType.PHOTO, data, path.name)
            run_pipeline(db, upload, read=ocr.read_image(data, "image/png"))
            upload.pipeline_info = {**(upload.pipeline_info or {}), "seeded_demo_history": True}
            db.commit()
            confirmed += len(confirm_upload(db, upload))
    log_event("demo_reset", user_id=user.id, with_history=with_history, records=confirmed)
    return {"reset": True, "history_records_confirmed": confirmed}


def seed_demo(db: Session, with_history: bool = True) -> dict:
    """Idempotent: creates the demo user and seeds history only if it has no uploads yet."""
    user = get_or_create_demo_user(db)
    has_data = db.scalar(select(Upload.id).where(Upload.user_id == user.id).limit(1)) is not None
    if has_data:
        return {"reset": False, "reason": "demo account already has data"}
    return reset_demo_user(db, user, with_history)

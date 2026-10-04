"""Database models.

Primary keys are random UUID strings so identifiers are not enumerable.
Only records with status CONFIRMED count towards official metrics and reports.
"""

import enum
import uuid
import datetime as dt
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UploadType(str, enum.Enum):
    PHOTO = "PHOTO"
    VOICE = "VOICE"
    TEXT = "TEXT"  # typed entry: same pipeline, no OCR/speech stage


class UploadStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    REVIEW = "REVIEW"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


class RecordType(str, enum.Enum):
    SALE = "SALE"
    DEBT = "DEBT"  # goods/money given on credit: the person owes the trader
    EXPENSE = "EXPENSE"
    RESTOCK = "RESTOCK"
    PAYMENT = "PAYMENT"  # a person repaying debt they owe the trader
    OTHER = "OTHER"


class RecordStatus(str, enum.Enum):
    AI_EXTRACTED = "AI_EXTRACTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class ReportStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


def _enum(e: type[enum.Enum]) -> Enum:
    return Enum(e, native_enum=False, length=20, validate_strings=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    phone: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(120))
    business_name: Mapped[str | None] = mapped_column(String(160))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[UploadType] = mapped_column(_enum(UploadType), nullable=False)
    # Storage key (local path or OBS object key). Files are served only through
    # the authenticated API, so this is never handed to clients directly.
    file_url: Mapped[str | None] = mapped_column(String(512))
    original_filename: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[UploadStatus] = mapped_column(_enum(UploadStatus), default=UploadStatus.UPLOADED)
    # Full text produced by the READ stage (OCR text or voice transcript, or typed text).
    raw_text: Mapped[str | None] = mapped_column(Text)
    # Short, user-safe explanation when processing fails.
    error_message: Mapped[str | None] = mapped_column(String(500))
    pipeline_info: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)

    pages: Mapped[list["SourcePage"]] = relationship(
        back_populates="upload", cascade="all, delete-orphan", order_by="SourcePage.page_number"
    )
    records: Mapped[list["Record"]] = relationship(back_populates="upload", cascade="all, delete-orphan")


class SourcePage(Base):
    __tablename__ = "source_pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    upload_id: Mapped[str] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), index=True)
    # Notebook page number as written/understood by the trader (may differ from
    # position in the upload); defaults to 1.
    page_number: Mapped[int] = mapped_column(Integer, default=1)
    image_url: Mapped[str | None] = mapped_column(String(512))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    # OCR lines: [{"index", "text", "confidence", "bbox": {x,y,width,height} (0..1)}]
    lines: Mapped[list | None] = mapped_column(JSON)

    upload: Mapped[Upload] = relationship(back_populates="pages")


class Person(Base):
    __tablename__ = "people"
    __table_args__ = (UniqueConstraint("user_id", "normalized_name", name="uq_people_user_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class Record(TimestampMixin, Base):
    __tablename__ = "records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    upload_id: Mapped[str] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), index=True)
    source_page_id: Mapped[str | None] = mapped_column(ForeignKey("source_pages.id", ondelete="SET NULL"))
    person_id: Mapped[str | None] = mapped_column(ForeignKey("people.id", ondelete="SET NULL"))

    # --- Business fields ---------------------------------------------------------
    date: Mapped[dt.date | None] = mapped_column(Date)
    type: Mapped[RecordType | None] = mapped_column(_enum(RecordType))
    item: Mapped[str | None] = mapped_column(String(160))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    person: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(String(500))

    # --- AI + validation ---------------------------------------------------------
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    # Per-field confidence from extraction, e.g. {"amount": 0.55, "person": 0.9}.
    field_confidence: Mapped[dict | None] = mapped_column(JSON)
    # Deterministic validation output: [{"field", "code", "message", "severity"}].
    validation_issues: Mapped[list | None] = mapped_column(JSON)
    # What the AI originally proposed, kept unchanged for audit after edits.
    ai_original: Mapped[dict | None] = mapped_column(JSON)
    edited: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[RecordStatus] = mapped_column(_enum(RecordStatus), default=RecordStatus.NEEDS_REVIEW)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)

    # --- Provenance ----------------------------------------------------------------
    source_reference: Mapped[str | None] = mapped_column(String(64))  # e.g. "page-2-row-4"
    line_index: Mapped[int | None] = mapped_column(Integer)
    original_text: Mapped[str | None] = mapped_column(String(500))
    # Bounding box of the source line on the page image, as fractions (0..1).
    bbox_x: Mapped[float | None] = mapped_column(Float)
    bbox_y: Mapped[float | None] = mapped_column(Float)
    bbox_width: Mapped[float | None] = mapped_column(Float)
    bbox_height: Mapped[float | None] = mapped_column(Float)

    upload: Mapped[Upload] = relationship(back_populates="records")
    source_page: Mapped[SourcePage | None] = relationship()


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    period_start: Mapped[dt.date | None] = mapped_column(Date)
    period_end: Mapped[dt.date | None] = mapped_column(Date)
    # Frozen copy of the figures at generation time, so a shared link stays stable.
    snapshot: Mapped[dict | None] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    share_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[ReportStatus] = mapped_column(_enum(ReportStatus), default=ReportStatus.ACTIVE)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)

"""Request bodies. Responses are plain dicts built in app/provenance and app/reports."""

import datetime as dt
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.extraction.normalize import parse_amount

RecordTypeLiteral = Literal["SALE", "DEBT", "EXPENSE", "RESTOCK", "PAYMENT", "OTHER"]


class OtpRequest(BaseModel):
    phone: str = Field(min_length=7, max_length=20)


class OtpVerify(BaseModel):
    phone: str = Field(min_length=7, max_length=20)
    code: str = Field(min_length=4, max_length=8)


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    business_name: str | None = Field(default=None, max_length=160)


class TextUpload(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class RecordFields(BaseModel):
    """Editable record fields. Only fields present in the request are changed."""

    model_config = ConfigDict(extra="forbid")

    date: dt.date | None = None
    type: RecordTypeLiteral | None = None
    item: str | None = Field(default=None, max_length=160)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=3)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    person: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("amount", mode="before")
    @classmethod
    def _amount(cls, v):
        # Accept the way traders write money: "20k", "₦20,000".
        if isinstance(v, str):
            parsed = parse_amount(v)
            if parsed is None:
                raise ValueError("Enter the amount as a number, e.g. 20000")
            return parsed
        return v

    def changes(self) -> dict:
        return {k: getattr(self, k) for k in self.model_fields_set}


class ConfirmUpload(BaseModel):
    record_ids: list[str] | None = None


class ReportCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    period_start: dt.date | None = None
    period_end: dt.date | None = None
    consent: bool = False


class DemoReset(BaseModel):
    with_history: bool = True

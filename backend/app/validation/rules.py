"""VALIDATE stage: deterministic checks on proposed records.

Validation never rejects a record. It produces issues that tell the trader what
needs attention:
  * severity "error"   - must be fixed before the record can be confirmed
  * severity "warning" - worth checking, does not block confirmation
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.core.config import Settings
from app.extraction.normalize import money_values_in
from app.extraction.vocab import load_vocab

ALLOWED_TYPES = {"SALE", "DEBT", "EXPENSE", "RESTOCK", "PAYMENT", "OTHER"}
PERSON_REQUIRED = {"DEBT", "PAYMENT"}


def confidence_level(value: float, settings: Settings) -> str:
    if value >= settings.confidence_high:
        return "high"
    if value >= settings.confidence_review:
        return "review"
    return "low"


def _issue(field: str, code: str, message: str, severity: str) -> dict:
    return {"field": field, "code": code, "message": message, "severity": severity}


def validate_record(
    fields: dict,
    field_confidence: dict,
    confidence: float,
    original_text: str | None,
    human_fields: set[str],
    settings: Settings,
    today: date,
) -> list[dict]:
    issues: list[dict] = []
    rtype = fields.get("type")
    amount = fields.get("amount")
    quantity = fields.get("quantity")
    person = fields.get("person")
    rdate = fields.get("date")

    if rtype is None:
        issues.append(_issue("type", "missing", "Choose what kind of transaction this is.", "error"))
    elif rtype not in ALLOWED_TYPES:
        issues.append(_issue("type", "invalid", "Unknown transaction type.", "error"))

    if amount is None:
        issues.append(_issue("amount", "missing", "Amount could not be read. Please enter it.", "error"))
    else:
        if not isinstance(amount, Decimal) or amount <= 0:
            issues.append(_issue("amount", "invalid", "Amount must be a number greater than zero.", "error"))
        elif amount > Decimal(str(settings.suspicious_amount)):
            issues.append(_issue("amount", "suspicious", "This amount is unusually large. Please double-check.", "warning"))

    if quantity is not None and (not isinstance(quantity, Decimal) or quantity <= 0):
        issues.append(_issue("quantity", "invalid", "Quantity must be a number greater than zero.", "error"))

    if rtype in PERSON_REQUIRED and not person:
        issues.append(_issue("person", "missing", "Who is this debt or payment for?", "error"))

    if rdate is not None:
        if rdate > today + timedelta(days=1):
            issues.append(_issue("date", "future", "This date is in the future.", "warning"))
        elif rdate < today - timedelta(days=730):
            issues.append(_issue("date", "old", "This date is more than two years ago.", "warning"))

    # Anti-hallucination: AI-proposed values must be traceable to the source text.
    if original_text:
        vocab = load_vocab(tuple(settings.extraction_language_list))
        if amount is not None and "amount" not in human_fields:
            if amount not in money_values_in(original_text, vocab.units, vocab.thousand_words):
                issues.append(
                    _issue("amount", "not_in_source", "This amount does not appear in the original text.", "warning")
                )
        if person and "person" not in human_fields and person.lower() not in original_text.lower():
            issues.append(
                _issue("person", "not_in_source", "This name does not appear in the original text.", "warning")
            )

    for name, value in field_confidence.items():
        if name in human_fields or fields.get(name) is None:
            continue
        if value < settings.confidence_review:
            issues.append(_issue(name, "low_confidence", "The AI is unsure about this value.", "warning"))

    return issues


def has_errors(issues: list[dict] | None) -> bool:
    return any(i.get("severity") == "error" for i in issues or [])


def needs_review(issues: list[dict], confidence: float, settings: Settings) -> bool:
    return bool(issues) or confidence < settings.confidence_high


@dataclass
class TotalCheck:
    page_number: int
    reference: str
    written_total: Decimal
    extracted_sales: Decimal

    @property
    def matches(self) -> bool:
        return self.written_total == self.extracted_sales

    def to_dict(self) -> dict:
        return {
            "page_number": self.page_number,
            "reference": self.reference,
            "written_total": str(self.written_total),
            "extracted_sales": str(self.extracted_sales),
            "matches": self.matches,
        }


def check_written_totals(totals, records_by_page: dict[int, list[dict]]) -> list[TotalCheck]:
    """Compare totals written in the notebook with the sum of extracted sales on that page.

    A mismatch suggests a missed or misread line. This is a consistency hint only;
    official figures always come from confirmed records.
    """
    checks = []
    for total in totals:
        page_records = records_by_page.get(total.line.page_number, [])
        sales = sum(
            (r["amount"] for r in page_records if r.get("type") == "SALE" and r.get("amount") is not None),
            Decimal("0"),
        )
        checks.append(TotalCheck(total.line.page_number, total.line.reference, total.amount, sales))
    return checks

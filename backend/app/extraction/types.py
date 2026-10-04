"""Data passed between the READ, UNDERSTAND and VALIDATE stages."""

from dataclasses import dataclass, field
from decimal import Decimal

FIELDS = ("date", "type", "item", "quantity", "amount", "person", "notes")


@dataclass
class SourceLine:
    page_number: int
    line_index: int
    text: str
    confidence: float = 1.0
    bbox: dict | None = None

    @property
    def line_id(self) -> str:
        """Identifier the interpreter must use to tie a record to its evidence."""
        return f"p{self.page_number}:L{self.line_index}"

    @property
    def reference(self) -> str:
        """Human-readable provenance reference, e.g. "page-2-row-4" (rows are 1-based)."""
        return f"page-{self.page_number}-row-{self.line_index + 1}"


@dataclass
class Candidate:
    """A proposed record. Never authoritative until a human confirms it."""

    line: SourceLine
    fields: dict
    field_confidence: dict
    confidence: float


@dataclass
class WrittenTotal:
    line: SourceLine
    amount: Decimal


@dataclass
class Interpretation:
    candidates: list[Candidate]
    totals: list[WrittenTotal] = field(default_factory=list)
    interpreter: str = "rules"
    fallback_reason: str | None = None

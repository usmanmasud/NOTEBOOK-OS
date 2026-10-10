"""LLM-based interpreter with a strict output schema.

The model sees each source line tagged with an id (e.g. "p2:L3") and must attach
every record to one of those ids, so provenance is assigned by the application,
not invented by the model. Output that does not match the schema is rejected as a
whole (`ExtractionError`) and the pipeline falls back to the rule-based interpreter.
"""

import json
import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.extraction.normalize import parse_amount, parse_iso_date
from app.extraction.types import Candidate, Interpretation, SourceLine, WrittenTotal
from app.providers.base import LLMProvider

RecordTypeLiteral = Literal["SALE", "DEBT", "EXPENSE", "RESTOCK", "PAYMENT", "OTHER"]


class ExtractionError(Exception):
    pass


class LLMRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    line_id: str
    date: str | None = None
    type: RecordTypeLiteral | None = None
    item: str | None = Field(default=None, max_length=160)
    quantity: float | None = None
    amount: float | str | None = None
    person: str | None = Field(default=None, max_length=120)
    confidence: float = Field(ge=0, le=1)
    field_confidence: dict[str, float] = Field(default_factory=dict)

    @field_validator("type", mode="before")
    @classmethod
    def _upper(cls, v):
        return v.upper() if isinstance(v, str) else v


class LLMTotal(BaseModel):
    model_config = ConfigDict(extra="ignore")

    line_id: str
    amount: float | str


class LLMOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    records: list[LLMRecord]
    totals: list[LLMTotal] = Field(default_factory=list)


SYSTEM_PROMPT = """You convert lines from a small trader's handwritten notebook (or a voice note \
transcript) into structured transaction records. Lines may mix English, Hausa and informal \
abbreviations, and may contain OCR errors.

Rules:
- Only extract what is written. NEVER invent amounts, people, items, dates or transactions.
- If a value is unclear or missing, use null and lower the confidence for that field.
- Do NOT do arithmetic. Do not compute totals, balances or unit prices.
- Every record must reference exactly one line_id from the input.
- Lines that are headings, dates or notes are not records. A line stating a written total \
goes in "totals", not "records".
- type is one of SALE, DEBT (someone took goods/money on credit and owes the trader), \
EXPENSE, RESTOCK (trader bought stock), PAYMENT (someone repaid what they owed), OTHER.
- amount is a plain number in the local currency ("20k" = 20000, "dubu 15" = 15000).
- date is ISO YYYY-MM-DD only if a date is written on that line or in a heading above it; else null.
- confidence and field_confidence are between 0 and 1 and reflect how clearly the value is written.

Vocabulary hints (not exhaustive; interpret by meaning): bashi = debt/credit, biya = pay/repay, \
sayar = sell, kashe = spend, kaya = goods/stock, sayo kaya = bought stock, kudin mota = transport, \
haya = rent, dubu = thousand, buhu = bag, jimla = total.

Respond with JSON only, in exactly this shape:
{"records":[{"line_id":"p1:L0","date":null,"type":"SALE","item":"Rice","quantity":2,"amount":30000,\
"person":null,"confidence":0.9,"field_confidence":{"type":0.95,"amount":0.9,"item":0.9,"quantity":0.9}}],\
"totals":[{"line_id":"p1:L5","amount":45000}]}

Examples:
"Musa shinkafa 2? 20k bashi" -> type DEBT, person "Musa", item "Rice", quantity null (unclear), amount 20000.
"Aisha ta biya 10k" -> type PAYMENT, person "Aisha", amount 10000.
"Kudin mota N2,500" -> type EXPENSE, item "Transport", amount 2500.
"Litinin 1/10/26" -> not a record (date heading)."""


def build_user_prompt(lines: list[SourceLine], reference: date, date_order: str) -> str:
    rendered = "\n".join(f"[{ln.line_id}] {ln.text}" for ln in lines if ln.text.strip())
    return (
        f"Date format in this market: {date_order}. Upload date (for missing years only): "
        f"{reference.isoformat()}.\n\nLines:\n{rendered}"
    )


def parse_llm_output(raw: str) -> LLMOutput:
    # Reasoning models (e.g. DeepSeek-R1 on ModelArts) may prepend a <think> block.
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.S).strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.S)
    if fence:
        text = fence.group(1)
    elif not text.startswith("{") and "{" in text and "}" in text:
        # Tolerate a short preamble/epilogue around the JSON object.
        text = text[text.index("{") : text.rindex("}") + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ExtractionError("model output was not valid JSON") from exc
    try:
        return LLMOutput.model_validate(data)
    except ValidationError as exc:
        raise ExtractionError(f"model output did not match schema ({exc.error_count()} errors)") from exc


class LLMInterpreter:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self.name = provider.name

    def interpret(self, lines: list[SourceLine], reference: date, date_order: str = "DMY") -> Interpretation:
        raw = self.provider.complete_json(SYSTEM_PROMPT, build_user_prompt(lines, reference, date_order))
        output = parse_llm_output(raw)
        by_id = {ln.line_id: ln for ln in lines}

        candidates: list[Candidate] = []
        for rec in output.records:
            line = by_id.get(rec.line_id)
            if line is None:
                continue  # a record that cannot be traced to evidence is discarded
            fc = {k: max(0.0, min(1.0, float(v))) for k, v in rec.field_confidence.items()}
            amount = parse_amount(rec.amount)
            if rec.amount is not None and amount is None:
                fc["amount"] = 0.0
            record_date = parse_iso_date(rec.date)
            if rec.date and record_date is None:
                fc["date"] = 0.0
            fields = {
                "date": record_date,
                "type": rec.type,
                "item": (rec.item or "").strip() or None,
                "quantity": parse_amount(rec.quantity) if rec.quantity is not None else None,
                "amount": amount,
                "person": (rec.person or "").strip() or None,
                "notes": None,
            }
            for key in ("type", "amount", "item", "person", "quantity", "date"):
                if fields[key] is not None:
                    fc.setdefault(key, rec.confidence)
            required = ["type", "amount"] + (["person"] if rec.type in ("DEBT", "PAYMENT") else [])
            conf = min([rec.confidence] + [fc.get(f, 0.0) if fields[f] is not None else 0.0 for f in required])
            candidates.append(
                Candidate(line=line, fields=fields, field_confidence=fc, confidence=round(min(conf, line.confidence), 2))
            )

        totals = []
        for t in output.totals:
            line = by_id.get(t.line_id)
            amount = parse_amount(t.amount)
            if line is not None and amount is not None:
                totals.append(WrittenTotal(line=line, amount=amount))
        return Interpretation(candidates=candidates, totals=totals, interpreter=self.name)

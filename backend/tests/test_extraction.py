"""READ-output parsing, rule-based interpretation and LLM JSON validation."""

import json
from datetime import date
from decimal import Decimal

import pytest

from app.extraction.interpret import interpret
from app.extraction.llm_interpreter import ExtractionError, LLMInterpreter, parse_llm_output
from app.extraction.normalize import find_date, parse_amount
from app.extraction.rules import RuleBasedInterpreter
from app.extraction.types import SourceLine
from app.extraction.vocab import load_vocab
from app.providers import registry
from app.providers.base import ProviderUnavailable

REF = date(2026, 10, 4)


def lines(*texts, page=2, conf=0.9):
    return [SourceLine(page, i, t, conf) for i, t in enumerate(texts)]


def rules():
    return RuleBasedInterpreter(load_vocab(("en", "ha")))


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("20k", Decimal(20000)), ("₦20,000", Decimal(20000)), ("N2,500", Decimal(2500)),
        ("1.5m", Decimal(1500000)), ("dubu 15", Decimal(15000)), (45000, Decimal(45000)),
        ("20k?", None), ("abc", None), ("", None), (None, None),
    ],
)
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == expected


def test_find_date_dmy_and_inferred_year():
    assert find_date("1/10/26", REF).value == date(2026, 10, 1)
    found = find_date("Talata 2/10", REF)
    assert found.value == date(2026, 10, 2) and found.year_inferred
    assert find_date("3 Oct", REF).value == date(2026, 10, 3)
    assert find_date("Sold 3 bags rice", REF) is None


def test_rules_mixed_language_page():
    result = rules().interpret(
        lines(
            "1/10/26",
            "Sold 3 bags rice 45,000",
            "Musa shinkafa 2? 20k bashi",
            "Kudin mota 2,500",
            "Sayo kaya sukari 5 buhu 150k",
            "Aisha ta biya 10k",
            "Total sales 45,000",
        ),
        REF,
    )
    got = [(c.fields["type"], c.fields["amount"], c.fields["person"]) for c in result.candidates]
    assert got == [
        ("SALE", Decimal(45000), None),
        ("DEBT", Decimal(20000), "Musa"),
        ("EXPENSE", Decimal(2500), None),
        ("RESTOCK", Decimal(150000), None),
        ("PAYMENT", Decimal(10000), "Aisha"),
    ]
    assert all(c.fields["date"] == date(2026, 10, 1) for c in result.candidates)
    assert [t.amount for t in result.totals] == [Decimal(45000)]


def test_rules_unclear_quantity_becomes_null_not_guessed():
    musa = rules().interpret(lines("Musa shinkafa 2? 20k bashi", conf=0.61), REF).candidates[0]
    assert musa.fields["quantity"] is None
    assert musa.fields["item"] == "Rice"
    assert musa.confidence == 0.61  # capped by OCR confidence for the line
    assert "2?" in musa.fields["notes"]


def test_rules_unclear_amount_is_null_and_zero_confidence():
    cand = rules().interpret(lines("sayar gishiri ?,000"), REF).candidates[0]
    assert cand.fields["type"] == "SALE"
    assert cand.fields["amount"] is None
    assert cand.confidence == 0.0


def test_rules_ocr_confusable_digits_are_low_confidence():
    cand = rules().interpret(lines("Halima taliya kwali 1 bashi 8,5OO"), REF).candidates[0]
    assert cand.fields["amount"] == Decimal(8500)
    assert cand.field_confidence["amount"] == 0.5


def test_rules_no_type_keyword_gives_null_type():
    cand = rules().interpret(lines("Musa 20k"), REF).candidates[0]
    assert cand.fields["type"] is None and cand.confidence == 0.0


def test_rules_skip_headings_and_notes():
    result = rules().interpret(lines("Demo Provisions Store", "p.2", "Litinin"), REF)
    assert result.candidates == []


# ---- LLM output validation -----------------------------------------------------------


class FakeLLM:
    name = "fake-llm"

    def __init__(self, output):
        self.output = output
        self.calls = 0

    def complete_json(self, system, user):
        self.calls += 1
        if isinstance(self.output, Exception):
            raise self.output
        return self.output if isinstance(self.output, str) else json.dumps(self.output)


def test_llm_output_valid_and_fenced():
    payload = {"records": [{"line_id": "p2:L0", "type": "debt", "amount": "20k", "person": "Musa", "confidence": 0.7}]}
    parsed = parse_llm_output("```json\n" + json.dumps(payload) + "\n```")
    assert parsed.records[0].type == "DEBT"


@pytest.mark.parametrize(
    "raw",
    [
        "not json at all",
        '{"records": "nope"}',
        '{"records": [{"line_id": "p2:L0", "type": "LOAN", "confidence": 0.5}]}',
        '{"records": [{"line_id": "p2:L0", "confidence": 7}]}',
        '{"items": []}',
    ],
)
def test_llm_malformed_output_is_rejected(raw):
    with pytest.raises(ExtractionError):
        parse_llm_output(raw)


def test_llm_output_with_reasoning_and_preamble():
    payload = '{"records": [{"line_id": "p2:L0", "type": "SALE", "amount": 45000, "confidence": 0.9}]}'
    parsed = parse_llm_output("<think>The line says sold rice.</think>\nHere is the JSON:\n" + payload + "\nDone.")
    assert parsed.records[0].amount == 45000


def test_llm_records_must_reference_real_lines():
    llm = FakeLLM({"records": [
        {"line_id": "p2:L0", "type": "SALE", "amount": 45000, "confidence": 0.9},
        {"line_id": "p9:L9", "type": "SALE", "amount": 999999, "confidence": 0.99},
    ]})
    result = LLMInterpreter(llm).interpret(lines("Sold rice 45,000"), REF)
    assert len(result.candidates) == 1
    assert result.candidates[0].line.reference == "page-2-row-1"


def test_llm_confidence_capped_by_ocr_confidence():
    llm = FakeLLM({"records": [{"line_id": "p2:L0", "type": "DEBT", "amount": 20000, "person": "Musa", "confidence": 0.95}]})
    cand = LLMInterpreter(llm).interpret(lines("Musa 20k bashi", conf=0.61), REF).candidates[0]
    assert cand.confidence == 0.61


def test_llm_failure_falls_back_to_rules():
    registry.override("llm", [FakeLLM(ProviderUnavailable("down", "timeout"))])
    result = interpret(lines("Sold 3 bags rice 45,000"), REF)
    assert result.interpreter == "rules"
    assert result.fallback_reason == "timeout"
    assert result.candidates[0].fields["amount"] == Decimal(45000)


def test_llm_malformed_falls_back_to_rules():
    registry.override("llm", [FakeLLM("I think Musa owes money")])
    result = interpret(lines("Musa 20k bashi"), REF)
    assert result.interpreter == "rules" and result.fallback_reason


def test_llm_used_when_valid():
    registry.override("llm", [FakeLLM({"records": [{"line_id": "p2:L0", "type": "SALE", "amount": 45000, "confidence": 0.9}]})])
    result = interpret(lines("Sold 3 bags rice 45,000"), REF)
    assert result.interpreter == "fake-llm" and result.fallback_reason is None

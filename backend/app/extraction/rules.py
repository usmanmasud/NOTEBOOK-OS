"""Deterministic rule-based interpreter.

Works offline and is the fallback whenever the LLM is unavailable or returns
something invalid. It only reports what is written: unclear values become null
with low confidence, nothing is invented and no arithmetic is performed.
"""

import re
from datetime import date

from app.extraction.normalize import FoundDate, find_date, find_numbers, spaced
from app.extraction.types import Candidate, Interpretation, SourceLine, WrittenTotal
from app.extraction.vocab import Vocab

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’\-]*")


def _match_phrases(lowered: str, phrases: list[tuple[str, str]]) -> list[tuple[int, int, str]]:
    """Non-overlapping whole-word phrase matches, longest phrases first."""
    taken: list[tuple[int, int]] = []
    hits: list[tuple[int, int, str]] = []
    for phrase, value in sorted(phrases, key=lambda p: -len(p[0])):
        for m in re.finditer(rf"(?<![a-z]){re.escape(phrase)}(?![a-z])", lowered):
            s, e = m.span()
            if any(s < te and ts < e for ts, te in taken):
                continue
            taken.append((s, e))
            hits.append((s, e, value))
    return sorted(hits)


def _resolve_type(hits: list[str], order: list[str]) -> tuple[str | None, float]:
    types = list(dict.fromkeys(hits))
    if not types:
        return None, 0.0
    if len(types) == 1:
        return types[0], 0.9
    # Common composite phrasings: "ya biya bashi" (paid the debt), "sold on credit".
    if "PAYMENT" in types:
        return "PAYMENT", 0.8
    if "DEBT" in types:
        return "DEBT", 0.8
    return sorted(types, key=lambda t: order.index(t) if t in order else 99)[0], 0.6


class RuleBasedInterpreter:
    name = "rules"

    def __init__(self, vocab: Vocab) -> None:
        self.vocab = vocab
        self.keyword_words = vocab.keyword_words

    def interpret(self, lines: list[SourceLine], reference: date, date_order: str = "DMY") -> Interpretation:
        candidates: list[Candidate] = []
        totals: list[WrittenTotal] = []
        header_date: FoundDate | None = None

        for line in lines:
            text = spaced(line.text.strip())
            if not text:
                continue
            lowered = text.lower()
            numbers = find_numbers(text, self.vocab.units, self.vocab.thousand_words)
            money = [n for n in numbers if n.is_money]
            type_hits = _match_phrases(lowered, self.vocab.type_phrases)
            found_date = find_date(text, reference, date_order)

            if found_date and not money and not type_hits:
                header_date = found_date  # a date heading applies to the lines below it
                continue
            if any(re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", lowered) for w in self.vocab.total_markers):
                if money:
                    totals.append(WrittenTotal(line=line, amount=money[-1].value))
                continue
            if not money and not type_hits:
                continue  # heading, page number or a note without a transaction

            candidates.append(self._candidate(line, text, lowered, numbers, money, type_hits, found_date, header_date))

        return Interpretation(candidates=candidates, totals=totals, interpreter=self.name)

    def _candidate(self, line, text, lowered, numbers, money, type_hits, found_date, header_date) -> Candidate:
        # Blank out number tokens so digits/OCR letters inside them are not read as words.
        words_text = text
        for n in numbers:
            words_text = words_text[: n.start] + " " * (n.end - n.start) + words_text[n.end :]

        fields: dict = {k: None for k in ("date", "type", "item", "quantity", "amount", "person", "notes")}
        conf: dict[str, float] = {}
        unclear: list[str] = []

        rtype, conf["type"] = _resolve_type([h[2] for h in type_hits], self.vocab.type_order)
        fields["type"] = rtype

        # Amount: read exactly as written; several different amounts are ambiguous.
        distinct = list(dict.fromkeys(t.value for t in money))
        if distinct:
            token = [t for t in money if t.value == distinct[-1]][-1]
            if token.uncertain and "?" in token.raw:
                unclear.append(token.raw)
                conf["amount"] = 0.2
            else:
                fields["amount"] = token.value
                if token.uncertain:
                    conf["amount"] = 0.5
                elif len(distinct) > 1:
                    conf["amount"] = 0.55
                else:
                    conf["amount"] = 0.95 if token.explicit else 0.8
        else:
            conf["amount"] = 0.0

        quantities = [n for n in numbers if not n.is_money]
        if quantities:
            q = quantities[0]
            if q.uncertain:
                unclear.append(q.raw)
                conf["quantity"] = 0.2
            else:
                fields["quantity"] = q.value
                conf["quantity"] = (0.9 if q.unit else 0.6) if len(quantities) == 1 else 0.5

        # Person: leading capitalised words that carry no vocabulary meaning.
        name_words: list[str] = []
        for m in _WORD_RE.finditer(words_text):
            word = m.group(0)
            if word.lower() in self.keyword_words or not word[0].isupper() or len(word) < 2:
                if name_words:
                    break
                continue
            name_words.append(word)
            if len(name_words) == 3:
                break
        if name_words:
            fields["person"] = " ".join(name_words)
            conf["person"] = 0.85 if rtype in ("DEBT", "PAYMENT") else 0.75

        # Item: known product, or expense category for expenses.
        phrases = self.vocab.expense_phrases if rtype == "EXPENSE" else self.vocab.item_phrases
        item_hits = _match_phrases(lowered, phrases)
        if item_hits:
            fields["item"] = item_hits[0][2]
            conf["item"] = 0.9 if rtype == "EXPENSE" else 0.85
        else:
            person_words = {w.lower() for w in name_words}
            leftovers = [
                w for w in _WORD_RE.findall(words_text)
                if w.lower() not in self.keyword_words and w.lower() not in person_words and len(w) > 2
            ]
            if leftovers:
                fields["item"] = " ".join(leftovers[:3]).capitalize()
                conf["item"] = 0.5

        if found_date:
            fields["date"] = found_date.value
            conf["date"] = 0.7 if found_date.year_inferred else 0.9
        elif header_date:
            fields["date"] = header_date.value
            conf["date"] = 0.7 if header_date.year_inferred else 0.88

        if unclear:
            fields["notes"] = "Unclear in notebook: " + ", ".join(unclear)

        required = ["type", "amount"] + (["person"] if rtype in ("DEBT", "PAYMENT") else [])
        record_conf = min(conf.get(f, 0.0) if fields[f] is not None else 0.0 for f in required)
        record_conf = min(record_conf, line.confidence)
        return Candidate(line=line, fields=fields, field_confidence=conf, confidence=round(record_conf, 2))

"""Deterministic parsing of amounts, quantities and dates from messy notebook text.

Used by the rule-based interpreter, to normalise LLM output, and by validation
to check that an extracted amount actually appears in the source text.
"""

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

# OCR commonly confuses these letters with digits inside numbers.
_OCR_DIGIT_FIX = str.maketrans({"O": "0", "o": "0", "l": "1", "I": "1", "S": "5"})

_CURRENCY = r"(?:₦|NGN|N|#|GHS|GH₵|₵|KES|KSh|Ksh|₹|Rs\.?|Tk|৳)"
# A number possibly containing OCR-confused letters, e.g. "2O,OOO" or "l5k".
_NUM = r"[0-9][0-9OolIS,.]*[0-9Oo]|[0-9]"

_MONEY_RE = re.compile(
    rf"(?:(?P<cur>{_CURRENCY})\s?)?(?P<num>{_NUM})\s?(?P<suf>k|K|m|M)?(?![A-Za-z0-9])(?P<q>\?)?"
)


@dataclass
class NumberToken:
    value: Decimal
    raw: str
    start: int
    end: int
    is_money: bool
    uncertain: bool
    unit: str | None = None  # unit word attached to a quantity
    explicit: bool = False  # written with a currency sign, k/m suffix or thousand-word


def _to_decimal(num: str) -> tuple[Decimal | None, bool]:
    fixed = num.translate(_OCR_DIGIT_FIX)
    uncertain = fixed != num
    # "20,000" / "20.000" thousands separators vs "1.5" decimals.
    if re.fullmatch(r"\d{1,3}([,.]\d{3})+", fixed):
        fixed = re.sub(r"[,.]", "", fixed)
    else:
        fixed = fixed.replace(",", "")
    try:
        return Decimal(fixed), uncertain
    except InvalidOperation:
        return None, True


def spaced(text: str) -> str:
    """Separate digits from attached unit words: "20kg" -> "20 kg", "3x" -> "3 x"."""
    text = re.sub(r"(\d)([A-Za-z]{2,})", r"\1 \2", text)
    return re.sub(r"(\d)[xX]\b", r"\1 x", text)


def find_numbers(text: str, units: set[str], thousand_words: set[str]) -> list[NumberToken]:
    """Find numeric tokens and classify them as money or quantity."""
    tokens: list[NumberToken] = []
    text = spaced(text)
    lowered = text.lower()
    for m in _MONEY_RE.finditer(text):
        start, end = m.span()
        # Skip numbers that are part of a word (e.g. "B2") or dates like 1/10/26.
        if start > 0 and text[start - 1].isalpha() and not m.group("cur"):
            continue
        if re.match(r"[/\-]\d", text[end : end + 2]) or (start > 0 and text[start - 1] in "/-" and not m.group("cur")):
            continue
        value, uncertain = _to_decimal(m.group("num"))
        if value is None:
            continue
        suffix = (m.group("suf") or "").lower()
        if suffix == "k":
            value *= 1000
        elif suffix == "m":
            value *= 1_000_000
        uncertain = uncertain or bool(m.group("q"))

        before = lowered[:start].split()
        after = lowered[end:].split()
        prev_word = before[-1] if before else ""
        next_word = after[0].strip(".,:;") if after else ""

        # "dubu 20" / "20 dubu" / "20 thousand" -> 20,000
        thousand = False
        if next_word in thousand_words:
            value *= 1000
            thousand = True
            end = end + lowered[end:].find(next_word) + len(next_word)
        elif prev_word in thousand_words:
            value *= 1000
            thousand = True

        unit = None
        if not (m.group("cur") or suffix or thousand):
            if next_word in units:
                unit = next_word
            elif (
                prev_word in units  # Hausa order: "buhu 2"
                and value < 100
                and not any(t.unit == prev_word and t.end >= start - len(prev_word) - 2 for t in tokens)
            ):
                unit = prev_word

        is_money = bool(m.group("cur") or suffix or thousand) or (unit is None and value >= 100)
        tokens.append(
            NumberToken(
                value=value,
                raw=text[start:end].strip(),
                start=start,
                end=end,
                is_money=is_money,
                uncertain=uncertain,
                unit=unit,
                explicit=bool(m.group("cur") or suffix or thousand),
            )
        )
    return tokens


def money_values_in(text: str, units: set[str], thousand_words: set[str]) -> set[Decimal]:
    return {t.value for t in find_numbers(text, units, thousand_words) if t.is_money}


def parse_amount(value) -> Decimal | None:
    """Normalise an amount coming from an LLM or a user ("20k", "₦20,000", 20000)."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    tokens = find_numbers(str(value), set(), {"thousand", "dubu"})
    money = [t for t in tokens if t.is_money] or tokens
    if len(money) != 1 or money[0].uncertain:
        return None
    return money[0].value


_MONTHS = {
    m: i + 1
    for i, names in enumerate(
        [
            ("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"),
            ("may",), ("jun", "june"), ("jul", "july"), ("aug", "august"),
            ("sep", "sept", "september"), ("oct", "october"), ("nov", "november"), ("dec", "december"),
        ]
    )
    for m in names
}

_NUMERIC_DATE = re.compile(r"\b(\d{1,4})[/\-.](\d{1,2})(?:[/\-.](\d{2,4}))?\b")
_TEXT_DATE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\.?(?:,?\s+(\d{2,4}))?\b")
_TEXT_DATE_US = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{2,4}))?\b")


@dataclass
class FoundDate:
    value: date
    year_inferred: bool


def _year(raw: str | None, reference: date) -> tuple[int, bool]:
    if not raw:
        return reference.year, True
    y = int(raw)
    return (2000 + y if y < 100 else y), False


def find_date(text: str, reference: date, order: str = "DMY") -> FoundDate | None:
    """Find a written date. Missing years are taken from the reference date and flagged."""
    m = _NUMERIC_DATE.search(text)
    if m:
        a, b, c = m.group(1), m.group(2), m.group(3)
        try:
            if len(a) == 4:  # ISO-like 2026-10-01
                return FoundDate(date(int(a), int(b), int(c or 1)), False) if c else None
            year, inferred = _year(c, reference)
            day, month = (int(a), int(b)) if order == "DMY" else (int(b), int(a))
            return FoundDate(date(year, month, day), inferred)
        except ValueError:
            pass
    for regex, day_first in ((_TEXT_DATE, True), (_TEXT_DATE_US, False)):
        m = regex.search(text)
        if not m:
            continue
        day_raw, month_raw = (m.group(1), m.group(2)) if day_first else (m.group(2), m.group(1))
        month = _MONTHS.get(month_raw.lower())
        if not month:
            continue
        year, inferred = _year(m.group(3), reference)
        try:
            return FoundDate(date(year, month, int(day_raw)), inferred)
        except ValueError:
            continue
    return None


def parse_iso_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None

"""Loads and merges the vocabulary packs named in EXTRACTION_LANGUAGES.

Adding a market/language means adding a JSON file here; no code changes.
"""

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent

_MONTH_WORDS = {
    "jan", "january", "feb", "february", "mar", "march", "apr", "april", "may", "jun", "june",
    "jul", "july", "aug", "august", "sep", "sept", "september", "oct", "october", "nov",
    "november", "dec", "december",
}
_DAY_WORDS = {
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "mon", "tue", "wed", "thu", "fri", "sat", "sun",
    "litinin", "talata", "laraba", "alhamis", "juma'a", "jumma'a", "asabar", "lahadi",
    "page", "shafi", "date", "rana",
}


@dataclass
class Vocab:
    languages: list[str]
    type_phrases: list[tuple[str, str]] = field(default_factory=list)  # (phrase, TYPE)
    item_phrases: list[tuple[str, str]] = field(default_factory=list)  # (phrase, canonical)
    expense_phrases: list[tuple[str, str]] = field(default_factory=list)
    total_markers: set[str] = field(default_factory=set)
    units: set[str] = field(default_factory=set)
    thousand_words: set[str] = field(default_factory=set)
    stopwords: set[str] = field(default_factory=set)
    type_order: list[str] = field(default_factory=list)

    @property
    def keyword_words(self) -> set[str]:
        """Every single word that has a vocabulary meaning (so it is not a name)."""
        words: set[str] = set()
        for phrase, _ in self.type_phrases + self.item_phrases + self.expense_phrases:
            words.update(phrase.split())
        return (
            words | self.total_markers | self.units | self.thousand_words | self.stopwords
            | _MONTH_WORDS | _DAY_WORDS
        )


@lru_cache
def load_vocab(languages: tuple[str, ...]) -> Vocab:
    vocab = Vocab(languages=list(languages))
    for lang in languages:
        path = _DIR / f"{lang}.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for rtype, phrases in data.get("types", {}).items():
            if rtype not in vocab.type_order:
                vocab.type_order.append(rtype)
            vocab.type_phrases += [(p.lower(), rtype) for p in phrases]
        for canonical, phrases in data.get("items", {}).items():
            vocab.item_phrases += [(p.lower(), canonical) for p in phrases]
        for canonical, phrases in data.get("expense_categories", {}).items():
            vocab.expense_phrases += [(p.lower(), canonical) for p in phrases]
        vocab.total_markers |= {w.lower() for w in data.get("total_markers", [])}
        vocab.units |= {w.lower() for w in data.get("units", [])}
        vocab.thousand_words |= {w.lower() for w in data.get("thousand_words", [])}
        vocab.stopwords |= {w.lower() for w in data.get("stopwords", [])}
    return vocab

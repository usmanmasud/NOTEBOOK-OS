"""Provider interfaces for the READ (OCR / speech) and UNDERSTAND (LLM) stages.

Implementations can be swapped through configuration without touching the
pipeline. Every provider failure is raised as `ProviderUnavailable` carrying a
message that is safe to show to the trader.
"""

from dataclasses import dataclass, field
from typing import Protocol

OCR_UNAVAILABLE_MSG = (
    "Automatic reading is temporarily unavailable. You can enter the transaction manually."
)
VOICE_UNAVAILABLE_MSG = "Voice processing unavailable. Use typed entry."
LLM_UNAVAILABLE_MSG = "We could not interpret this entry automatically. Please retry or enter it manually."


class ProviderUnavailable(Exception):
    def __init__(self, user_message: str, detail: str = "") -> None:
        super().__init__(detail or user_message)
        self.user_message = user_message
        self.detail = detail


@dataclass
class BBox:
    """Bounding box as fractions (0..1) of the page width/height."""

    x: float
    y: float
    width: float
    height: float

    def to_dict(self) -> dict:
        return {"x": round(self.x, 4), "y": round(self.y, 4), "width": round(self.width, 4), "height": round(self.height, 4)}


@dataclass
class TextLine:
    index: int
    text: str
    confidence: float = 1.0
    bbox: BBox | None = None


@dataclass
class ReadPage:
    page_number: int = 1
    width: int | None = None
    height: int | None = None
    lines: list[TextLine] = field(default_factory=list)


@dataclass
class ReadResult:
    """Output of the READ stage: raw text plus structure."""

    pages: list[ReadPage]
    provider: str
    # True when the text came from a pre-recorded demo fixture rather than a live
    # model. Shown in the UI so a demo never misrepresents what happened.
    is_fixture: bool = False

    @property
    def text(self) -> str:
        return "\n".join(line.text for page in self.pages for line in page.lines)


class OCRProvider(Protocol):
    name: str

    def read_image(self, data: bytes, mime_type: str) -> ReadResult: ...


class SpeechProvider(Protocol):
    name: str

    def transcribe(self, data: bytes, mime_type: str) -> ReadResult: ...


class LLMProvider(Protocol):
    name: str

    def complete_json(self, system: str, user: str) -> str:
        """Return the raw model output, which should be a JSON document."""
        ...

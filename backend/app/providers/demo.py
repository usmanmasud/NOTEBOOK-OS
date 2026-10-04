"""Offline demo providers.

These do not run any model. They recognise the fictional sample files shipped in
`samples/` (by SHA-256) and return the pre-recorded reading for that file, so the
competition demo still works with no internet. Any other file is reported as
unavailable rather than guessed at. Results are labelled `is_fixture=True`.
"""

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings
from app.providers.base import (
    OCR_UNAVAILABLE_MSG,
    VOICE_UNAVAILABLE_MSG,
    BBox,
    ProviderUnavailable,
    ReadPage,
    ReadResult,
    TextLine,
)


@lru_cache
def _load_fixtures(folder: str, suffix: str) -> dict[str, dict]:
    fixtures: dict[str, dict] = {}
    root = Path(folder)
    if not root.exists():
        return fixtures
    for path in root.glob(f"*{suffix}"):
        data = json.loads(path.read_text(encoding="utf-8"))
        fixtures[data["sha256"]] = data
    return fixtures


def _pages_from_fixture(data: dict) -> list[ReadPage]:
    pages = []
    for page in data["pages"]:
        lines = [
            TextLine(
                index=i,
                text=line["text"],
                confidence=float(line.get("confidence", 1.0)),
                bbox=BBox(**line["bbox"]) if line.get("bbox") else None,
            )
            for i, line in enumerate(page["lines"])
        ]
        pages.append(
            ReadPage(
                page_number=int(page.get("page_number", 1)),
                width=page.get("width"),
                height=page.get("height"),
                lines=lines,
            )
        )
    return pages


class DemoOCRProvider:
    name = "demo-fixture"

    def read_image(self, data: bytes, mime_type: str) -> ReadResult:
        folder = str(Path(get_settings().samples_dir) / "notebooks")
        fixture = _load_fixtures(folder, ".ocr.json").get(hashlib.sha256(data).hexdigest())
        if fixture is None:
            raise ProviderUnavailable(OCR_UNAVAILABLE_MSG, "image is not a known demo sample")
        return ReadResult(pages=_pages_from_fixture(fixture), provider=self.name, is_fixture=True)


class DemoSpeechProvider:
    name = "demo-fixture"

    def transcribe(self, data: bytes, mime_type: str) -> ReadResult:
        folder = str(Path(get_settings().samples_dir) / "voice")
        fixture = _load_fixtures(folder, ".transcript.json").get(hashlib.sha256(data).hexdigest())
        if fixture is None:
            raise ProviderUnavailable(VOICE_UNAVAILABLE_MSG, "audio is not a known demo sample")
        lines = [
            TextLine(index=i, text=t, confidence=float(fixture.get("confidence", 0.9)))
            for i, t in enumerate(fixture["transcript"])
        ]
        return ReadResult(pages=[ReadPage(page_number=1, lines=lines)], provider=self.name, is_fixture=True)

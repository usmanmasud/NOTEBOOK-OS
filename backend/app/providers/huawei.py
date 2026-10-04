"""Huawei Cloud AI providers (OCR handwriting recognition, SIS speech, IAM auth).

These call the public Huawei Cloud REST APIs with an IAM token. They are wired in
through configuration (`OCR_PROVIDER=huawei`, `SPEECH_PROVIDER=huawei`).
Status: implemented against the documented API shapes; automated tests use mocked
HTTP responses. Validate with real credentials before relying on them in a demo.
"""

import base64
import re
import threading
import time

import httpx

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


class IAMTokenCache:
    """Fetches and caches a project-scoped IAM token (valid 24h; refreshed after 20h)."""

    def __init__(self) -> None:
        self._token: str | None = None
        self._expires = 0.0
        self._lock = threading.Lock()

    def get(self) -> str:
        with self._lock:
            if self._token and time.time() < self._expires:
                return self._token
            s = get_settings()
            if not (s.huawei_iam_user and s.huawei_iam_password and s.huawei_iam_domain):
                raise ProviderUnavailable(OCR_UNAVAILABLE_MSG, "Huawei IAM credentials not configured")
            body = {
                "auth": {
                    "identity": {
                        "methods": ["password"],
                        "password": {
                            "user": {
                                "name": s.huawei_iam_user,
                                "password": s.huawei_iam_password,
                                "domain": {"name": s.huawei_iam_domain},
                            }
                        },
                    },
                    "scope": {"project": {"name": s.huawei_region}},
                }
            }
            url = f"https://iam.{s.huawei_region}.myhuaweicloud.com/v3/auth/tokens"
            resp = httpx.post(url, json=body, timeout=15)
            if resp.status_code != 201 or "X-Subject-Token" not in resp.headers:
                raise ProviderUnavailable(OCR_UNAVAILABLE_MSG, f"IAM token request failed ({resp.status_code})")
            self._token = resp.headers["X-Subject-Token"]
            self._expires = time.time() + 20 * 3600
            return self._token


_iam = IAMTokenCache()


def _image_size(data: bytes) -> tuple[int, int] | None:
    try:
        from io import BytesIO

        from PIL import Image

        with Image.open(BytesIO(data)) as img:
            return img.size
    except Exception:
        return None


class HuaweiOCRProvider:
    """Huawei Cloud OCR `handwriting` API (falls back to `general-text` if configured)."""

    name = "huawei-ocr"

    def __init__(self, endpoint_kind: str = "handwriting", client: httpx.Client | None = None) -> None:
        self.endpoint_kind = endpoint_kind
        self.client = client or httpx.Client(timeout=30)

    def read_image(self, data: bytes, mime_type: str) -> ReadResult:
        s = get_settings()
        if not s.huawei_project_id:
            raise ProviderUnavailable(OCR_UNAVAILABLE_MSG, "HUAWEI_PROJECT_ID not configured")
        url = f"https://ocr.{s.huawei_region}.myhuaweicloud.com/v2/{s.huawei_project_id}/ocr/{self.endpoint_kind}"
        try:
            resp = self.client.post(
                url,
                headers={"X-Auth-Token": _iam.get(), "Content-Type": "application/json"},
                json={"image": base64.b64encode(data).decode(), "detect_direction": True},
            )
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(OCR_UNAVAILABLE_MSG, f"OCR request failed: {type(exc).__name__}") from exc
        if resp.status_code != 200:
            raise ProviderUnavailable(OCR_UNAVAILABLE_MSG, f"OCR returned HTTP {resp.status_code}")
        return parse_huawei_ocr(resp.json(), _image_size(data), self.name)


def parse_huawei_ocr(payload: dict, size: tuple[int, int] | None, provider: str) -> ReadResult:
    """Convert a Huawei OCR response (`result.words_block_list`) into lines with bboxes."""
    blocks = (payload.get("result") or {}).get("words_block_list") or []
    width, height = size or (None, None)
    lines: list[TextLine] = []
    for i, block in enumerate(blocks):
        text = str(block.get("words", "")).strip()
        if not text:
            continue
        bbox = None
        loc = block.get("location")
        if loc and width and height:
            xs = [p[0] for p in loc]
            ys = [p[1] for p in loc]
            bbox = BBox(min(xs) / width, min(ys) / height, (max(xs) - min(xs)) / width, (max(ys) - min(ys)) / height)
        lines.append(TextLine(index=len(lines), text=text, confidence=float(block.get("confidence", 0.8)), bbox=bbox))
    if not lines:
        raise ProviderUnavailable(OCR_UNAVAILABLE_MSG, "OCR returned no text")
    lines.sort(key=lambda ln: (ln.bbox.y if ln.bbox else 0))
    for i, line in enumerate(lines):
        line.index = i
    return ReadResult(pages=[ReadPage(page_number=1, width=width, height=height, lines=lines)], provider=provider)


class HuaweiSpeechProvider:
    """Huawei Cloud SIS short-audio recognition (audio up to ~1 minute)."""

    name = "huawei-sis"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=60)

    def transcribe(self, data: bytes, mime_type: str) -> ReadResult:
        s = get_settings()
        if not s.huawei_project_id:
            raise ProviderUnavailable(VOICE_UNAVAILABLE_MSG, "HUAWEI_PROJECT_ID not configured")
        fmt = {"audio/wav": "wav", "audio/x-wav": "wav", "audio/mpeg": "mp3"}.get(mime_type)
        if fmt is None:
            raise ProviderUnavailable(VOICE_UNAVAILABLE_MSG, f"unsupported audio format {mime_type} for SIS")
        url = f"https://sis-ext.{s.huawei_region}.myhuaweicloud.com/v1/{s.huawei_project_id}/asr/short-audio"
        body = {
            "config": {"audio_format": fmt, "property": f"{s.huawei_sis_language.split('_')[0]}_16k"},
            "data": base64.b64encode(data).decode(),
        }
        try:
            token = _iam.get()
        except ProviderUnavailable as exc:
            raise ProviderUnavailable(VOICE_UNAVAILABLE_MSG, exc.detail) from exc
        try:
            resp = self.client.post(url, headers={"X-Auth-Token": token}, json=body)
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(VOICE_UNAVAILABLE_MSG, f"SIS request failed: {type(exc).__name__}") from exc
        if resp.status_code != 200:
            raise ProviderUnavailable(VOICE_UNAVAILABLE_MSG, f"SIS returned HTTP {resp.status_code}")
        result = resp.json().get("result") or {}
        text = str(result.get("text", "")).strip()
        if not text:
            raise ProviderUnavailable(VOICE_UNAVAILABLE_MSG, "SIS returned empty transcript")
        score = float(result.get("score", 0.8))
        # Split into sentences without breaking decimals such as "1.5".
        sentences = [t.strip() for t in re.split(r"(?<!\d)[.?!](?!\d)", text) if t.strip()] or [text]
        lines = [TextLine(index=i, text=t, confidence=score) for i, t in enumerate(sentences)]
        return ReadResult(pages=[ReadPage(page_number=1, lines=lines)], provider=self.name)

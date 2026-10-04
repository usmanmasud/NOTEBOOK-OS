"""Builds the configured provider chains and runs them with graceful fallback."""

import logging
from collections.abc import Callable

from app.core.config import get_settings
from app.providers.base import (
    LLM_UNAVAILABLE_MSG,
    OCR_UNAVAILABLE_MSG,
    VOICE_UNAVAILABLE_MSG,
    LLMProvider,
    OCRProvider,
    ProviderUnavailable,
    ReadResult,
    SpeechProvider,
)

logger = logging.getLogger(__name__)

# Tests and the demo can override providers here.
_overrides: dict[str, list] = {}


def override(kind: str, providers: list | None) -> None:
    if providers is None:
        _overrides.pop(kind, None)
    else:
        _overrides[kind] = providers


def ocr_providers() -> list[OCRProvider]:
    if "ocr" in _overrides:
        return _overrides["ocr"]
    from app.providers.demo import DemoOCRProvider
    from app.providers.huawei import HuaweiOCRProvider

    s = get_settings()
    built: list[OCRProvider] = []
    for name in s.ocr_chain:
        if name == "huawei":
            built.append(HuaweiOCRProvider(s.huawei_ocr_endpoint))
        elif name == "demo":
            built.append(DemoOCRProvider())
    return built


def speech_providers() -> list[SpeechProvider]:
    if "speech" in _overrides:
        return _overrides["speech"]
    from app.providers.demo import DemoSpeechProvider
    from app.providers.huawei import HuaweiSpeechProvider

    built: list[SpeechProvider] = []
    for name in get_settings().speech_chain:
        if name == "huawei":
            built.append(HuaweiSpeechProvider())
        elif name == "demo":
            built.append(DemoSpeechProvider())
    return built


def llm_provider() -> LLMProvider | None:
    if "llm" in _overrides:
        return _overrides["llm"][0] if _overrides["llm"] else None
    if get_settings().llm_provider == "openai_compatible":
        from app.providers.llm import OpenAICompatibleLLMProvider

        return OpenAICompatibleLLMProvider()
    return None


def _run_chain(providers: list, call: Callable, empty_msg: str) -> ReadResult:
    last: ProviderUnavailable | None = None
    for provider in providers:
        try:
            return call(provider)
        except ProviderUnavailable as exc:
            logger.warning("provider %s unavailable: %s", provider.name, exc.detail or exc.user_message)
            last = exc
        except Exception:  # never let a provider bug take down processing
            logger.exception("provider %s failed", getattr(provider, "name", provider))
            last = ProviderUnavailable(empty_msg, "provider error")
    raise last or ProviderUnavailable(empty_msg, "no provider configured")


def read_image(data: bytes, mime_type: str) -> ReadResult:
    return _run_chain(ocr_providers(), lambda p: p.read_image(data, mime_type), OCR_UNAVAILABLE_MSG)


def transcribe(data: bytes, mime_type: str) -> ReadResult:
    return _run_chain(speech_providers(), lambda p: p.transcribe(data, mime_type), VOICE_UNAVAILABLE_MSG)


def provider_status() -> dict:
    s = get_settings()
    llm = s.llm_provider
    if llm == "openai_compatible" and not (s.llm_base_url and s.llm_model):
        llm += " (not configured" + (", using rules fallback)" if s.llm_fallback_to_rules else ")")
    return {"ok": True, "ocr": s.ocr_chain, "speech": s.speech_chain, "llm": llm}


__all__ = ["read_image", "transcribe", "llm_provider", "provider_status", "override", "LLM_UNAVAILABLE_MSG"]

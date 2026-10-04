"""UNDERSTAND stage: choose the interpreter and fall back safely."""

import logging
from datetime import date

from app.core.config import get_settings
from app.extraction.llm_interpreter import ExtractionError, LLMInterpreter
from app.extraction.rules import RuleBasedInterpreter
from app.extraction.types import Interpretation, SourceLine
from app.extraction.vocab import load_vocab
from app.providers import registry
from app.providers.base import LLM_UNAVAILABLE_MSG, ProviderUnavailable

logger = logging.getLogger(__name__)


def rules_interpreter() -> RuleBasedInterpreter:
    return RuleBasedInterpreter(load_vocab(tuple(get_settings().extraction_language_list)))


def interpret(lines: list[SourceLine], reference: date) -> Interpretation:
    settings = get_settings()
    order = settings.date_order
    provider = registry.llm_provider()
    if provider is None:
        return rules_interpreter().interpret(lines, reference, order)

    try:
        return LLMInterpreter(provider).interpret(lines, reference, order)
    except (ProviderUnavailable, ExtractionError) as exc:
        reason = getattr(exc, "detail", "") or str(exc)
        logger.warning("LLM interpretation failed: %s", reason)
        if not settings.llm_fallback_to_rules:
            raise ProviderUnavailable(LLM_UNAVAILABLE_MSG, reason) from exc
        result = rules_interpreter().interpret(lines, reference, order)
        result.fallback_reason = reason
        return result

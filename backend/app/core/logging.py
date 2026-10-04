"""Structured application logging.

Pipeline events are logged with `log_event` so they are easy to grep and ship
to Huawei Cloud LTS. Never pass OTP codes, tokens, passwords or API keys here.
"""

import json
import logging
import sys

_REDACT_KEYS = {"otp", "code", "token", "password", "api_key", "secret", "authorization"}


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if any(getattr(h, "_notebookos", False) for h in root.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    handler._notebookos = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    root.setLevel(level.upper())


def log_event(event: str, **fields) -> None:
    safe = {k: ("[redacted]" if k.lower() in _REDACT_KEYS else v) for k, v in fields.items()}
    logging.getLogger("notebookos.events").info("%s %s", event, json.dumps(safe, default=str))

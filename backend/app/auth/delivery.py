"""Delivery of one-time sign-in codes.

Only email (via Resend's HTTP API) is wired up. Codes are never logged.
"""

import html

import httpx

from app.core.config import get_settings
from app.core.logging import log_event


class DeliveryError(Exception):
    pass


def send_email_code(email: str, code: str, minutes: int) -> None:
    s = get_settings()
    if s.email_provider == "console":
        # Development only (refused by login_methods in production): never prints the code.
        log_event("otp_email_stub", delivery="console")
        return
    if s.email_provider != "resend" or not (s.resend_api_key and s.email_from):
        raise DeliveryError("email delivery is not configured")
    safe = html.escape(code)
    body = {
        "from": s.email_from,
        "to": [email],
        "subject": f"{code} is your {s.app_name} sign-in code",
        "text": (
            f"Your {s.app_name} sign-in code is {code}.\n\n"
            f"It expires in {minutes} minutes and can be used once. "
            "If you did not try to sign in, you can ignore this email."
        ),
        "html": (
            f"<p>Your {html.escape(s.app_name)} sign-in code is</p>"
            f'<p style="font-size:28px;font-weight:700;letter-spacing:6px;margin:12px 0">{safe}</p>'
            f"<p>It expires in {minutes} minutes and can be used once.</p>"
            '<p style="color:#666">If you did not try to sign in, you can ignore this email.</p>'
        ),
    }
    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            json=body,
            headers={"Authorization": f"Bearer {s.resend_api_key}"},
            timeout=15,
        )
    except httpx.HTTPError as exc:
        raise DeliveryError(f"email request failed: {type(exc).__name__}") from exc
    if resp.status_code >= 300:
        try:
            reason = resp.json().get("message", "")
        except Exception:
            reason = ""
        raise DeliveryError(f"email provider returned HTTP {resp.status_code} {reason}"[:300])

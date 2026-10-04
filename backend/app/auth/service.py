"""Phone + OTP authentication with short-lived opaque session tokens.

* OTP codes are stored only as salted hashes in the KV store, expire quickly and
  allow a limited number of attempts.
* Session tokens are random; only their SHA-256 hash is stored server-side.
* Codes and tokens are never logged.
"""

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.kv import get_kv
from app.core.logging import log_event
from app.models import User

PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def normalize_phone(raw: str) -> str:
    phone = re.sub(r"[\s\-()]", "", raw or "")
    if not PHONE_RE.match(phone):
        raise AuthError("Enter a valid phone number, including country code.", 422)
    return phone


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _phone_key(phone: str) -> str:
    # Keys use a hash so phone numbers are not readable in the cache.
    return _hash("phone:" + phone)[:32]


def mask_phone(phone: str) -> str:
    return phone[:4] + "*" * max(len(phone) - 6, 0) + phone[-2:]


@dataclass
class OtpRequestResult:
    expires_in: int
    dev_code: str | None = None


def request_otp(phone: str) -> OtpRequestResult:
    settings = get_settings()
    kv = get_kv()
    key = _phone_key(phone)

    sent = kv.incr(f"otp:rate:{key}", 3600)
    if sent > settings.rate_limit_otp_per_hour:
        raise AuthError("Too many codes requested. Please wait and try again.", 429)

    code = f"{secrets.randbelow(1_000_000):06d}"
    salt = secrets.token_hex(8)
    kv.set(f"otp:code:{key}", f"{salt}:{_hash(salt + code)}", settings.otp_ttl_seconds)
    kv.delete(f"otp:attempts:{key}")

    if settings.sms_provider == "console" and not settings.is_production:
        # Development convenience: never prints the code itself.
        log_event("otp_requested", phone=mask_phone(phone), delivery="console-stub")
    else:
        log_event("otp_requested", phone=mask_phone(phone), delivery=settings.sms_provider)
    # NOTE: production SMS delivery requires plugging an SMS gateway in here.

    return OtpRequestResult(
        expires_in=settings.otp_ttl_seconds,
        dev_code=code if settings.otp_dev_echo and not settings.is_production else None,
    )


def verify_otp(db: Session, phone: str, code: str) -> User:
    settings = get_settings()
    kv = get_kv()
    key = _phone_key(phone)

    attempts = kv.incr(f"otp:attempts:{key}", settings.otp_ttl_seconds)
    if attempts > settings.otp_max_attempts:
        kv.delete(f"otp:code:{key}")
        raise AuthError("Too many attempts. Request a new code.", 429)

    stored = kv.get(f"otp:code:{key}")
    if not stored:
        raise AuthError("This code has expired. Request a new one.", 400)
    salt, digest = stored.split(":", 1)
    if not hmac.compare_digest(digest, _hash(salt + (code or "").strip())):
        raise AuthError("That code is not correct.", 400)

    kv.delete(f"otp:code:{key}")
    kv.delete(f"otp:attempts:{key}")

    user = db.scalar(select(User).where(User.phone == phone))
    if user is None:
        user = User(phone=phone)
        db.add(user)
        db.commit()
        log_event("user_created", user_id=user.id)
    log_event("otp_verified", user_id=user.id)
    return user


def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    ttl = get_settings().session_ttl_minutes * 60
    get_kv().set(f"session:{_hash(token)}", user_id, ttl)
    return token


def resolve_session(token: str) -> str | None:
    if not token:
        return None
    return get_kv().get(f"session:{_hash(token)}")


def end_session(token: str) -> None:
    get_kv().delete(f"session:{_hash(token)}")


def get_or_create_demo_user(db: Session) -> User:
    settings = get_settings()
    user = db.scalar(select(User).where(User.phone == settings.demo_phone))
    if user is None:
        user = User(
            phone=settings.demo_phone,
            name=settings.demo_name,
            business_name="Demo Provisions Store (fictional)",
            is_demo=True,
        )
        db.add(user)
        db.commit()
    return user

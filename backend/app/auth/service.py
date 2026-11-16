"""Phone or email + OTP authentication with short-lived opaque session tokens.

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
from app.auth.delivery import DeliveryError, send_email_code
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


EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")


def normalize_email(raw: str) -> str:
    email = (raw or "").strip().lower()
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise AuthError("Enter a valid email address.", 422)
    return email


@dataclass(frozen=True)
class Identity:
    """Who is signing in: kind is "phone" or "email", value is normalized."""

    kind: str
    value: str

    @property
    def key(self) -> str:
        # Keys use a hash so phone numbers and emails are not readable in the cache.
        return _hash(f"{self.kind}:{self.value}")[:32]

    @property
    def masked(self) -> str:
        return mask_phone(self.value) if self.kind == "phone" else mask_email(self.value)


def identity_from(phone: str | None, email: str | None) -> Identity:
    if email:
        return Identity("email", normalize_email(email))
    return Identity("phone", normalize_phone(phone or ""))


def mask_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    return phone[:4] + "*" * max(len(phone) - 6, 0) + phone[-2:]


def mask_email(email: str | None) -> str | None:
    if not email:
        return None
    local, _, domain = email.partition("@")
    return f"{local[:2]}{'*' * max(len(local) - 2, 1)}@{domain}"


@dataclass
class OtpRequestResult:
    expires_in: int
    dev_code: str | None = None


def request_otp(who: Identity) -> OtpRequestResult:
    settings = get_settings()
    if who.kind not in settings.login_methods:
        label = "Email" if who.kind == "email" else "Phone"
        raise AuthError(f"{label} sign-in is not available right now.", 400)
    kv = get_kv()
    key = who.key

    sent = kv.incr(f"otp:rate:{key}", 3600)
    if sent > settings.rate_limit_otp_per_hour:
        raise AuthError("Too many codes requested. Please wait and try again.", 429)

    code = f"{secrets.randbelow(1_000_000):06d}"
    salt = secrets.token_hex(8)
    kv.set(f"otp:code:{key}", f"{salt}:{_hash(salt + code)}", settings.otp_ttl_seconds)
    kv.delete(f"otp:attempts:{key}")

    delivery = "dev-echo"
    if who.kind == "email" and settings.email_provider == "resend":
        try:
            send_email_code(who.value, code, max(settings.otp_ttl_seconds // 60, 1))
        except DeliveryError as exc:
            kv.delete(f"otp:code:{key}")
            log_event("otp_delivery_failed", to=who.masked, reason=str(exc))
            raise AuthError("We couldn't send the code right now. Please try again in a minute.", 503)
        delivery = "email"
    log_event("otp_requested", to=who.masked, delivery=delivery)

    return OtpRequestResult(
        expires_in=settings.otp_ttl_seconds,
        dev_code=code if settings.otp_dev_echo and not settings.is_production else None,
    )


def verify_otp(db: Session, who: Identity, code: str) -> User:
    settings = get_settings()
    kv = get_kv()
    key = who.key

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

    column = User.email if who.kind == "email" else User.phone
    user = db.scalar(select(User).where(column == who.value))
    if user is None:
        user = User(**{who.kind: who.value})
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

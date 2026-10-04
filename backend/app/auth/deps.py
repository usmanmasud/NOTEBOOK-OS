"""FastAPI dependencies for authentication and rate limiting."""

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.service import resolve_session
from app.core.db import get_db
from app.core.kv import get_kv
from app.models import User


def bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Please sign in.")
    return authorization.split(" ", 1)[1].strip()


def current_user(token: str = Depends(bearer_token), db: Session = Depends(get_db)) -> User:
    user_id = resolve_session(token)
    if not user_id:
        raise HTTPException(401, "Your session has expired. Please sign in again.")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(401, "Please sign in.")
    return user


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def rate_limit(bucket: str, limit: int, window_seconds: int, identity: str) -> None:
    count = get_kv().incr(f"rl:{bucket}:{identity}", window_seconds)
    if count > limit:
        raise HTTPException(429, "Too many requests. Please slow down and try again shortly.")

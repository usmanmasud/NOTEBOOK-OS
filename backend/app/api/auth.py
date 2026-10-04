from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.deps import bearer_token, client_ip, current_user, rate_limit
from app.core.config import get_settings
from app.core.db import get_db
from app.models import User
from app.schemas.requests import OtpRequest, OtpVerify, ProfileUpdate

router = APIRouter(prefix="/auth", tags=["auth"])


def user_out(user: User) -> dict:
    return {
        "id": user.id,
        "phone": service.mask_phone(user.phone),
        "name": user.name,
        "business_name": user.business_name,
        "is_demo": user.is_demo,
    }


@router.post("/request-otp")
def request_otp(body: OtpRequest, request: Request) -> dict:
    rate_limit("otp-ip", 20, 3600, client_ip(request))
    try:
        phone = service.normalize_phone(body.phone)
        result = service.request_otp(phone)
    except service.AuthError as exc:
        raise HTTPException(exc.status_code, exc.message)
    out = {"sent": True, "expires_in": result.expires_in}
    if result.dev_code:
        out["dev_code"] = result.dev_code  # development only; disabled in production
    return out


@router.post("/verify-otp")
def verify_otp(body: OtpVerify, request: Request, db: Session = Depends(get_db)) -> dict:
    rate_limit("verify-ip", 30, 3600, client_ip(request))
    try:
        phone = service.normalize_phone(body.phone)
        user = service.verify_otp(db, phone, body.code)
    except service.AuthError as exc:
        raise HTTPException(exc.status_code, exc.message)
    return {"token": service.create_session(user.id), "user": user_out(user)}


@router.post("/demo")
def demo_login(db: Session = Depends(get_db)) -> dict:
    if not get_settings().demo_mode:
        raise HTTPException(404, "Not found")
    user = service.get_or_create_demo_user(db)
    return {"token": service.create_session(user.id), "user": user_out(user)}


@router.post("/logout")
def logout(token: str = Depends(bearer_token)) -> dict:
    service.end_session(token)
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)) -> dict:
    return user_out(user)


@router.patch("/me")
def update_me(body: ProfileUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    for field in body.model_fields_set:
        setattr(user, field, (getattr(body, field) or "").strip() or None)
    db.commit()
    return user_out(user)

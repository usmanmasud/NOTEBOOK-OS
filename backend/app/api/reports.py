from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import client_ip, current_user, rate_limit
from app.core.db import get_db
from app.models import Report, ReportStatus, User
from app.reports import builder
from app.schemas.requests import ReportCreate

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", status_code=201)
def create_report(body: ReportCreate, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    try:
        report = builder.create_report(db, user, body.period_start, body.period_end, body.title, body.consent)
    except builder.ReportError as exc:
        raise HTTPException(422, str(exc))
    return builder.report_out(report)


@router.get("")
def list_reports(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[dict]:
    reports = db.scalars(select(Report).where(Report.user_id == user.id).order_by(Report.generated_at.desc()))
    return [builder.report_out(r) for r in reports]


@router.post("/{report_id}/revoke")
def revoke_report(report_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    report = db.get(Report, report_id)
    if report is None or report.user_id != user.id:
        raise HTTPException(404, "Report not found.")
    return builder.report_out(builder.revoke_report(db, report))


@router.get("/{share_token}")
def public_report(share_token: str, request: Request, db: Session = Depends(get_db)) -> dict:
    """Public, read-only. Missing and revoked links return the same 404."""
    rate_limit("public-report", 120, 60, client_ip(request))
    if len(share_token) < 20 or len(share_token) > 64:
        raise HTTPException(404, "This report link is not valid or has been revoked.")
    report = db.scalar(select(Report).where(Report.share_token == share_token))
    if report is None or report.status != ReportStatus.ACTIVE:
        raise HTTPException(404, "This report link is not valid or has been revoked.")
    return builder.public_report_out(report)

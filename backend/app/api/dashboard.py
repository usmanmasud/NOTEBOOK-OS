import datetime as dt
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.analytics.metrics import METRIC_LABELS, compute_metrics, contributing_records, detect_patterns, filter_period
from app.auth.deps import current_user
from app.core.db import get_db
from app.models import Record, RecordStatus, User
from app.provenance.trace import confirmed_records, record_out, to_rec

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _f(v):
    return float(v) if isinstance(v, Decimal) else v


def _jsonify(rows: list[dict]) -> list[dict]:
    return [{k: _f(v) for k, v in row.items()} for row in rows]


@router.get("")
def dashboard(
    start: dt.date | None = None,
    end: dt.date | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    records = confirmed_records(db, user.id)
    recs = [to_rec(r) for r in records]
    m = compute_metrics(recs, start, end)
    in_period = {r.id for r in filter_period(recs, start, end)}
    pending = db.query(Record).filter(
        Record.user_id == user.id, Record.status.in_([RecordStatus.NEEDS_REVIEW, RecordStatus.AI_EXTRACTED])
    ).count()
    return {
        "period": {"start": start.isoformat() if start else None, "end": end.isoformat() if end else None},
        "metrics": {
            key: {"label": label, "value": _f(getattr(m, key))} for key, label in METRIC_LABELS.items()
        },
        "debtors": [
            {"person": d.person, "credit_given": _f(d.credit_given), "repaid": _f(d.repaid), "outstanding": _f(d.outstanding)}
            for d in m.debtors
        ],
        "stock": _jsonify(m.stock),
        "items": _jsonify(m.items),
        "trend": _jsonify(m.trend),
        "trend_granularity": m.trend_granularity,
        "undated_records": m.undated_records,
        "recent": [record_out(r) for r in records if r.id in in_period][:10],
        "pending_review": pending,
        "patterns": detect_patterns(recs, dt.date.today()),
        "basis": "Calculated by NotebookOS from your confirmed records only.",
    }


@router.get("/evidence/{metric}")
def evidence(
    metric: str,
    person: str | None = None,
    start: dt.date | None = None,
    end: dt.date | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    if metric not in METRIC_LABELS:
        raise HTTPException(404, "Unknown metric.")
    records = confirmed_records(db, user.id)
    recs = [to_rec(r) for r in records]
    m = compute_metrics(recs, start, end)
    if metric == "outstanding_debt":
        upto = [r for r in recs if end is None or (r.date is not None and r.date <= end)]
        contributing = contributing_records(metric, upto, person)
        value = sum((d.outstanding for d in m.debtors if not person or d.person.lower() == person.lower()), Decimal(0))
    else:
        contributing = contributing_records(metric, filter_period(recs, start, end), person)
        value = getattr(m, metric) if not person else None
    ids = {r.id for r in contributing}
    return {
        "metric": metric,
        "label": METRIC_LABELS[metric],
        "value": _f(value) if value is not None else None,
        "person": person,
        "explanation": _explain(metric),
        "records": [record_out(r) for r in records if r.id in ids],
    }


def _explain(metric: str) -> str:
    return {
        "total_sales": "Sum of all confirmed SALE records.",
        "credit_given": "Sum of all confirmed DEBT records (goods or money given on credit).",
        "debt_collected": "Sum of all confirmed PAYMENT records (repayments received).",
        "outstanding_debt": "For each customer: credit given minus repayments (never below zero), added together.",
        "total_expenses": "Sum of all confirmed EXPENSE records.",
        "stock_purchases": "Sum of all confirmed RESTOCK records.",
        "net_cash_flow": "Sales + repayments received − expenses − stock purchases.",
        "transactions": "Number of confirmed records.",
    }[metric]

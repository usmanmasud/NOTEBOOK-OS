"""Business / lender report built from confirmed records only.

The report is a summary of confirmed, user-provided business records. It is not a
credit score and NotebookOS does not independently verify the trader's finances.
"""

import logging
import re
import secrets
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.analytics.metrics import Metrics, compute_metrics, filter_period
from app.core.config import get_settings
from app.core.logging import log_event
from app.models import Record, Report, ReportStatus, UploadType, User, utcnow
from app.provenance.trace import confirmed_records, to_rec

logger = logging.getLogger(__name__)

EVIDENCE_STATEMENT = (
    "This report summarises business records that the trader captured in NotebookOS from their own "
    "notebook pages, voice notes or typed entries, and personally reviewed and confirmed. Every figure "
    "is calculated by software from those confirmed records and each record is linked to its original "
    "source in the trader's account."
)
DISCLAIMER = (
    "This is not a credit score or an audited statement. NotebookOS does not independently verify the "
    "trader's finances, and the figures are only as accurate as the records the trader confirmed. "
    "Lenders should apply their own assessment."
)


def _f(value: Decimal) -> float:
    return float(value)


def money(value: Decimal, currency: str) -> str:
    symbol = {"NGN": "₦", "GHS": "GH₵", "KES": "KSh ", "INR": "₹", "BDT": "৳"}.get(currency, currency + " ")
    return f"{symbol}{value:,.0f}"


def template_narrative(m: Metrics, currency: str) -> str:
    parts = [
        f"Across {m.transactions} confirmed transactions, recorded sales were {money(m.total_sales, currency)} "
        f"and expenses were {money(m.total_expenses, currency)}."
    ]
    if m.stock_purchases:
        parts.append(f"Stock purchases came to {money(m.stock_purchases, currency)}.")
    if m.credit_given or m.outstanding_debt:
        parts.append(
            f"Customers took {money(m.credit_given, currency)} on credit and repaid "
            f"{money(m.debt_collected, currency)}; {money(m.outstanding_debt, currency)} is still owed."
        )
    if len(m.trend) >= 2:
        first, last = m.trend[0]["sales"], m.trend[-1]["sales"]
        if last > first:
            parts.append(f"Sales in the most recent {m.trend_granularity} recorded were higher than in the first.")
        elif last < first:
            parts.append(f"Sales in the most recent {m.trend_granularity} recorded were lower than in the first.")
    return " ".join(parts)


def _numbers_in(text: str) -> set[str]:
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


def llm_narrative(m: Metrics, currency: str, fallback: str) -> str:
    """Optionally let the LLM re-phrase the summary. Rejected if it introduces any new number."""
    from app.providers import registry

    provider = registry.llm_provider()
    if provider is None:
        return fallback
    try:
        raw = provider.complete_json(
            "Rewrite this business summary in two plain sentences for a lender. Do not add, change or "
            'compute any numbers. Respond as JSON: {"summary": "..."}',
            fallback,
        )
        import json

        text = str(json.loads(raw).get("summary", "")).strip()
    except Exception:
        return fallback
    if not text or not _numbers_in(text) <= _numbers_in(fallback):
        logger.info("LLM narrative rejected: introduced numbers not present in calculated metrics")
        return fallback
    return text


def build_snapshot(user: User, records: list[Record], start: date | None, end: date | None) -> dict:
    s = get_settings()
    recs = [to_rec(r) for r in records]
    m = compute_metrics(recs, start, end)
    in_period_ids = {r.id for r in filter_period(recs, start, end)}
    period_records = [r for r in records if r.id in in_period_ids]

    by_type: dict[str, dict] = {}
    for r in period_records:
        t = r.type.value if r.type else "OTHER"
        entry = by_type.setdefault(t, {"count": 0, "amount": Decimal("0")})
        entry["count"] += 1
        entry["amount"] += r.amount or Decimal("0")

    dates = sorted(r.date for r in period_records if r.date)
    uploads = {r.upload_id: r.upload for r in period_records}
    narrative = template_narrative(m, s.currency)

    return {
        "business_name": user.business_name or user.name or "Trader",
        "owner_name": user.name,
        "currency": s.currency,
        "locale": s.locale,
        "period": {"start": start.isoformat() if start else (dates[0].isoformat() if dates else None),
                   "end": end.isoformat() if end else (dates[-1].isoformat() if dates else None)},
        "metrics": {
            "total_sales": _f(m.total_sales),
            "total_expenses": _f(m.total_expenses),
            "stock_purchases": _f(m.stock_purchases),
            "credit_given": _f(m.credit_given),
            "debt_collected": _f(m.debt_collected),
            "outstanding_debt": _f(m.outstanding_debt),
            "net_cash_flow": _f(m.net_cash_flow),
            "transactions": m.transactions,
        },
        "repayment": {
            "customers_with_balance": sum(1 for d in m.debtors if d.outstanding > 0),
            "customers_fully_repaid": sum(1 for d in m.debtors if d.credit_given > 0 and d.outstanding == 0),
        },
        "activity": {
            "by_type": {k: {"count": v["count"], "amount": _f(v["amount"])} for k, v in sorted(by_type.items())},
            "first_date": dates[0].isoformat() if dates else None,
            "last_date": dates[-1].isoformat() if dates else None,
            "active_days": len(set(dates)),
            "undated_records": m.undated_records,
        },
        "trend": [
            {"period": p["period"], "sales": _f(p["sales"]), "expenses": _f(p["expenses"])} for p in m.trend
        ],
        "trend_granularity": m.trend_granularity,
        "sources": {
            "notebook_photos": sum(1 for u in uploads.values() if u.type == UploadType.PHOTO),
            "voice_notes": sum(1 for u in uploads.values() if u.type == UploadType.VOICE),
            "typed_entries": sum(1 for u in uploads.values() if u.type == UploadType.TEXT),
            "records_corrected_by_trader": sum(1 for r in period_records if r.edited),
            "records_entered_manually": sum(1 for r in period_records if r.ai_original is None),
            "records_preloaded_demo_history": sum(
                1 for r in period_records if (r.upload.pipeline_info or {}).get("seeded_demo_history")
            ),
        },
        "narrative": llm_narrative(m, s.currency, narrative),
        "evidence_statement": EVIDENCE_STATEMENT,
        "disclaimer": DISCLAIMER,
    }


class ReportError(Exception):
    pass


def create_report(db: Session, user: User, start: date | None, end: date | None, title: str | None, consent: bool) -> Report:
    if not consent:
        raise ReportError("Please confirm you agree to share this information before generating a report.")
    if start and end and start > end:
        raise ReportError("The start date must be before the end date.")
    records = confirmed_records(db, user.id)
    if not records:
        raise ReportError("Confirm at least one record before generating a report.")
    snapshot = build_snapshot(user, records, start, end)
    report = Report(
        user_id=user.id,
        title=(title or f"Business summary — {snapshot['business_name']}")[:200],
        summary=snapshot["narrative"],
        period_start=start,
        period_end=end,
        snapshot=snapshot,
        share_token=secrets.token_urlsafe(24),
        status=ReportStatus.ACTIVE,
    )
    db.add(report)
    db.commit()
    log_event("report_generated", report_id=report.id, records=snapshot["metrics"]["transactions"])
    return report


def revoke_report(db: Session, report: Report) -> Report:
    report.status = ReportStatus.REVOKED
    report.revoked_at = utcnow()
    db.commit()
    log_event("report_revoked", report_id=report.id)
    return report


def report_out(report: Report, include_token: bool = True) -> dict:
    s = get_settings()
    out = {
        "id": report.id,
        "title": report.title,
        "status": report.status.value,
        "generated_at": report.generated_at.isoformat(),
        "revoked_at": report.revoked_at.isoformat() if report.revoked_at else None,
        "snapshot": report.snapshot,
    }
    if include_token:
        out["share_token"] = report.share_token
        out["share_url"] = f"{s.public_base_url.rstrip('/')}/reports/{report.share_token}"
    return out


def public_report_out(report: Report) -> dict:
    """Read-only public view: no internal IDs, no uploads, no debtor names."""
    return {
        "title": report.title,
        "generated_at": report.generated_at.isoformat(),
        "snapshot": report.snapshot,
    }

"""SUMMARIZE stage: business metrics computed by application code.

These functions are pure: they take already-confirmed records and return exact
Decimal figures. No LLM is involved in any number produced here.

Definitions (also in docs/ai-pipeline.md):
  total_sales       sum of SALE amounts (cash sales)
  credit_given      sum of DEBT amounts (goods/money given on credit)
  debt_collected    sum of PAYMENT amounts (repayments received)
  outstanding_debt  per person: max(DEBT - PAYMENT, 0), summed over people
  total_expenses    sum of EXPENSE amounts
  stock_purchases   sum of RESTOCK amounts
  net_cash_flow     total_sales + debt_collected - total_expenses - stock_purchases
"""

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from statistics import median

ZERO = Decimal("0")


@dataclass
class Rec:
    """Minimal view of a confirmed record used by analytics."""

    id: str
    type: str
    amount: Decimal
    date: dt.date | None = None
    person: str | None = None
    item: str | None = None
    quantity: Decimal | None = None


def person_key(name: str | None) -> str:
    return " ".join((name or "").lower().split())


@dataclass
class DebtorBalance:
    person: str
    credit_given: Decimal
    repaid: Decimal

    @property
    def outstanding(self) -> Decimal:
        return max(self.credit_given - self.repaid, ZERO)

    @property
    def overpaid(self) -> Decimal:
        return max(self.repaid - self.credit_given, ZERO)


@dataclass
class Metrics:
    total_sales: Decimal = ZERO
    credit_given: Decimal = ZERO
    debt_collected: Decimal = ZERO
    outstanding_debt: Decimal = ZERO
    total_expenses: Decimal = ZERO
    stock_purchases: Decimal = ZERO
    net_cash_flow: Decimal = ZERO
    transactions: int = 0
    undated_records: int = 0
    debtors: list[DebtorBalance] = field(default_factory=list)
    stock: list[dict] = field(default_factory=list)
    items: list[dict] = field(default_factory=list)
    trend: list[dict] = field(default_factory=list)
    trend_granularity: str = "day"


def _sum(records: list[Rec], rtype: str) -> Decimal:
    return sum((r.amount for r in records if r.type == rtype), ZERO)


def debtor_balances(records: list[Rec]) -> list[DebtorBalance]:
    names: dict[str, str] = {}
    given: dict[str, Decimal] = defaultdict(lambda: ZERO)
    repaid: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for r in records:
        if r.type not in ("DEBT", "PAYMENT") or not r.person:
            continue
        key = person_key(r.person)
        names.setdefault(key, r.person.strip())
        if r.type == "DEBT":
            given[key] += r.amount
        else:
            repaid[key] += r.amount
    balances = [DebtorBalance(names[k], given[k], repaid[k]) for k in names]
    return sorted(balances, key=lambda b: (-b.outstanding, b.person.lower()))


def filter_period(records: list[Rec], start: date | None, end: date | None) -> list[Rec]:
    """Records within [start, end]. With no period, every record (dated or not) counts."""
    if start is None and end is None:
        return list(records)
    return [
        r for r in records
        if r.date is not None and (start is None or r.date >= start) and (end is None or r.date <= end)
    ]


def compute_metrics(records: list[Rec], start: date | None = None, end: date | None = None) -> Metrics:
    in_period = filter_period(records, start, end)
    # Outstanding debt is a balance: everything up to the end of the period counts.
    upto_end = [r for r in records if end is None or (r.date is not None and r.date <= end)]

    m = Metrics()
    m.total_sales = _sum(in_period, "SALE")
    m.credit_given = _sum(in_period, "DEBT")
    m.debt_collected = _sum(in_period, "PAYMENT")
    m.total_expenses = _sum(in_period, "EXPENSE")
    m.stock_purchases = _sum(in_period, "RESTOCK")
    m.net_cash_flow = m.total_sales + m.debt_collected - m.total_expenses - m.stock_purchases
    m.transactions = len(in_period)
    m.undated_records = sum(1 for r in in_period if r.date is None)
    m.debtors = debtor_balances(upto_end)
    m.outstanding_debt = sum((b.outstanding for b in m.debtors), ZERO)
    m.stock = stock_movement(in_period)
    m.items = item_sales(in_period)
    m.trend, m.trend_granularity = trend(in_period)
    return m


def stock_movement(records: list[Rec]) -> list[dict]:
    moves: dict[str, dict] = {}
    for r in records:
        if not r.item or r.quantity is None or r.type not in ("RESTOCK", "SALE", "DEBT"):
            continue
        entry = moves.setdefault(r.item.strip().lower(), {"item": r.item.strip(), "in": ZERO, "out": ZERO})
        if r.type == "RESTOCK":
            entry["in"] += r.quantity
        else:
            entry["out"] += r.quantity
    for entry in moves.values():
        entry["net"] = entry["in"] - entry["out"]
    return sorted(moves.values(), key=lambda e: e["item"].lower())


def item_sales(records: list[Rec]) -> list[dict]:
    totals: dict[str, dict] = {}
    for r in records:
        if r.type not in ("SALE", "DEBT") or not r.item:
            continue
        entry = totals.setdefault(r.item.strip().lower(), {"item": r.item.strip(), "amount": ZERO, "count": 0})
        entry["amount"] += r.amount
        entry["count"] += 1
    return sorted(totals.values(), key=lambda e: -e["amount"])


def trend(records: list[Rec]) -> tuple[list[dict], str]:
    dated = [r for r in records if r.date is not None]
    if not dated:
        return [], "day"
    first, last = min(r.date for r in dated), max(r.date for r in dated)
    weekly = (last - first).days > 45

    def bucket(d: date) -> date:
        return d - timedelta(days=d.weekday()) if weekly else d

    series: dict[date, dict] = {}
    cursor, step = bucket(first), timedelta(days=7 if weekly else 1)
    while cursor <= bucket(last):
        series[cursor] = {"period": cursor.isoformat(), "sales": ZERO, "expenses": ZERO, "credit": ZERO, "collected": ZERO}
        cursor += step
    keys = {"SALE": "sales", "EXPENSE": "expenses", "DEBT": "credit", "PAYMENT": "collected"}
    for r in dated:
        if r.type in keys:
            series[bucket(r.date)][keys[r.type]] += r.amount
    return list(series.values()), "week" if weekly else "day"


def contributing_records(metric: str, records: list[Rec], person: str | None = None) -> list[Rec]:
    """The confirmed records that make up a metric (used by the evidence view)."""
    by_type = {
        "total_sales": {"SALE"},
        "credit_given": {"DEBT"},
        "debt_collected": {"PAYMENT"},
        "total_expenses": {"EXPENSE"},
        "stock_purchases": {"RESTOCK"},
        "net_cash_flow": {"SALE", "PAYMENT", "EXPENSE", "RESTOCK"},
        "transactions": None,
    }
    if metric == "outstanding_debt":
        owing = {person_key(b.person) for b in debtor_balances(records) if b.outstanding > 0}
        if person:
            owing &= {person_key(person)}
        return [r for r in records if r.type in ("DEBT", "PAYMENT") and person_key(r.person) in owing]
    if metric not in by_type:
        raise KeyError(metric)
    types = by_type[metric]
    selected = [r for r in records if types is None or r.type in types]
    if person:
        selected = [r for r in selected if person_key(r.person) == person_key(person)]
    return selected


METRIC_LABELS = {
    "total_sales": "Total Sales",
    "credit_given": "Credit Given",
    "debt_collected": "Debt Collected",
    "outstanding_debt": "Outstanding Debt",
    "total_expenses": "Expenses",
    "stock_purchases": "Stock Purchases",
    "net_cash_flow": "Net Cash Flow",
    "transactions": "Transactions",
}


def detect_patterns(records: list[Rec], today: date) -> list[dict]:
    """Simple, explainable patterns. Labelled "Pattern detected", never "risk" or "fraud"."""
    patterns: list[dict] = []
    expenses = [r for r in records if r.type == "EXPENSE"]
    if len(expenses) >= 5:
        mid = median(r.amount for r in expenses)
        for r in expenses:
            if mid > 0 and r.amount >= 3 * mid:
                patterns.append({
                    "kind": "high_expense",
                    "title": "Pattern detected: unusually high expense",
                    "detail": f"One expense is at least 3x your typical expense ({r.item or 'expense'}).",
                    "record_ids": [r.id],
                })

    dated = [r for r in records if r.date]
    for b in debtor_balances(records):
        if b.outstanding <= 0:
            continue
        debts = sorted((r for r in dated if r.type == "DEBT" and person_key(r.person) == person_key(b.person)), key=lambda r: r.date)
        if debts and (today - debts[0].date).days > 30:
            patterns.append({
                "kind": "debt_aging",
                "title": "Pattern detected: older unpaid credit",
                "detail": f"{b.person} has had an outstanding balance since {debts[0].date.isoformat()}.",
                "record_ids": [r.id for r in debts],
            })

    recent_start, prior_start = today - timedelta(days=14), today - timedelta(days=28)

    def window(rtype: str, lo: date, hi: date) -> Decimal:
        return sum((r.amount for r in dated if r.type == rtype and lo <= r.date < hi), ZERO)

    credit_now, credit_before = window("DEBT", recent_start, today + timedelta(days=1)), window("DEBT", prior_start, recent_start)
    paid_now, paid_before = window("PAYMENT", recent_start, today + timedelta(days=1)), window("PAYMENT", prior_start, recent_start)
    if credit_before > 0 and paid_before > 0 and credit_now > credit_before and paid_now < paid_before:
        patterns.append({
            "kind": "credit_up_collections_down",
            "title": "Pattern detected: more credit, fewer collections",
            "detail": "In the last 14 days credit given rose while repayments fell, compared with the 14 days before.",
            "record_ids": [],
        })
    return patterns

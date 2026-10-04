"""Deterministic analytics. No LLM is involved in any of these numbers."""

from datetime import date
from decimal import Decimal

from app.analytics.metrics import Rec, compute_metrics, contributing_records, detect_patterns

D = Decimal


def rec(i, type_, amount, person=None, day=None, item=None, qty=None):
    return Rec(id=str(i), type=type_, amount=D(amount), person=person, date=day, item=item,
               quantity=D(qty) if qty is not None else None)


def test_critical_financial_calculation():
    """Spec §34: Sale ₦100,000, Expense ₦20,000, Debt ₦40,000 -> computed by code."""
    records = [
        rec(1, "SALE", 100000),
        rec(2, "EXPENSE", 20000),
        rec(3, "DEBT", 40000, person="Musa"),
    ]
    m = compute_metrics(records)
    assert m.total_sales == D(100000)
    assert m.total_expenses == D(20000)
    assert m.outstanding_debt == D(40000)
    assert m.credit_given == D(40000)
    assert m.debt_collected == D(0)
    assert m.net_cash_flow == D(80000)
    assert m.transactions == 3


def test_outstanding_debt_is_per_person_and_never_negative():
    records = [
        rec(1, "DEBT", 20000, person="Musa"),
        rec(2, "DEBT", 20000, person="Aisha"),
        rec(3, "PAYMENT", 5000, person="musa "),  # same person, different spacing/case
        rec(4, "PAYMENT", 9000, person="Bello"),  # paid more than owed: not a negative debt
    ]
    m = compute_metrics(records)
    assert m.outstanding_debt == D(35000)
    assert m.debt_collected == D(14000)
    balances = {b.person: b for b in m.debtors}
    assert balances["Musa"].outstanding == D(15000)
    assert balances["Bello"].outstanding == D(0)
    assert balances["Bello"].overpaid == D(9000)


def test_sales_and_expense_sums_are_exact():
    records = [rec(i, "SALE", "1999.99") for i in range(3)] + [rec(9, "EXPENSE", "0.01")]
    m = compute_metrics(records)
    assert m.total_sales == D("5999.97")
    assert m.total_expenses == D("0.01")


def test_period_filter_and_balance_up_to_period_end():
    records = [
        rec(1, "SALE", 1000, day=date(2026, 9, 1)),
        rec(2, "SALE", 2000, day=date(2026, 10, 1)),
        rec(3, "DEBT", 5000, person="Musa", day=date(2026, 9, 2)),
        rec(4, "PAYMENT", 5000, person="Musa", day=date(2026, 10, 2)),
    ]
    sept = compute_metrics(records, date(2026, 9, 1), date(2026, 9, 30))
    assert sept.total_sales == D(1000)
    assert sept.outstanding_debt == D(5000)  # repaid only in October
    october = compute_metrics(records, date(2026, 10, 1), date(2026, 10, 31))
    assert october.total_sales == D(2000)
    assert october.outstanding_debt == D(0)


def test_stock_movement():
    records = [
        rec(1, "RESTOCK", 150000, item="Sugar", qty=5),
        rec(2, "SALE", 30000, item="Sugar", qty=1),
        rec(3, "DEBT", 30000, person="Musa", item="sugar", qty=1),
    ]
    stock = compute_metrics(records).stock
    assert stock == [{"item": "Sugar", "in": D(5), "out": D(2), "net": D(3)}]


def test_trend_is_daily_and_fills_gaps():
    records = [rec(1, "SALE", 100, day=date(2026, 10, 1)), rec(2, "SALE", 300, day=date(2026, 10, 3))]
    m = compute_metrics(records)
    assert [p["period"] for p in m.trend] == ["2026-10-01", "2026-10-02", "2026-10-03"]
    assert [p["sales"] for p in m.trend] == [D(100), D(0), D(300)]


def test_evidence_records_for_outstanding_debt_exclude_settled_people():
    records = [
        rec(1, "DEBT", 20000, person="Musa"),
        rec(2, "DEBT", 15000, person="Ibrahim"),
        rec(3, "PAYMENT", 15000, person="Ibrahim"),
        rec(4, "SALE", 5000),
    ]
    ids = {r.id for r in contributing_records("outstanding_debt", records)}
    assert ids == {"1"}
    assert {r.id for r in contributing_records("total_sales", records)} == {"4"}


def test_patterns_are_labelled_as_patterns_not_risk():
    records = [rec(i, "EXPENSE", 1000, day=date(2026, 10, 1)) for i in range(5)]
    records.append(rec(99, "EXPENSE", 9000, day=date(2026, 10, 2), item="Repairs"))
    records.append(rec(100, "DEBT", 5000, person="Musa", day=date(2026, 8, 1)))
    patterns = detect_patterns(records, date(2026, 10, 4))
    kinds = {p["kind"] for p in patterns}
    assert {"high_expense", "debt_aging"} <= kinds
    for p in patterns:
        assert p["title"].startswith("Pattern detected")
        assert "fraud" not in p["title"].lower() and "risk" not in p["title"].lower()

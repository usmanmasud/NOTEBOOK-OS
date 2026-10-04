import type { ReportSnapshot } from "../types";
import { dateTime, money, shortDate } from "../utils/format";

const TYPE_LABEL: Record<string, string> = {
  SALE: "Sales", DEBT: "Credit given", PAYMENT: "Repayments received", EXPENSE: "Expenses", RESTOCK: "Stock purchases", OTHER: "Other",
};

/** One-page business summary. Same component for the owner's view, print/PDF and the public link. */
export function ReportSheet({ title, generatedAt, s }: { title: string; generatedAt: string; s: ReportSnapshot }) {
  const figures: [string, number][] = [
    ["Total sales", s.metrics.total_sales],
    ["Expenses", s.metrics.total_expenses],
    ["Outstanding debt", s.metrics.outstanding_debt],
    ["Repayments received", s.metrics.debt_collected],
  ];
  const period = s.period.start || s.period.end
    ? `${shortDate(s.period.start)} – ${shortDate(s.period.end)}`
    : "All confirmed records";

  return (
    <article className="report-sheet">
      <p className="tiny">Business summary · generated {dateTime(generatedAt)}</p>
      <h1 style={{ marginTop: 6 }}>{s.business_name}</h1>
      {s.owner_name && s.owner_name !== s.business_name && <p className="muted">{s.owner_name}</p>}
      <p className="muted small" style={{ marginTop: 4 }}>{title} · Reporting period: {period}</p>

      <div className="report-figures">
        {figures.map(([label, value]) => (
          <div key={label}>
            <div className="label">{label}</div>
            <div className="value">{money(value)}</div>
          </div>
        ))}
      </div>

      <p style={{ marginBottom: 16 }}>{s.narrative}</p>

      <h3 style={{ marginBottom: 6 }}>Transaction summary</h3>
      <table className="data" style={{ marginBottom: 16 }}>
        <thead><tr><th>Type</th><th className="num">Entries</th><th className="num">Total</th></tr></thead>
        <tbody>
          {Object.entries(s.activity.by_type).map(([type, v]) => (
            <tr key={type}><td>{TYPE_LABEL[type] ?? type}</td><td className="num">{v.count}</td><td className="num">{money(v.amount)}</td></tr>
          ))}
          <tr><td><strong>Net cash flow</strong> <span className="tiny">(sales + repayments − expenses − stock)</span></td><td /><td className="num"><strong>{money(s.metrics.net_cash_flow)}</strong></td></tr>
        </tbody>
      </table>

      <div className="report-figures" style={{ marginTop: 0 }}>
        <div><div className="label">Transactions</div><div className="value">{s.metrics.transactions}</div></div>
        <div><div className="label">Active days</div><div className="value">{s.activity.active_days}</div></div>
        <div><div className="label">Customers owing</div><div className="value">{s.repayment.customers_with_balance}</div></div>
        <div><div className="label">Customers fully repaid</div><div className="value">{s.repayment.customers_fully_repaid}</div></div>
      </div>

      {s.trend.length > 1 && (
        <>
          <h3 style={{ marginBottom: 6 }}>Sales by {s.trend_granularity}</h3>
          <table className="data" style={{ marginBottom: 16 }}>
            <thead><tr><th>{s.trend_granularity === "week" ? "Week of" : "Date"}</th><th className="num">Sales</th><th className="num">Expenses</th></tr></thead>
            <tbody>
              {s.trend.filter((p) => p.sales || p.expenses).map((p) => (
                <tr key={p.period}><td>{shortDate(p.period)}</td><td className="num">{money(p.sales)}</td><td className="num">{money(p.expenses)}</td></tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <div className="report-box" style={{ marginBottom: 10 }}>
        <strong>Evidence.</strong> {s.evidence_statement} Sources: {s.sources.notebook_photos} notebook photo(s),{" "}
        {s.sources.voice_notes} voice note(s), {s.sources.typed_entries} typed entr{s.sources.typed_entries === 1 ? "y" : "ies"};{" "}
        {s.sources.records_corrected_by_trader} record(s) corrected and {s.sources.records_entered_manually} entered manually by the trader.
        {s.sources.records_preloaded_demo_history ? ` ${s.sources.records_preloaded_demo_history} record(s) are pre-loaded fictional demo history.` : ""}
      </div>
      <div className="report-box">
        <strong>Important.</strong> This report is a summary of confirmed user-provided business records. {s.disclaimer}
      </div>
    </article>
  );
}

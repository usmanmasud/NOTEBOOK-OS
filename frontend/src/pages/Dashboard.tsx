import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ColumnChart, HBarList } from "../components/Charts";
import { Icon, Loading, Notice } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { useI18n } from "../i18n";
import { api } from "../services/api";
import type { MetricKey } from "../types";
import { money, num, shortDate } from "../utils/format";

const TILES: MetricKey[] = ["total_sales", "outstanding_debt", "total_expenses", "stock_purchases", "debt_collected", "credit_given", "net_cash_flow", "transactions"];

export function Dashboard() {
  const { data, error, loading } = useAsync(() => api.dashboard(), []);
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useI18n();
  const [series, setSeries] = useState<"sales" | "expenses">("sales");
  const justConfirmed = (location.state as { justConfirmed?: string } | null)?.justConfirmed;

  if (loading && !data) return <Loading />;
  if (error || !data) return <Notice kind="error">{error ?? "Could not load the dashboard."}</Notice>;

  const m = data.metrics;
  const empty = m.transactions.value === 0;
  const open = (metric: MetricKey, person?: string) =>
    navigate(`/evidence/${metric}${person ? `?person=${encodeURIComponent(person)}` : ""}`);

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Dashboard</h1>
          <p>{data.basis} Tap any number to see where it came from.</p>
        </div>
      </div>

      {justConfirmed && <Notice kind="good">Records confirmed. Your dashboard is up to date.</Notice>}
      {data.pending_review > 0 && (
        <Notice kind="warn">
          {data.pending_review} record{data.pending_review === 1 ? " is" : "s are"} waiting for your review and not counted yet.{" "}
          <Link to="/records">Review now →</Link>
        </Notice>
      )}

      {empty ? (
        <div className="card empty">
          <h3>No confirmed records yet</h3>
          <p>Scan a notebook page or record a voice note, then confirm the results.</p>
          <p style={{ marginTop: 12 }}><Link className="btn btn-primary" to="/">Capture</Link></p>
        </div>
      ) : (
        <>
          <div className="stat-grid">
            {TILES.map((key) => (
              <button key={key} className={`stat ${key === "outstanding_debt" ? "featured" : ""}`} onClick={() => open(key)}
                aria-label={`${m[key].label}: ${key === "transactions" ? m[key].value : money(m[key].value)}. Show evidence`}>
                <span className="label">{m[key].label}</span>
                <span className="value">{key === "transactions" ? num(m[key].value) : money(m[key].value)}</span>
                <span className="trace"><Icon.trace /> See evidence</span>
              </button>
            ))}
          </div>

          <div className="grid-2">
            <section className="card">
              <div className="card-head">
                <h2>{series === "sales" ? "Sales" : "Expenses"} by {data.trend_granularity}</h2>
                <div className="seg" role="group" aria-label="Series">
                  <button aria-pressed={series === "sales"} onClick={() => setSeries("sales")}>Sales</button>
                  <button aria-pressed={series === "expenses"} onClick={() => setSeries("expenses")}>Expenses</button>
                </div>
              </div>
              {data.trend.length > 0 ? (
                <ColumnChart title={series === "sales" ? "Sales" : "Expenses"} granularity={data.trend_granularity}
                  points={data.trend.map((p) => ({ label: p.period, value: p[series] }))} />
              ) : (
                <p className="muted small">Add dates to your records to see a trend.</p>
              )}
              {data.undated_records > 0 && (
                <p className="tiny">{data.undated_records} record(s) without a date are not shown in this chart.</p>
              )}
            </section>

            <section className="card">
              <div className="card-head">
                <h2>Who owes you</h2>
                <button className="btn btn-sm btn-ghost" onClick={() => open("outstanding_debt")}>Evidence</button>
              </div>
              {data.debtors.filter((d) => d.outstanding > 0).length > 0 ? (
                <HBarList rows={data.debtors.filter((d) => d.outstanding > 0).map((d) => ({ label: d.person, value: d.outstanding }))}
                  onSelect={(person) => open("outstanding_debt", person)} />
              ) : (
                <p className="muted small">Nobody owes you money in your confirmed records.</p>
              )}
              {data.debtors.some((d) => d.outstanding === 0 && d.repaid > 0) && (
                <p className="tiny" style={{ marginTop: 8 }}>
                  Fully repaid: {data.debtors.filter((d) => d.outstanding === 0 && d.repaid > 0).map((d) => d.person).join(", ")}
                </p>
              )}
            </section>
          </div>

          {data.patterns.length > 0 && (
            <section className="card stack">
              <h2>Patterns</h2>
              {data.patterns.map((p, i) => (
                <div key={i} className="pattern">
                  <Icon.pattern />
                  <div>
                    <strong className="small">{p.title}</strong>
                    <p className="small muted">{p.detail}</p>
                  </div>
                </div>
              ))}
              <p className="tiny">Patterns are hints from your own records, not financial advice.</p>
            </section>
          )}

          <section className="card">
            <div className="card-head">
              <h2>Recent transactions</h2>
              <Link className="small" to="/records">All records</Link>
            </div>
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr><th>Date</th><th>Type</th><th>Details</th><th className="num">Amount</th><th>Source</th></tr>
                </thead>
                <tbody>
                  {data.recent.map((r) => (
                    <tr key={r.id}>
                      <td style={{ whiteSpace: "nowrap" }}>{shortDate(r.date).replace(/ \d{4}$/, "")}</td>
                      <td>{r.type ? t(`short.${r.type}`) : "—"}</td>
                      <td>{[r.person, r.item, r.quantity ? `× ${num(r.quantity)}` : null].filter(Boolean).join(" · ") || "—"}</td>
                      <td className="num">{money(r.amount)}</td>
                      <td><Link className="small" to={`/evidence/record/${r.id}`}>Trace</Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {(data.items.length > 0 || data.stock.length > 0) && (
            <div className="grid-2">
              {data.items.length > 0 && (
                <section className="card">
                  <h2 style={{ marginBottom: 12 }}>Items sold</h2>
                  <table className="data">
                    <thead><tr><th>Item</th><th className="num">Entries</th><th className="num">Value</th></tr></thead>
                    <tbody>
                      {data.items.map((i) => (
                        <tr key={i.item}><td>{i.item}</td><td className="num">{i.count}</td><td className="num">{money(i.amount)}</td></tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="tiny" style={{ marginTop: 6 }}>Includes cash sales and goods given on credit.</p>
                </section>
              )}
              {data.stock.length > 0 && (
                <section className="card">
                  <h2 style={{ marginBottom: 12 }}>Stock movement</h2>
                  <table className="data">
                    <thead><tr><th>Item</th><th className="num">In</th><th className="num">Out</th><th className="num">Net</th></tr></thead>
                    <tbody>
                      {data.stock.map((s) => (
                        <tr key={s.item}><td>{s.item}</td><td className="num">{num(s.in)}</td><td className="num">{num(s.out)}</td><td className="num">{num(s.net)}</td></tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="tiny" style={{ marginTop: 6 }}>Only records with a quantity are counted, in the units written. Opening stock is not recorded, so net can be negative.</p>
                </section>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

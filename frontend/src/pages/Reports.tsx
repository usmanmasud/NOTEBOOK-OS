import { useState } from "react";
import { useParams } from "react-router-dom";
import { BrandMark } from "../components/Layout";
import { ReportSheet } from "../components/ReportSheet";
import { Icon, Loading, Notice } from "../components/ui";
import { useApp } from "../hooks/useApp";
import { useAsync } from "../hooks/useAsync";
import { api, ApiError } from "../services/api";
import type { Report } from "../types";
import { dateTime } from "../utils/format";

export function Reports() {
  const { user, setUser } = useApp();
  const { data: reports, setData, loading } = useAsync(() => api.reports(), []);
  const [consent, setConsent] = useState(false);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [business, setBusiness] = useState(user?.business_name ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const current = reports?.[0];

  async function generate() {
    setBusy(true);
    setError(null);
    try {
      if (business.trim() && business.trim() !== user?.business_name) setUser(await api.updateMe({ business_name: business.trim() }));
      const r = await api.createReport({ consent, period_start: start || undefined, period_end: end || undefined });
      setData([r, ...(reports ?? [])]);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not generate the report.");
    } finally {
      setBusy(false);
    }
  }

  async function revoke(r: Report) {
    if (!window.confirm("Revoke this link? Anyone who has it will no longer be able to open the report.")) return;
    const updated = await api.revokeReport(r.id);
    setData((reports ?? []).map((x) => (x.id === r.id ? updated : x)));
  }

  async function copy(url: string) {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      window.prompt("Copy this link", url);
    }
  }

  return (
    <div className="stack">
      <div className="page-head no-print">
        <div>
          <h1>Business report</h1>
          <p>A one-page summary of your confirmed records, to keep or share with a lender.</p>
        </div>
      </div>

      <section className="card stack no-print">
        <div className="grid-2">
          <div className="field">
            <label htmlFor="biz">Business name on the report</label>
            <input id="biz" className="input" value={business} onChange={(e) => setBusiness(e.target.value)} maxLength={160} />
          </div>
          <div className="row" style={{ alignItems: "flex-end" }}>
            <div className="field" style={{ flex: 1 }}>
              <label htmlFor="start">From (optional)</label>
              <input id="start" className="input" type="date" value={start} onChange={(e) => setStart(e.target.value)} />
            </div>
            <div className="field" style={{ flex: 1 }}>
              <label htmlFor="end">To (optional)</label>
              <input id="end" className="input" type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
            </div>
          </div>
        </div>
        <label className="row small" style={{ alignItems: "flex-start", flexWrap: "nowrap" }}>
          <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} style={{ marginTop: 3 }} />
          <span>
            I understand this report contains information from the records I confirmed, and that anyone I give the share link to can
            read it. Customer names and my notebook photos are not included.
          </span>
        </label>
        {error && <Notice kind="error">{error}</Notice>}
        <div>
          <button className="btn btn-primary" onClick={generate} disabled={!consent || busy}>
            <Icon.doc /> {busy ? "Generating…" : "Generate report"}
          </button>
        </div>
      </section>

      {loading && !reports && <Loading />}

      {current && (
        <>
          <section className="card stack no-print">
            {current.status === "ACTIVE" ? (
              <>
                <div className="share-box">
                  <input className="input" readOnly value={current.share_url} aria-label="Share link" onFocus={(e) => e.target.select()} />
                  <button className="btn btn-sm" onClick={() => copy(current.share_url)}>
                    <Icon.link /> {copied ? "Copied" : "Copy share link"}
                  </button>
                </div>
                <div className="row">
                  <button className="btn btn-sm" onClick={() => window.print()}><Icon.printer /> Download PDF (print)</button>
                  <a className="btn btn-sm" href={current.share_url} target="_blank" rel="noreferrer">Open public view</a>
                  <button className="btn btn-sm btn-ghost btn-danger" onClick={() => revoke(current)}>Revoke link</button>
                </div>
                <p className="tiny">The link is read-only and needs no login. Revoke it at any time.</p>
              </>
            ) : (
              <Notice kind="warn">This report's share link was revoked {dateTime(current.revoked_at)}.</Notice>
            )}
          </section>
          <ReportSheet title={current.title} generatedAt={current.generated_at} s={current.snapshot} />
        </>
      )}

      {reports && reports.length > 1 && (
        <section className="card no-print">
          <h2 style={{ marginBottom: 10 }}>Earlier reports</h2>
          <table className="data">
            <tbody>
              {reports.slice(1).map((r) => (
                <tr key={r.id}>
                  <td>{dateTime(r.generated_at)}</td>
                  <td>{r.status === "ACTIVE" ? "Link active" : "Revoked"}</td>
                  <td className="num">
                    {r.status === "ACTIVE" && <button className="btn btn-sm btn-ghost btn-danger" onClick={() => revoke(r)}>Revoke</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}

/** Public read-only page at /reports/:token — no login, no internal IDs. */
export function PublicReport() {
  const { token = "" } = useParams();
  const { data, error, loading } = useAsync(() => api.publicReport(token), [token]);
  return (
    <div className="main">
      <div className="row no-print" style={{ justifyContent: "space-between", maxWidth: 820, margin: "0 auto 16px" }}>
        <span className="row" style={{ gap: 8, fontWeight: 700 }}><BrandMark /> NotebookOS</span>
        {data && <button className="btn btn-sm" onClick={() => window.print()}><Icon.printer /> Print / save PDF</button>}
      </div>
      {loading && !data && <Loading />}
      {error && (
        <div style={{ maxWidth: 520, margin: "0 auto" }}>
          <Notice kind="warn">{error}</Notice>
        </div>
      )}
      {data && <ReportSheet title={data.title} generatedAt={data.generated_at} s={data.snapshot} />}
      <p className="tiny no-print" style={{ textAlign: "center", marginTop: 16 }}>
        Read-only shared report. Figures come from records the business owner confirmed; NotebookOS does not verify them independently.
      </p>
    </div>
  );
}

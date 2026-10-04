import { Link, useParams, useSearchParams } from "react-router-dom";
import { SourceEvidence } from "../components/SourceEvidence";
import { ConfidenceBadge, FixtureBadge, Icon, Loading, Notice, StatusBadge } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { useI18n } from "../i18n";
import { api } from "../services/api";
import type { BusinessRecord, MetricKey } from "../types";
import { dateTime, money, num, percent, referenceLabel, shortDate } from "../utils/format";

/** Evidence for a dashboard metric: the number, its formula and every confirmed record behind it. */
export function MetricEvidence() {
  const { metric = "" } = useParams();
  const [params] = useSearchParams();
  const person = params.get("person");
  const { data, error, loading } = useAsync(() => api.evidence(metric as MetricKey, person), [metric, person]);

  if (loading && !data) return <Loading />;
  if (error || !data) return <Notice kind="error">{error ?? "Not found."}</Notice>;
  const isCount = data.metric === "transactions";

  return (
    <div className="stack">
      <Link to="/dashboard" className="tiny" style={{ textDecoration: "none" }}>← Dashboard</Link>
      <section className="card evidence-total">
        <span className="muted">{data.label}{person ? ` — ${person}` : ""}</span>
        <span className="big">{data.value === null ? "—" : isCount ? num(data.value) : money(data.value)}</span>
        <span className="small muted">{data.explanation}</span>
        <span className="small">
          Based on <strong>{data.records.length}</strong> confirmed record{data.records.length === 1 ? "" : "s"}. This number did not come from
          nowhere — each one is shown below with its original source.
        </span>
      </section>
      {data.records.length === 0 && <div className="card empty"><p>No confirmed records contribute to this number.</p></div>}
      {data.records.map((r) => <EvidenceItem key={r.id} record={r} />)}
    </div>
  );
}

/** Evidence for a single record. */
export function RecordEvidence() {
  const { recordId = "" } = useParams();
  const { data, error, loading } = useAsync(() => api.record(recordId), [recordId]);
  if (loading && !data) return <Loading />;
  if (error || !data) return <Notice kind="error">{error ?? "Not found."}</Notice>;
  return (
    <div className="stack">
      <Link to="/dashboard" className="tiny" style={{ textDecoration: "none" }}>← Dashboard</Link>
      <EvidenceItem record={data} />
    </div>
  );
}

export function EvidenceItem({ record: r }: { record: BusinessRecord }) {
  const { t } = useI18n();
  const s = r.source;
  const sourceName = s.upload_type === "PHOTO" ? `Notebook page ${s.page_number ?? ""}` : s.upload_type === "VOICE" ? "Voice note" : "Typed entry";
  const lines = s.original_text && s.reference && s.reference !== "manual-entry"
    ? [{ index: Number(s.reference.split("-row-")[1]) - 1, text: s.original_text, confidence: r.confidence, bbox: s.bbox }]
    : [];

  return (
    <article className="card evidence-item">
      <div className="stack" style={{ gap: 12 }}>
        <div className="row">
          <h2 style={{ marginRight: 4 }}>{r.person ?? r.item ?? (r.type ? t(`type.${r.type}`) : "Record")}</h2>
          <span style={{ fontSize: "1.15rem", fontWeight: 650 }}>{money(r.amount)}</span>
        </div>
        <div className="row">
          <span className="badge">{r.type ? t(`type.${r.type}`) : "—"}</span>
          <StatusBadge status={r.status} />
          <span className="tiny">{shortDate(r.date)}</span>
        </div>
        <ol className="trace-steps" aria-label="How this record was created">
          <li className="ok">
            <Icon.page />
            <span>
              <strong>Source:</strong> {sourceName}
              {s.reference && s.reference !== "manual-entry" ? `, ${referenceLabel(s.reference).replace(/^Page \d+, /, "")}` : ""}
              {r.manual_entry && " — typed by you"}
              {s.uploaded_at && <span className="tiny"> · uploaded {dateTime(s.uploaded_at)}</span>}
            </span>
          </li>
          {s.original_text && (
            <li className="ok">
              <Icon.info />
              <span>
                <strong>Original text:</strong> <span className="quote">“{s.original_text}”</span>{" "}
                <FixtureBadge show={s.read_is_demo_fixture} />
              </span>
            </li>
          )}
          {!r.manual_entry && (
            <li className="ok">
              <Icon.chart />
              <span>
                <strong>AI extraction:</strong> <ConfidenceBadge value={r.confidence} level={r.confidence_level} />
                {s.interpreted_by && <span className="tiny"> by {s.interpreted_by === "rules" ? "rule-based reader" : s.interpreted_by}</span>}
              </span>
            </li>
          )}
          {r.edited && (
            <li className="ok">
              <Icon.edit />
              <span>
                <strong>Corrected by trader:</strong>{" "}
                {r.human_fields.map((f) => {
                  const before = r.ai_original?.[f];
                  return `${t(`field.${f}` as never)} (AI read: ${before === null || before === undefined ? "unclear" : f === "amount" ? money(Number(before)) : String(before)})`;
                }).join(", ")}
              </span>
            </li>
          )}
          <li className={r.status === "CONFIRMED" ? "ok" : ""}>
            <Icon.check />
            <span>
              <strong>{r.status !== "CONFIRMED" ? "Not confirmed" : s.seeded_demo_history ? "Pre-confirmed demo history (loaded by the demo setup, not by a person)" : "Confirmed by trader"}</strong>
              {r.confirmed_at && <span className="tiny"> · {dateTime(r.confirmed_at)}</span>}
            </span>
          </li>
        </ol>
        {r.quantity !== null && <p className="small muted">Quantity: {num(r.quantity)}{r.item ? ` · ${r.item}` : ""}</p>}
        <Link className="small" to={`/uploads/${r.upload_id}`}>Open the full {s.upload_type === "PHOTO" ? "page" : "entry"} →</Link>
      </div>
      <div>
        {s.upload_type === "PHOTO" && s.has_image ? (
          <SourceEvidence uploadId={r.upload_id} uploadType="PHOTO" hasFile lines={[]} activeBox={s.bbox} />
        ) : s.upload_type === "PHOTO" ? (
          <p className="muted small">Original photo not available.</p>
        ) : (
          <SourceEvidence uploadId={r.upload_id} uploadType={s.upload_type} hasFile={s.upload_type === "VOICE"} lines={lines}
            activeLine={lines[0]?.index ?? null} />
        )}
        {s.bbox && <p className="tiny" style={{ marginTop: 6 }}>Highlighted: the line this record was read from ({percent(r.confidence)} confidence).</p>}
      </div>
    </article>
  );
}

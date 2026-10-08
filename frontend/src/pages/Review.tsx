import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { EditForm, RecordCard } from "../components/RecordCard";
import { SourceEvidence } from "../components/SourceEvidence";
import { FixtureBadge, Icon, Loading, Notice } from "../components/ui";
import { api, ApiError } from "../services/api";
import type { BusinessRecord, Upload } from "../types";
import { dateTime, money } from "../utils/format";

const ACTIVE = ["UPLOADED", "PROCESSING"];

export function Review() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [upload, setUpload] = useState<Upload | null>(null);
  const [records, setRecords] = useState<BusinessRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [activeLine, setActiveLine] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [pollKey, setPollKey] = useState(0);

  // Poll while the pipeline runs, then load the extracted records.
  useEffect(() => {
    let stop = false;
    let timer: ReturnType<typeof setTimeout>;
    async function tick() {
      try {
        const u = await api.upload(id);
        if (stop) return;
        if (ACTIVE.includes(u.status)) {
          setUpload(u);
          timer = setTimeout(tick, 900);
        } else {
          // Load the records before leaving the "Reading…" screen, so a slow
          // connection never shows a half-loaded page ("No transactions found").
          const rs = await api.uploadRecords(id);
          if (stop) return;
          setRecords(rs);
          setUpload(u);
        }
      } catch (e) {
        if (!stop) setError(e instanceof ApiError ? e.message : "Could not load this upload.");
      }
    }
    tick();
    return () => {
      stop = true;
      clearTimeout(timer);
    };
  }, [id, pollKey]);

  const refreshUpload = async () => setUpload(await api.upload(id));

  const recordLines = useMemo(() => {
    const m = new Map<number, { flagged: boolean }>();
    for (const r of records) {
      if (r.source.reference === "manual-entry") continue;
      const idx = Number(r.source.reference?.split("-row-")[1]) - 1;
      if (!Number.isNaN(idx)) m.set(idx, { flagged: r.status === "NEEDS_REVIEW" });
    }
    return m;
  }, [records]);

  const lineOf = (r: BusinessRecord) => Number(r.source.reference?.split("-row-")[1]) - 1;

  function updateRecord(next: BusinessRecord) {
    setRecords((rs) => rs.map((r) => (r.id === next.id ? next : r)));
    refreshUpload();
  }

  async function confirmAll() {
    setBusy(true);
    setConfirmError(null);
    try {
      await api.confirmUpload(id);
      navigate("/dashboard", { state: { justConfirmed: id } });
    } catch (e) {
      setConfirmError(e instanceof ApiError ? e.message : "Could not confirm.");
      setRecords(await api.uploadRecords(id));
    } finally {
      setBusy(false);
    }
  }

  async function retry() {
    setError(null);
    await api.retryUpload(id);
    setUpload(null);
    setRecords([]);
    setPollKey((k) => k + 1);
  }

  async function remove() {
    const confirmed = records.filter((r) => r.status === "CONFIRMED").length;
    const msg = confirmed
      ? `Delete this upload and its ${confirmed} confirmed record(s)? They will be removed from your dashboard.`
      : "Delete this upload and the original file?";
    if (!window.confirm(msg)) return;
    await api.deleteUpload(id);
    navigate("/records");
  }

  if (error) return <Notice kind="error">{error}</Notice>;
  if (!upload) return <Loading />;

  if (ACTIVE.includes(upload.status)) {
    return (
      <div className="card stack" style={{ maxWidth: 520, margin: "10vh auto" }}>
        <Loading label={upload.type === "VOICE" ? "Transcribing your voice note…" : upload.type === "PHOTO" ? "Reading your notebook page…" : "Reading your entry…"} />
        <p className="muted small" style={{ textAlign: "center" }}>
          Read → understand → check. Nothing is saved to your records until you confirm it.
        </p>
      </div>
    );
  }

  const pending = records.filter((r) => r.status === "NEEDS_REVIEW" || r.status === "AI_EXTRACTED");
  const blocking = pending.filter((r) => r.validation_issues.some((i) => i.severity === "error"));
  const flagged = pending.filter((r) => r.status === "NEEDS_REVIEW").length;
  const page = upload.pages?.[0];
  const p = upload.pipeline;

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <Link to="/records" className="tiny" style={{ textDecoration: "none" }}>← All records</Link>
          <h1 style={{ marginTop: 4 }}>
            {upload.type === "PHOTO" ? `Notebook page${page ? ` ${page.page_number}` : ""}` : upload.type === "VOICE" ? "Voice note" : "Typed entry"}
          </h1>
          <p>Check what the AI read. Fix anything highlighted, then confirm.</p>
        </div>
        <button className="btn btn-sm btn-ghost btn-danger" onClick={remove}>Delete upload</button>
      </div>

      {upload.status === "FAILED" ? (
        <Notice kind="warn">
          {upload.error_message}{" "}
          <button className="btn btn-sm" onClick={retry} style={{ marginLeft: 8 }}>Try again</button>
        </Notice>
      ) : (
        <div className="pipeline-steps" aria-label="Processing steps">
          <span><Icon.check /> Read{p.read_provider ? ` (${p.read_provider})` : ""}</span>
          <span><Icon.check /> Understood ({p.interpreter === "rules" ? "rule-based" : p.interpreter})</span>
          <span><Icon.check /> Checked · {p.records_extracted ?? 0} found, {p.records_flagged ?? 0} flagged</span>
          <FixtureBadge show={p.read_is_demo_fixture} />
          {p.seeded_demo_history && <span className="badge fixture">Seeded demo history</span>}
          <span className="tiny">· {dateTime(upload.created_at)}</span>
        </div>
      )}
      {p.interpreter_fallback_reason && (
        <Notice kind="info">The AI model was unavailable, so the built-in rule-based reader was used.</Notice>
      )}
      {p.total_checks?.map((c) =>
        c.matches ? (
          <Notice key={c.reference} kind="good">
            The total written on the page ({money(Number(c.written_total))}) matches the sales found.
          </Notice>
        ) : (
          <Notice key={c.reference} kind="warn">
            The total written on the page is {money(Number(c.written_total))}, but the sales found add up to{" "}
            {money(Number(c.extracted_sales))}. A line may be missing or misread.
          </Notice>
        ),
      )}

      <div className="review-layout">
        <section className="sticky stack" aria-label="Original evidence">
          <div className="section-title">Original evidence</div>
          <SourceEvidence
            uploadId={upload.id}
            uploadType={upload.type}
            hasFile={upload.has_file}
            lines={page?.lines ?? []}
            recordLines={recordLines}
            activeLine={activeLine}
            onSelectLine={setActiveLine}
          />
          {upload.type === "PHOTO" && page && page.lines.length > 0 && (
            <p className="tiny">Boxes show each line the AI read. Tap one to find its record.</p>
          )}
        </section>

        <section className="stack" aria-label="Extracted records">
          <div className="section-title">Extracted records ({records.length})</div>
          {records.length === 0 && upload.status !== "FAILED" && (
            <div className="empty">
              <h3>No transactions found</h3>
              <p>Add them yourself below.</p>
            </div>
          )}
          {records.map((r) => (
            <RecordCard key={r.id} record={r} active={activeLine !== null && lineOf(r) === activeLine}
              onFocus={() => setActiveLine(lineOf(r))} onChange={updateRecord} />
          ))}

          {adding ? (
            <div className="record-card">
              <h3>Add a transaction</h3>
              <EditForm busy={busy} submitLabel="Add" onCancel={() => setAdding(false)}
                onSave={async (fields) => {
                  setBusy(true);
                  try {
                    const r = await api.addRecord(upload.id, fields);
                    setRecords((rs) => [...rs, r]);
                    setAdding(false);
                    refreshUpload();
                  } catch (e) {
                    setConfirmError(e instanceof ApiError ? e.message : "Could not add.");
                  } finally {
                    setBusy(false);
                  }
                }} />
            </div>
          ) : (
            <button className="btn" onClick={() => setAdding(true)}>
              <Icon.keyboard /> {upload.status === "FAILED" ? "Enter transactions manually" : "Add a missing transaction"}
            </button>
          )}
        </section>
      </div>

      {pending.length > 0 && (
        <div className="confirm-bar">
          <div className="small">
            {blocking.length > 0 ? (
              <span style={{ color: "var(--crit-text)" }}><strong>{blocking.length}</strong> record(s) need a value before confirming.</span>
            ) : flagged > 0 ? (
              <span><strong>{flagged}</strong> highlighted — please check them.</span>
            ) : (
              <span>All records look clear.</span>
            )}
            {confirmError && <div style={{ color: "var(--crit-text)" }}>{confirmError}</div>}
          </div>
          <span className="spacer" />
          <button className="btn btn-primary" onClick={confirmAll} disabled={busy || blocking.length > 0}>
            <Icon.check /> Confirm {pending.length} record{pending.length === 1 ? "" : "s"}
          </button>
        </div>
      )}
      {pending.length === 0 && records.some((r) => r.status === "CONFIRMED") && (
        <Notice kind="good">
          All records on this page are confirmed. <Link to="/dashboard">See your dashboard →</Link>
        </Notice>
      )}
    </div>
  );
}

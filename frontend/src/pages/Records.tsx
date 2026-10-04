import { Link } from "react-router-dom";
import { Icon, Loading, Notice } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { api } from "../services/api";
import type { Upload } from "../types";
import { dateTime } from "../utils/format";

const STATUS_TEXT: Record<Upload["status"], string> = {
  UPLOADED: "Uploaded",
  PROCESSING: "Reading…",
  REVIEW: "Needs your review",
  CONFIRMED: "Confirmed",
  FAILED: "Couldn’t read — enter manually",
};

export function Records() {
  const { data, error, loading } = useAsync(() => api.uploads(), []);
  if (loading && !data) return <Loading />;
  if (error || !data) return <Notice kind="error">{error ?? "Could not load."}</Notice>;

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Records</h1>
          <p>Every notebook page, voice note and typed entry, with its review status.</p>
        </div>
        <Link className="btn btn-primary btn-sm" to="/">Capture</Link>
      </div>
      {data.length === 0 && (
        <div className="card empty"><h3>Nothing captured yet</h3><p>Scan a notebook page to get started.</p></div>
      )}
      <div className="stack" style={{ gap: 8 }}>
        {data.map((u) => {
          const c = u.record_counts;
          const pending = c.NEEDS_REVIEW + c.AI_EXTRACTED;
          const I = u.type === "PHOTO" ? Icon.page : u.type === "VOICE" ? Icon.mic : Icon.keyboard;
          return (
            <Link key={u.id} to={`/uploads/${u.id}`} className="card row" style={{ textDecoration: "none", padding: 14 }}>
              <I width={22} height={22} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <strong className="small">
                  {u.type === "PHOTO" ? "Notebook photo" : u.type === "VOICE" ? "Voice note" : "Typed entry"}
                  {u.pipeline.seeded_demo_history ? " · seeded demo history" : ""}
                </strong>
                <div className="tiny">
                  {dateTime(u.created_at)} · {c.CONFIRMED} confirmed{pending ? ` · ${pending} to review` : ""}
                  {c.REJECTED ? ` · ${c.REJECTED} rejected` : ""}
                </div>
              </div>
              <span className={`badge ${u.status === "CONFIRMED" ? "confirmed" : u.status === "FAILED" ? "low" : u.status === "REVIEW" ? "review" : ""}`}>
                {u.status === "CONFIRMED" ? <Icon.check /> : <Icon.dot />} {STATUS_TEXT[u.status]}
              </span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

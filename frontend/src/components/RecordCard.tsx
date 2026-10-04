import { useState, type FormEvent } from "react";
import { useApp } from "../hooks/useApp";
import { useI18n } from "../i18n";
import { api, ApiError } from "../services/api";
import type { BusinessRecord, EditableFields, RecordType } from "../types";
import { money, num, percent, referenceLabel, shortDate } from "../utils/format";
import { ConfidenceBadge, Icon, StatusBadge } from "./ui";

export const RECORD_TYPES: RecordType[] = ["SALE", "DEBT", "PAYMENT", "EXPENSE", "RESTOCK", "OTHER"];
const FIELDS = ["type", "amount", "person", "item", "quantity", "date"] as const;
type Field = (typeof FIELDS)[number];

export type Flag = "error" | "low" | "review" | "human" | null;

/** Why a field is highlighted. Errors block confirmation; low/review are AI uncertainty. */
export function fieldFlag(record: BusinessRecord, field: string, thresholds: { high: number; review: number }): Flag {
  if (record.validation_issues.some((i) => i.field === field && i.severity === "error")) return "error";
  if (record.human_fields.includes(field) && !record.manual_entry) return "human";
  const c = record.field_confidence[field];
  if (c === undefined) return null;
  // A null value with a confidence means the AI saw something but could not read it.
  if ((record as unknown as Record<string, unknown>)[field] === null) return c < thresholds.review ? "low" : null;
  if (c < thresholds.review) return "low";
  if (c < thresholds.high) return "review";
  return null;
}

function display(record: BusinessRecord, field: Field, t: (k: never) => string): string | null {
  const v = record[field];
  if (v === null || v === undefined || v === "") return null;
  if (field === "amount") return money(v as number);
  if (field === "quantity") return num(v as number);
  if (field === "date") return shortDate(v as string);
  if (field === "type") return t(`type.${v}` as never);
  return String(v);
}

interface Props {
  record: BusinessRecord;
  active?: boolean;
  onFocus?: () => void;
  onChange: (r: BusinessRecord) => void;
}

export function RecordCard({ record, active, onFocus, onChange }: Props) {
  const { config } = useApp();
  const { t } = useI18n();
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const done = record.status === "CONFIRMED" || record.status === "REJECTED";

  async function act(fn: () => Promise<BusinessRecord>) {
    setBusy(true);
    setError(null);
    try {
      onChange(await fn());
      setEditing(false);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not save. Try again.");
    } finally {
      setBusy(false);
    }
  }

  const issues = record.validation_issues;
  return (
    <article
      className={`record-card status-${record.status} ${active ? "active" : ""}`}
      onClick={onFocus}
      aria-label={`Record from ${referenceLabel(record.source.reference)}`}
    >
      <div className="record-head">
        <StatusBadge status={record.status} />
        {!record.manual_entry && <ConfidenceBadge value={record.confidence} level={record.confidence_level} />}
        {record.edited && <span className="badge high"><Icon.edit /> Corrected by you</span>}
        <span className="spacer" />
        <span className="tiny">{referenceLabel(record.source.reference)}</span>
      </div>

      {record.source.original_text && (
        <div>
          <span className="tiny">Read from notebook: </span>
          <span className="quote">“{record.source.original_text}”</span>
        </div>
      )}

      {!editing ? (
        <div className="record-summary">
          {FIELDS.map((f) => {
            const flag = fieldFlag(record, f, config.confidence);
            const value = display(record, f, t as never);
            // Optional fields that are simply absent are hidden; unclear ones are shown and flagged.
            if (value === null && !flag && f !== "type" && f !== "amount") return null;
            const conf = record.field_confidence[f];
            return (
              <div key={f} className={`kv ${flag && flag !== "human" ? `flag-${flag}` : ""}`}>
                <span className="k">{t(`field.${f}` as never)}</span>
                <span className={`v ${value === null ? "empty-v" : ""}`}>{value ?? (flag === "error" ? "Missing — please fill in" : "Unclear — please check")}</span>
                {flag === "low" || flag === "review" ? (
                  <span className={`field-hint ${flag}`}>
                    <Icon.alert width={12} /> {value === null ? "Couldn’t read clearly" : `AI unsure · ${percent(conf)}`}
                  </span>
                ) : flag === "human" ? (
                  <span className="field-hint human">
                    <Icon.check width={12} /> You set this
                  </span>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : (
        <EditForm record={record} busy={busy} onCancel={() => setEditing(false)}
          onSave={(changes) => act(() => api.updateRecord(record.id, changes))} />
      )}

      {issues.length > 0 && !editing && record.status !== "REJECTED" && (
        <ul className="issues">
          {issues.map((i, n) => (
            <li key={n} className={i.severity}>
              {i.severity === "error" ? <Icon.x /> : <Icon.alert />}
              <span>
                <strong>{t(`field.${i.field}` as never) || i.field}:</strong> {i.message}
              </span>
            </li>
          ))}
        </ul>
      )}
      {error && <p className="small" style={{ color: "var(--crit-text)" }} role="alert">{error}</p>}

      {!editing && (
        <div className="row">
          {record.status !== "CONFIRMED" && (
            <button className="btn btn-sm btn-primary" disabled={busy}
              onClick={(e) => { e.stopPropagation(); act(() => api.confirmRecord(record.id)); }}>
              <Icon.check /> {t("action.confirm")}
            </button>
          )}
          <button className="btn btn-sm" disabled={busy} onClick={(e) => { e.stopPropagation(); setEditing(true); }}>
            <Icon.edit /> {t("action.edit")}
          </button>
          {record.status !== "REJECTED" && (
            <button className="btn btn-sm btn-ghost btn-danger" disabled={busy}
              onClick={(e) => { e.stopPropagation(); act(() => api.rejectRecord(record.id)); }}>
              <Icon.x /> {t("action.reject")}
            </button>
          )}
          {done && record.status === "CONFIRMED" && <span className="tiny">Counts towards your dashboard.</span>}
        </div>
      )}
    </article>
  );
}

export function EditForm({
  record, busy, onSave, onCancel, submitLabel,
}: {
  record?: BusinessRecord;
  busy: boolean;
  onSave: (changes: EditableFields) => void;
  onCancel?: () => void;
  submitLabel?: string;
}) {
  const { config } = useApp();
  const { t } = useI18n();
  const [form, setForm] = useState({
    type: record?.type ?? "",
    amount: record?.amount?.toString() ?? "",
    person: record?.person ?? "",
    item: record?.item ?? "",
    quantity: record?.quantity?.toString() ?? "",
    date: record?.date ?? "",
    notes: record?.notes ?? "",
  });
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });

  function submit(e: FormEvent) {
    e.preventDefault();
    const out: Record<string, unknown> = {};
    const original: Record<string, unknown> = record ? { ...record } : {};
    for (const [k, raw] of Object.entries(form)) {
      const v = raw.trim();
      let value: unknown = v === "" ? null : v;
      if (k === "quantity" && value !== null) value = Number(value);
      const before = original[k] ?? null;
      if (record && String(before ?? "") === String(value ?? "")) continue;
      if (!record && value === null) continue;
      out[k] = value;
    }
    onSave(out as EditableFields);
  }

  const cls = (f: Field) => {
    const flag = record ? fieldFlag(record, f, config.confidence) : null;
    return `field ${flag && flag !== "human" ? `flag-${flag}` : ""}`;
  };
  const uid = record?.id ?? "new";

  return (
    <form className="edit-grid" onSubmit={submit} onClick={(e) => e.stopPropagation()}>
      <div className={cls("type")}>
        <label htmlFor={`type-${uid}`}>{t("field.type")}</label>
        <select id={`type-${uid}`} className="input" value={form.type} onChange={set("type")} required>
          <option value="">Choose…</option>
          {RECORD_TYPES.map((rt) => (
            <option key={rt} value={rt}>{t(`type.${rt}`)}</option>
          ))}
        </select>
      </div>
      <div className={cls("amount")}>
        <label htmlFor={`amount-${uid}`}>{t("field.amount")} ({config.currency})</label>
        <input id={`amount-${uid}`} className="input" inputMode="decimal" placeholder="e.g. 20000 or 20k"
          value={form.amount} onChange={set("amount")} required />
      </div>
      <div className={cls("person")}>
        <label htmlFor={`person-${uid}`}>{t("field.person")}</label>
        <input id={`person-${uid}`} className="input" value={form.person} onChange={set("person")}
          placeholder={form.type === "DEBT" || form.type === "PAYMENT" ? "Required for debts" : "Optional"} />
      </div>
      <div className={cls("item")}>
        <label htmlFor={`item-${uid}`}>{t("field.item")}</label>
        <input id={`item-${uid}`} className="input" value={form.item} onChange={set("item")} />
      </div>
      <div className={cls("quantity")}>
        <label htmlFor={`qty-${uid}`}>{t("field.quantity")}</label>
        <input id={`qty-${uid}`} className="input" type="number" min="0" step="any" value={form.quantity} onChange={set("quantity")} />
      </div>
      <div className={cls("date")}>
        <label htmlFor={`date-${uid}`}>{t("field.date")}</label>
        <input id={`date-${uid}`} className="input" type="date" value={form.date} onChange={set("date")} />
      </div>
      <div className="field full">
        <label htmlFor={`notes-${uid}`}>{t("field.notes")}</label>
        <input id={`notes-${uid}`} className="input" value={form.notes} onChange={set("notes")} />
      </div>
      <div className="row full">
        <button className="btn btn-sm btn-primary" type="submit" disabled={busy}>
          {submitLabel ?? t("action.save")}
        </button>
        {onCancel && (
          <button className="btn btn-sm" type="button" onClick={onCancel} disabled={busy}>
            {t("action.cancel")}
          </button>
        )}
      </div>
    </form>
  );
}

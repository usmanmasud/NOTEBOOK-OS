import type { ConfidenceLevel } from "../types";

let currency = "NGN";
let locale = "en-NG";

/** Market settings come from the backend /api/config so nothing is hard-coded to one country. */
export function configureFormatting(next: { currency: string; locale: string }) {
  currency = next.currency;
  locale = next.locale;
}

export function money(value: number | null | undefined, opts: { compact?: boolean } = {}): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  try {
    return new Intl.NumberFormat(locale, {
      style: "currency",
      currency,
      maximumFractionDigits: value % 1 === 0 ? 0 : 2,
      notation: opts.compact ? "compact" : "standard",
    }).format(value);
  } catch {
    return `${currency} ${value.toLocaleString()}`;
  }
}

export function num(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 3 }).format(value);
}

export function shortDate(iso: string | null | undefined): string {
  if (!iso) return "No date";
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", year: "numeric" }).format(d);
}

export function dateTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`);
  return new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(d);
}

export function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function levelFor(value: number, thresholds: { high: number; review: number }): ConfidenceLevel {
  if (value >= thresholds.high) return "high";
  if (value >= thresholds.review) return "review";
  return "low";
}

/** "page-2-row-4" -> "Page 2, row 4" */
export function referenceLabel(ref: string | null | undefined): string {
  if (!ref) return "";
  if (ref === "manual-entry") return "Typed by you";
  const m = ref.match(/^page-(\d+)-row-(\d+)$/);
  return m ? `Page ${m[1]}, row ${m[2]}` : ref;
}

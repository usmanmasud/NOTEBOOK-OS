import type { ReactNode, SVGProps } from "react";
import { useI18n } from "../i18n";
import type { ConfidenceLevel, RecordStatus } from "../types";
import { percent } from "../utils/format";

type IconProps = SVGProps<SVGSVGElement>;
const base = (props: IconProps) => ({
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
  ...props,
});

export const Icon = {
  camera: (p: IconProps) => (
    <svg {...base(p)}><path d="M4 8h3l2-3h6l2 3h3v11H4z" /><circle cx="12" cy="13" r="3.5" /></svg>
  ),
  mic: (p: IconProps) => (
    <svg {...base(p)}><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></svg>
  ),
  keyboard: (p: IconProps) => (
    <svg {...base(p)}><rect x="3" y="6" width="18" height="12" rx="2" /><path d="M7 10h.01M11 10h.01M15 10h.01M7 14h10" /></svg>
  ),
  upload: (p: IconProps) => (
    <svg {...base(p)}><path d="M12 16V4M7 9l5-5 5 5M4 20h16" /></svg>
  ),
  check: (p: IconProps) => <svg {...base(p)}><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>,
  x: (p: IconProps) => <svg {...base(p)}><path d="M6 6l12 12M18 6L6 18" /></svg>,
  alert: (p: IconProps) => (
    <svg {...base(p)}><path d="M12 3l10 18H2z" /><path d="M12 10v4M12 17.5v.01" /></svg>
  ),
  info: (p: IconProps) => (
    <svg {...base(p)}><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8v.01" /></svg>
  ),
  dot: (p: IconProps) => <svg {...base(p)}><circle cx="12" cy="12" r="4" fill="currentColor" /></svg>,
  edit: (p: IconProps) => <svg {...base(p)}><path d="M4 20h4L19 9l-4-4L4 16zM13.5 6.5l4 4" /></svg>,
  trace: (p: IconProps) => (
    <svg {...base(p)}><path d="M4 6h10M4 12h7M4 18h4" /><circle cx="18" cy="15" r="3" /><path d="M20.2 17.2L22 19" /></svg>
  ),
  home: (p: IconProps) => <svg {...base(p)}><path d="M4 11l8-7 8 7v9h-5v-6H9v6H4z" /></svg>,
  list: (p: IconProps) => <svg {...base(p)}><path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01" /></svg>,
  chart: (p: IconProps) => <svg {...base(p)}><path d="M4 20V4M4 20h16M8 16v-5M12 16V8M16 16v-3" /></svg>,
  doc: (p: IconProps) => (
    <svg {...base(p)}><path d="M6 3h8l4 4v14H6z" /><path d="M14 3v4h4M9 12h6M9 16h6" /></svg>
  ),
  link: (p: IconProps) => (
    <svg {...base(p)}><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" /></svg>
  ),
  arrowLeft: (p: IconProps) => <svg {...base(p)}><path d="M15 6l-6 6 6 6" /></svg>,
  user: (p: IconProps) => <svg {...base(p)}><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></svg>,
  page: (p: IconProps) => (
    <svg {...base(p)}><rect x="5" y="3" width="14" height="18" rx="1.5" /><path d="M8 8h8M8 12h8M8 16h5" /></svg>
  ),
  pattern: (p: IconProps) => <svg {...base(p)}><path d="M3 17l5-5 4 4 8-8M14 8h6v6" /></svg>,
  printer: (p: IconProps) => (
    <svg {...base(p)}><path d="M7 9V3h10v6M7 17H4v-7h16v7h-3M7 14h10v7H7z" /></svg>
  ),
};

const LEVEL_TEXT: Record<ConfidenceLevel, string> = { high: "High", review: "Check", low: "Unsure" };

/** Confidence is always shown with an icon + words, never colour alone. */
export function ConfidenceBadge({ value, level }: { value: number; level: ConfidenceLevel }) {
  const I = level === "high" ? Icon.check : Icon.alert;
  return (
    <span className={`badge ${level}`} title={`AI confidence ${percent(value)}`}>
      <I /> {LEVEL_TEXT[level]} · {percent(value)}
    </span>
  );
}

export function StatusBadge({ status }: { status: RecordStatus }) {
  const { t } = useI18n();
  const cls = status === "CONFIRMED" ? "confirmed" : status === "REJECTED" ? "rejected" : status === "NEEDS_REVIEW" ? "review" : "";
  const I = status === "CONFIRMED" ? Icon.check : status === "REJECTED" ? Icon.x : Icon.dot;
  return (
    <span className={`badge ${cls}`}>
      <I /> {t(`status.${status}`)}
    </span>
  );
}

export function Notice({ kind = "info", children }: { kind?: "info" | "warn" | "error" | "good"; children: ReactNode }) {
  const I = kind === "good" ? Icon.check : kind === "info" ? Icon.info : Icon.alert;
  return (
    <div className={`notice ${kind === "info" ? "" : kind}`} role={kind === "error" ? "alert" : "status"}>
      <I />
      <div>{children}</div>
    </div>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="center" role="status">
      <div className="spinner" /> {label}
    </div>
  );
}

export function FixtureBadge({ show }: { show?: boolean }) {
  if (!show) return null;
  return (
    <span className="badge fixture" title="Read from a pre-recorded demo fixture, not a live OCR/speech model">
      Demo reading (offline)
    </span>
  );
}

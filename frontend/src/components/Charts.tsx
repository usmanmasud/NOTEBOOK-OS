import { useEffect, useRef, useState } from "react";
import { money, shortDate } from "../utils/format";

interface Point {
  label: string; // ISO date
  value: number;
}

function niceMax(v: number): number {
  if (v <= 0) return 1;
  const exp = 10 ** Math.floor(Math.log10(v));
  const f = v / exp;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * exp;
}

/**
 * Single-series column chart: one hue, no legend (the title names the series),
 * thin bars with rounded data-ends from a single baseline, hover/focus tooltip,
 * and a table view so no value depends on hovering.
 */
export function ColumnChart({ points, title, granularity }: { points: Point[]; title: string; granularity: "day" | "week" }) {
  const [hover, setHover] = useState<number | null>(null);
  const ref = useRef<HTMLElement>(null);
  const [W, setW] = useState(640);
  useEffect(() => {
    // Draw at the real pixel width so labels never shrink below their font size.
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(260, Math.round(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const H = 220, padL = 52, padR = 8, padT = 12, padB = 28;
  const max = niceMax(Math.max(0, ...points.map((p) => p.value)));
  const plotW = W - padL - padR, plotH = H - padT - padB;
  const band = plotW / Math.max(points.length, 1);
  const barW = Math.min(24, band * 0.6);
  const ticks = [0, 0.5, 1].map((f) => f * max);
  const labelEvery = Math.ceil(points.length / Math.max(2, Math.floor(W / 80)));
  const y = (v: number) => padT + plotH - (v / max) * plotH;

  return (
    <figure className="chart" style={{ margin: 0 }} ref={ref}>
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} role="img" aria-label={`${title} by ${granularity}`}>
        <g className="axis">
          {ticks.map((t) => (
            <g key={t}>
              <line className="gridline" x1={padL} x2={W - padR} y1={y(t)} y2={y(t)} />
              <text x={padL - 8} y={y(t) + 4} textAnchor="end">{money(t, { compact: true })}</text>
            </g>
          ))}
          {points.map((p, i) =>
            // Anchor labels on the latest point so the most recent bar is always labelled.
            (points.length - 1 - i) % labelEvery === 0 ? (
              <text key={p.label} x={padL + band * i + band / 2} y={H - 8} textAnchor="middle">
                {shortDate(p.label).replace(/ \d{4}$/, "")}
              </text>
            ) : null,
          )}
        </g>
        <line className="baseline" x1={padL} x2={W - padR} y1={y(0)} y2={y(0)} />
        {points.map((p, i) => {
          const x = padL + band * i + (band - barW) / 2;
          const h = Math.max(0, y(0) - y(p.value));
          const r = Math.min(4, h, barW / 2);
          // Rounded data-end, square at the baseline.
          const d = h <= 0 ? "" :
            `M${x},${y(0)} V${y(p.value) + r} Q${x},${y(p.value)} ${x + r},${y(p.value)} H${x + barW - r} Q${x + barW},${y(p.value)} ${x + barW},${y(p.value) + r} V${y(0)} Z`;
          return (
            <g key={p.label}>
              <rect
                className="hit"
                x={padL + band * i}
                y={padT}
                width={band}
                height={plotH}
                tabIndex={0}
                aria-label={`${shortDate(p.label)}: ${money(p.value)}`}
                onPointerEnter={() => setHover(i)}
                onPointerLeave={() => setHover(null)}
                onFocus={() => setHover(i)}
                onBlur={() => setHover(null)}
              />
              {d && <path className={`bar ${hover === i ? "hover" : ""}`} d={d} pointerEvents="none" />}
            </g>
          );
        })}
      </svg>
      {hover !== null && points[hover] && (
        <div
          className="tooltip"
          style={{
            left: `${((padL + band * hover + band / 2) / W) * 100}%`,
            top: `${(y(points[hover].value) / H) * 100}%`,
          }}
        >
          <strong>{money(points[hover].value)}</strong>
          {granularity === "week" ? "Week of " : ""}
          {shortDate(points[hover].label)}
        </div>
      )}
      <details className="table-view">
        <summary>View as table</summary>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr><th>{granularity === "week" ? "Week of" : "Date"}</th><th className="num">{title}</th></tr>
            </thead>
            <tbody>
              {points.map((p) => (
                <tr key={p.label}><td>{shortDate(p.label)}</td><td className="num">{money(p.value)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}

/** Horizontal bars, one row per person; values are always printed (no hover needed). */
export function HBarList({ rows, onSelect }: { rows: { label: string; value: number }[]; onSelect?: (label: string) => void }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <div className="hbar-list">
      {rows.map((r) => (
        <button key={r.label} type="button" className="hbar" onClick={() => onSelect?.(r.label)}
          aria-label={`${r.label}: ${money(r.value)}. Show evidence`}>
          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.label}</span>
          <span className="track"><span className="fill" style={{ width: `${(r.value / max) * 100}%` }} /></span>
          <span className="amt">{money(r.value)}</span>
        </button>
      ))}
    </div>
  );
}

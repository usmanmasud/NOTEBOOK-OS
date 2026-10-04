import { api } from "../services/api";
import { useObjectUrl } from "../hooks/useAsync";
import type { BBox, OcrLine, UploadType } from "../types";
import { percent } from "../utils/format";
import { Icon } from "./ui";

interface Props {
  uploadId: string;
  uploadType: UploadType | null;
  hasFile: boolean;
  lines?: OcrLine[];
  /** Line indexes that produced a record, and which of those need attention. */
  recordLines?: Map<number, { flagged: boolean }>;
  activeLine?: number | null;
  activeBox?: BBox | null;
  onSelectLine?: (index: number) => void;
}

const pct = (v: number) => `${(v * 100).toFixed(2)}%`;

/** The original evidence: notebook photo with line boxes, or the voice/typed transcript. */
export function SourceEvidence({
  uploadId, uploadType, hasFile, lines = [], recordLines, activeLine, activeBox, onSelectLine,
}: Props) {
  const showFile = hasFile && (uploadType === "PHOTO" || uploadType === "VOICE");
  const { url, failed } = useObjectUrl(showFile ? () => api.uploadFileBlob(uploadId) : null, showFile ? uploadId : null);

  if (uploadType === "PHOTO") {
    if (failed) return <p className="muted small">The original photo is no longer available.</p>;
    const boxed = lines.filter((l) => l.bbox);
    return (
      <div className="evidence-frame">
        {url ? (
          <img src={url} alt="Original notebook page" />
        ) : (
          <div className="center" style={{ aspectRatio: "0.775" }}>
            <div className="spinner" />
          </div>
        )}
        {url &&
          boxed.map((line) => {
            const b = line.bbox!;
            const rec = recordLines?.get(line.index);
            const cls = ["bbox", rec ? "has-record" : "", rec?.flagged ? "flagged" : "", activeLine === line.index ? "active" : ""].join(" ");
            return (
              <button
                key={line.index}
                type="button"
                className={cls}
                style={{ left: pct(b.x), top: pct(b.y), width: pct(b.width), height: pct(b.height) }}
                title={`Row ${line.index + 1}: “${line.text}” (read confidence ${percent(line.confidence)})`}
                aria-label={`Row ${line.index + 1}: ${line.text}`}
                onClick={() => onSelectLine?.(line.index)}
              />
            );
          })}
        {url && activeBox && (
          <div
            className="bbox active"
            style={{ left: pct(activeBox.x), top: pct(activeBox.y), width: pct(activeBox.width), height: pct(activeBox.height) }}
            aria-hidden="true"
          />
        )}
      </div>
    );
  }

  return (
    <div className="stack" style={{ gap: 10 }}>
      {uploadType === "VOICE" && showFile && url && (
        <audio controls src={url} style={{ width: "100%" }}>
          Your browser cannot play this recording.
        </audio>
      )}
      <div className="transcript">
        <div className="tiny" style={{ marginBottom: 6, display: "flex", gap: 6, alignItems: "center" }}>
          {uploadType === "VOICE" ? <Icon.mic width={14} /> : <Icon.keyboard width={14} />}
          {uploadType === "VOICE" ? "Transcript" : "Typed entry"}
        </div>
        {lines.length === 0 && <p className="muted small">No text.</p>}
        {lines.map((line) => (
          <div
            key={line.index}
            className={`transcript-line ${activeLine === line.index ? "active" : ""}`}
            onClick={() => onSelectLine?.(line.index)}
          >
            <span className="ln">{line.index + 1}</span>
            <span>{line.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

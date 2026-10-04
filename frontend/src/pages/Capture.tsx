import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Icon, Notice } from "../components/ui";
import { useApp } from "../hooks/useApp";
import { api, ApiError } from "../services/api";
import type { Sample } from "../types";

export function Capture() {
  const { config, user } = useApp();
  const navigate = useNavigate();
  const cameraInput = useRef<HTMLInputElement>(null);
  const imageInput = useRef<HTMLInputElement>(null);
  const audioInput = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [typed, setTyped] = useState("");
  const [showTyped, setShowTyped] = useState(false);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [recording, setRecording] = useState<MediaRecorder | null>(null);
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    if (config.demo_mode) api.samples().then(setSamples).catch(() => setSamples([]));
  }, [config.demo_mode]);

  useEffect(() => {
    if (!recording) return;
    const t = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [recording]);

  async function send(label: string, fn: () => Promise<{ id: string }>) {
    setBusy(label);
    setError(null);
    try {
      const upload = await fn();
      navigate(`/uploads/${upload.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Upload failed. Please try again.");
      setBusy(null);
    }
  }

  const onFile = (kind: "photo" | "voice") => (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    const limit = (kind === "photo" ? config.limits.photo_mb : config.limits.voice_mb) * 1024 * 1024;
    if (file.size > limit) {
      setError(`That file is too large (max ${limit / 1024 / 1024} MB).`);
      return;
    }
    send(kind, () => api.uploadFile(kind, file, file.name));
  };

  async function startRecording() {
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("Recording isn't supported in this browser. Upload an audio file or type the transaction instead.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      const chunks: Blob[] = [];
      rec.ondataavailable = (ev) => chunks.push(ev.data);
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunks, { type: rec.mimeType || "audio/webm" });
        const ext = blob.type.includes("mp4") ? "m4a" : blob.type.includes("ogg") ? "ogg" : "webm";
        send("voice", () => api.uploadFile("voice", blob, `recording.${ext}`));
      };
      rec.start();
      setSeconds(0);
      setRecording(rec);
    } catch {
      setError("Microphone access was blocked. Upload an audio file or type the transaction instead.");
    }
  }

  function stopRecording() {
    recording?.stop();
    setRecording(null);
  }

  async function pickSample(s: Sample) {
    send(s.id, async () => {
      const blob = await api.sampleFile(s.id);
      const name = s.mime_type === "image/png" ? `${s.id}.png` : `${s.id}.wav`;
      return api.uploadFile(s.type === "PHOTO" ? "photo" : "voice", blob, name);
    });
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Capture</h1>
          <p>Add today’s business from your notebook or by voice. You’ll check everything before it’s saved.</p>
        </div>
      </div>

      {error && <Notice kind="error">{error}</Notice>}

      <div className="capture-hero">
        <button className="capture-btn" onClick={() => cameraInput.current?.click()} disabled={!!busy}>
          <Icon.camera />
          <div>
            <strong>{busy === "photo" ? "Uploading…" : "Scan notebook"}</strong>
            <span>Take a photo of a page</span>
          </div>
        </button>
        {recording ? (
          <button className="capture-btn secondary" onClick={stopRecording}>
            <span className="recorder"><span className="rec-dot" /> Recording {seconds}s</span>
            <div>
              <strong>Tap to stop</strong>
              <span>Then we’ll transcribe it</span>
            </div>
          </button>
        ) : (
          <button className="capture-btn secondary" onClick={startRecording} disabled={!!busy}>
            <Icon.mic />
            <div>
              <strong>{busy === "voice" ? "Uploading…" : "Speak transaction"}</strong>
              <span>Record a voice note</span>
            </div>
          </button>
        )}
      </div>

      <input ref={cameraInput} type="file" accept="image/*" capture="environment" hidden onChange={onFile("photo")} />
      <input ref={imageInput} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={onFile("photo")} />
      <input ref={audioInput} type="file" accept="audio/*" hidden onChange={onFile("voice")} />

      <div className="row">
        <button className="btn btn-sm" onClick={() => imageInput.current?.click()} disabled={!!busy}>
          <Icon.upload /> Upload image
        </button>
        <button className="btn btn-sm" onClick={() => audioInput.current?.click()} disabled={!!busy}>
          <Icon.upload /> Upload audio
        </button>
        <button className="btn btn-sm" onClick={() => setShowTyped((v) => !v)} aria-expanded={showTyped}>
          <Icon.keyboard /> Typed entry
        </button>
      </div>

      {showTyped && (
        <div className="card stack">
          <div className="field">
            <label htmlFor="typed">One transaction per line</label>
            <textarea id="typed" className="input" value={typed} onChange={(e) => setTyped(e.target.value)}
              placeholder={"Sold 3 bags rice 45,000\nMusa 20k bashi\nKudin mota 2,500"} maxLength={5000} />
          </div>
          <div className="row">
            <button className="btn btn-primary" disabled={!typed.trim() || !!busy}
              onClick={() => send("text", () => api.uploadText(typed))}>
              Read my entry
            </button>
            <span className="tiny">English, Hausa or a mix is fine.</span>
          </div>
        </div>
      )}

      {config.demo_mode && samples.length > 0 && (
        <section className="card stack">
          <div className="card-head" style={{ marginBottom: 0 }}>
            <h2>Demo samples</h2>
            <span className="tiny">Fictional · work offline</span>
          </div>
          <div className="sample-list">
            {samples.map((s) => (
              <button key={s.id} className="sample" onClick={() => pickSample(s)} disabled={!!busy}>
                {s.type === "PHOTO" ? <Icon.page /> : <Icon.mic />}
                <span>
                  <strong className="small">{busy === s.id ? "Uploading…" : s.title}</strong>
                </span>
              </button>
            ))}
          </div>
          {user?.is_demo && <DemoReset />}
        </section>
      )}
    </div>
  );
}

function DemoReset() {
  const [state, setState] = useState<string | null>(null);
  async function reset() {
    if (!window.confirm("Reset the demo account? This removes everything in it and reloads the fictional history.")) return;
    setState("Resetting…");
    try {
      const r = await api.resetDemo(true);
      setState(`Demo reset. ${r.history_records_confirmed} earlier records loaded.`);
    } catch {
      setState("Reset failed.");
    }
  }
  return (
    <div className="row">
      <button className="btn btn-sm btn-ghost" onClick={reset}>Reset demo data</button>
      {state && <span className="tiny">{state}</span>}
    </div>
  );
}

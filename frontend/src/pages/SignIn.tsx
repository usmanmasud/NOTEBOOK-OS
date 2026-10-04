import { useState, type FormEvent } from "react";
import { BrandMark } from "../components/Layout";
import { Notice } from "../components/ui";
import { useApp } from "../hooks/useApp";
import { api, ApiError } from "../services/api";

export function SignIn() {
  const { signIn, config } = useApp();
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [devCode, setDevCode] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  const requestCode = (e: FormEvent) => {
    e.preventDefault();
    run(async () => {
      const r = await api.requestOtp(phone);
      setDevCode(r.dev_code ?? null);
      setStep("code");
    });
  };

  const verify = (e: FormEvent) => {
    e.preventDefault();
    run(async () => {
      const r = await api.verifyOtp(phone, code);
      signIn(r.token, r.user);
    });
  };

  const demo = () =>
    run(async () => {
      const r = await api.demoLogin();
      signIn(r.token, r.user);
    });

  return (
    <div className="main">
      <div className="signin">
        <div className="row" style={{ gap: 10 }}>
          <BrandMark />
          <h1>NotebookOS</h1>
        </div>
        <p className="tagline">
          Your business already has a database. It’s just handwritten. Photograph a notebook page or record a voice
          note — you check what the AI read, and only what you confirm becomes your business record.
        </p>

        <div className="card stack">
          {step === "phone" ? (
            <form className="stack" onSubmit={requestCode}>
              <div className="field">
                <label htmlFor="phone">Phone number</label>
                <input id="phone" className="input" type="tel" inputMode="tel" autoComplete="tel"
                  placeholder="+234 800 000 0000" value={phone} onChange={(e) => setPhone(e.target.value)} required />
              </div>
              <button className="btn btn-primary btn-block" disabled={busy}>Send code</button>
            </form>
          ) : (
            <form className="stack" onSubmit={verify}>
              <div className="field">
                <label htmlFor="code">Enter the 6-digit code sent to {phone}</label>
                <input id="code" className="input" inputMode="numeric" autoComplete="one-time-code" maxLength={6}
                  value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} required autoFocus />
              </div>
              {devCode && (
                <Notice kind="warn">
                  Development mode: no SMS is sent. Your code is <strong>{devCode}</strong>.
                </Notice>
              )}
              <button className="btn btn-primary btn-block" disabled={busy || code.length < 6}>Sign in</button>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setStep("phone")}>Use a different number</button>
            </form>
          )}
          {error && <Notice kind="error">{error}</Notice>}
        </div>

        {config.demo_mode && (
          <>
            <div className="divider">or</div>
            <div className="card stack">
              <button className="btn btn-block" onClick={demo} disabled={busy}>Open the demo account</button>
              <p className="tiny">
                The demo account contains fictional sample data only. No real people or businesses.
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

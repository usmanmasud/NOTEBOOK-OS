import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { BrandMark } from "../components/Layout";
import { Icon, Notice } from "../components/ui";
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
    <div className="auth">
      <aside className="auth-side">
        <Link to="/" className="brand auth-brand">
          <BrandMark /> NotebookOS
        </Link>
        <div className="auth-showcase" aria-hidden="true">
          <p className="auth-line">Musa shinkafa 2? 20k bashi</p>
          <span className="auth-arrow">
            <Icon.arrowRight />
          </span>
          <div className="auth-rec">
            <span>Musa · Credit · Rice</span>
            <strong>₦20,000</strong>
          </div>
        </div>
        <ul className="auth-points">
          <li>
            <Icon.check /> Photograph a page or record a voice note
          </li>
          <li>
            <Icon.check /> Check what was read, then confirm
          </li>
          <li>
            <Icon.check /> Every figure traces back to your handwriting
          </li>
        </ul>
      </aside>

      <main className="auth-main">
        <div className="signin">
          <Link to="/" className="brand auth-brand-mobile">
            <BrandMark /> NotebookOS
          </Link>
          <div>
            <h1>{step === "phone" ? "Sign in to NotebookOS" : "Check your phone"}</h1>
            <p className="tagline">
              {step === "phone"
                ? "Enter your phone number and we’ll send you a one-time code. No password needed."
                : `Enter the 6-digit code we sent to ${phone}.`}
            </p>
          </div>

          <div className="card stack">
            {step === "phone" ? (
              <form className="stack" onSubmit={requestCode}>
                <div className="field">
                  <label htmlFor="phone">Phone number</label>
                  <input
                    id="phone"
                    className="input"
                    type="tel"
                    inputMode="tel"
                    autoComplete="tel"
                    placeholder="+234 800 000 0000"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    required
                  />
                </div>
                <button className="btn btn-primary btn-block" disabled={busy}>
                  {busy ? "Sending…" : "Continue"}
                </button>
              </form>
            ) : (
              <form className="stack" onSubmit={verify}>
                <div className="field">
                  <label htmlFor="code">Verification code</label>
                  <input
                    id="code"
                    className="input otp-input"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={6}
                    placeholder="••••••"
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                    required
                    autoFocus
                  />
                </div>
                {devCode && (
                  <Notice kind="warn">
                    Development mode: no SMS is sent. Your code is <strong>{devCode}</strong>.
                  </Notice>
                )}
                <button className="btn btn-primary btn-block" disabled={busy || code.length < 6}>
                  {busy ? "Signing in…" : "Sign in"}
                </button>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setStep("phone")}>
                  Use a different number
                </button>
              </form>
            )}
            {error && <Notice kind="error">{error}</Notice>}
          </div>

          {config.demo_mode && (
            <div className="stack auth-demo">
              <div className="divider">or</div>
              <button className="btn btn-outline btn-block" onClick={demo} disabled={busy}>
                Explore a sample workspace <Icon.arrowRight />
              </button>
              <p className="tiny">Pre-filled with sample records for a fictional trader. No sign-up needed.</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

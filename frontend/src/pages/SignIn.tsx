import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { BrandMark } from "../components/Layout";
import { Icon, Notice } from "../components/ui";
import { useApp } from "../hooks/useApp";
import { api, ApiError, type SignInId } from "../services/api";
import type { LoginMethod } from "../types";

export function SignIn() {
  const { signIn, config } = useApp();
  const methods = config.login_methods;
  const [chosen, setChosen] = useState<LoginMethod | null>(null);
  const method: LoginMethod | undefined = chosen && methods.includes(chosen) ? chosen : methods[0];
  const [contact, setContact] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"contact" | "code">("contact");
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

  const who = (): SignInId => (method === "phone" ? { phone: contact } : { email: contact.trim() });

  const requestCode = (e: FormEvent) => {
    e.preventDefault();
    run(async () => {
      const r = await api.requestOtp(who());
      setCode("");
      setDevCode(r.dev_code ?? null);
      setStep("code");
    });
  };

  const verify = (e: FormEvent) => {
    e.preventDefault();
    run(async () => {
      const r = await api.verifyOtp(who(), code);
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
            <h1>{step === "contact" ? "Sign in to NotebookOS" : method === "phone" ? "Check your phone" : "Check your email"}</h1>
            <p className="tagline">
              {step === "code"
                ? `Enter the 6-digit code we sent to ${contact.trim()}.`
                : method === "phone"
                  ? "Enter your phone number and we’ll send you a one-time code. No password needed."
                  : "Enter your email address and we’ll send you a one-time code. No password needed."}
            </p>
          </div>

          <div className="card stack">
            {!method ? (
              <Notice kind="info">
                Sign-in with a code isn’t available on this server yet. You can still explore the sample workspace below.
              </Notice>
            ) : step === "contact" ? (
              <form className="stack" onSubmit={requestCode}>
                {methods.length > 1 && (
                  <div className="seg" role="group" aria-label="Sign in with">
                    {methods.map((m) => (
                      <button
                        key={m}
                        type="button"
                        aria-pressed={m === method}
                        onClick={() => {
                          setChosen(m);
                          setContact("");
                        }}
                      >
                        {m === "email" ? "Email" : "Phone"}
                      </button>
                    ))}
                  </div>
                )}
                <div className="field">
                  {method === "phone" ? (
                    <>
                      <label htmlFor="contact">Phone number</label>
                      <input
                        id="contact"
                        className="input"
                        type="tel"
                        inputMode="tel"
                        autoComplete="tel"
                        placeholder="+234 800 000 0000"
                        value={contact}
                        onChange={(e) => setContact(e.target.value)}
                        required
                      />
                    </>
                  ) : (
                    <>
                      <label htmlFor="contact">Email address</label>
                      <input
                        id="contact"
                        className="input"
                        type="email"
                        inputMode="email"
                        autoComplete="email"
                        placeholder="you@example.com"
                        value={contact}
                        onChange={(e) => setContact(e.target.value)}
                        required
                      />
                    </>
                  )}
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
                    Development mode: the code is shown here instead of being sent. Your code is <strong>{devCode}</strong>.
                  </Notice>
                )}
                <button className="btn btn-primary btn-block" disabled={busy || code.length < 6}>
                  {busy ? "Signing in…" : "Sign in"}
                </button>
                {method === "email" && <p className="tiny">Didn’t get it? Check your spam folder. Codes expire after 5 minutes.</p>}
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setStep("contact")}>
                  {method === "phone" ? "Use a different number" : "Use a different email"}
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

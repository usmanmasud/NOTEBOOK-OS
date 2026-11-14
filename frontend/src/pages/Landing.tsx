import { Link } from "react-router-dom";
import { BrandMark } from "../components/Layout";
import { Icon } from "../components/ui";

const REPO_URL = "https://github.com/usmanmasud/NOTEBOOK-OS";

const ENTRY_TYPES = ["Sales", "Credit (bashi)", "Repayments", "Expenses", "Restocks"];

const GAPS = [
  { title: "It can't be searched", body: "Finding one customer means turning pages until you see their name." },
  { title: "It can't be totalled", body: "A month of sales is an evening with a calculator." },
  { title: "It can't say who owes you", body: "Goods given on credit are scattered across weeks of entries." },
  { title: "A lender can't read it", body: "There is no summary to hand over when you ask for a loan." },
];

const STEPS = [
  {
    icon: Icon.camera,
    title: "Capture",
    body: "Photograph a notebook page, record a voice note, or type the entries. English, Hausa, or a mix of both.",
  },
  {
    icon: Icon.page,
    title: "Read",
    body: "Each line becomes a record: a sale, credit, a repayment, an expense or a restock, with a confidence score on every field.",
  },
  {
    icon: Icon.check,
    title: "Confirm",
    body: "Anything uncertain is highlighted next to the original line. You correct it and confirm. Only confirmed records count.",
  },
  {
    icon: Icon.chart,
    title: "Grow",
    body: "Track sales, expenses and who owes you, and share a one-page business summary through a link you control.",
  },
];

const PRINCIPLES = [
  {
    title: "You have the final say",
    body: "Nothing NotebookOS reads becomes a business record until you confirm it.",
  },
  {
    title: "Every number shows its source",
    body: "Tap a figure to see the records behind it and the exact line on the notebook photo.",
  },
  {
    title: "Unclear stays unclear",
    body: "A smudged value is left blank and flagged, never guessed. Every amount and name is checked against the source text.",
  },
  {
    title: "Totals you can rely on",
    body: "Figures are calculated by plain, deterministic code, so the same records always give the same numbers.",
  },
];

const SECURITY = [
  {
    icon: Icon.lock,
    title: "Private by default",
    body: "Your records, photos and voice notes are visible only to your account. Files are stored privately and served only to you.",
  },
  {
    icon: Icon.phone,
    title: "No passwords to lose",
    body: "Sign in with your phone number and a one-time code. Codes expire in minutes and are never stored in readable form.",
  },
  {
    icon: Icon.link,
    title: "Sharing you control",
    body: "Report links are read-only, leave out your customers’ names, and can be switched off at any time.",
  },
];

const FAQ = [
  {
    q: "Do I need to install an app?",
    a: "No. NotebookOS runs in the browser on any phone, tablet or computer. Open the site, sign in with your phone number, and start capturing.",
  },
  {
    q: "Which languages does it understand?",
    a: "English, Hausa, and the mix of both that most traders actually write. Common shorthand like “20k” and “bashi” is understood.",
  },
  {
    q: "What happens if my handwriting is hard to read?",
    a: "Anything NotebookOS isn’t sure about is left blank and highlighted next to the original line. You fill it in before confirming. It never guesses.",
  },
  {
    q: "Can I keep using my notebook?",
    a: "Yes, that’s the point. Keep writing the way you always have, and photograph the page at the end of the day.",
  },
  {
    q: "Is the business summary a credit score?",
    a: "No. It is a clear summary of the records you confirmed. It helps you start a conversation with a lender or supplier, but it doesn’t rate you.",
  },
];

function HeroVisual() {
  return (
    <figure className="lp-visual">
      <div className="lp-glow" aria-hidden="true" />
      <div className="lp-page">
        <div className="lp-page-bar" aria-hidden="true">
          <span />
          <span />
          <span />
          <em>Page 2 · scanned</em>
        </div>
        <div className="lp-page-img">
          <img
            src="/landing-notebook.webp"
            width={930}
            height={690}
            alt="A handwritten notebook page listing sales, an expense, a restock and one smudged credit entry for Musa."
          />
          <span className="lp-mark" aria-hidden="true">
            <span className="lp-mark-tag">Needs a look · 61%</span>
          </span>
          <span className="lp-scan" aria-hidden="true" />
        </div>
      </div>

      <div className="lp-float lp-float-stat" aria-hidden="true">
        <span className="lp-float-label">Outstanding debt</span>
        <strong>₦40,000</strong>
        <span className="lp-float-sub">
          <Icon.trace /> 2 customers · traced to source
        </span>
      </div>

      <div className="record-card status-NEEDS_REVIEW lp-record">
        <div className="record-head">
          <strong>Musa</strong>
          <span className="badge review">
            <Icon.alert /> Check · 61%
          </span>
          <span className="spacer" />
          <span className="tiny">Page 2, row 4</span>
        </div>
        <div className="record-summary">
          <div className="kv">
            <span className="k">Type</span>
            <span className="v">Credit</span>
          </div>
          <div className="kv">
            <span className="k">Item</span>
            <span className="v">Rice</span>
          </div>
          <div className="kv">
            <span className="k">Amount</span>
            <span className="v">₦20,000</span>
          </div>
          <div className="kv flag-review">
            <span className="k">Quantity</span>
            <span className="v empty-v">Unclear</span>
          </div>
        </div>
      </div>
    </figure>
  );
}

function Trace() {
  return (
    <div className="lp-trace" aria-label="Example: where the outstanding debt figure comes from">
      <div className="lp-trace-head">
        <span className="section-title">Outstanding debt</span>
        <span className="badge confirmed">
          <Icon.check /> Confirmed
        </span>
      </div>
      <div className="lp-trace-total">₦40,000</div>
      <ul className="lp-trace-rows">
        <li>
          <span>
            <strong>Musa</strong>
            <span className="tiny">Page 2, row 4</span>
          </span>
          <span className="quote">Musa shinkafa 2? 20k bashi</span>
          <span className="lp-amt">₦20,000</span>
        </li>
        <li>
          <span>
            <strong>Aisha</strong>
            <span className="tiny">Page 5, row 3</span>
          </span>
          <span className="quote">Aisha mai 20,000 bashi</span>
          <span className="lp-amt">₦20,000</span>
        </li>
      </ul>
      <p className="tiny">
        <Icon.trace /> Every figure opens the records and notebook lines it was built from.
      </p>
    </div>
  );
}

function MiniBars() {
  const bars = [38, 52, 44, 70, 58, 84, 66];
  return (
    <div className="lp-minibars" aria-hidden="true">
      {bars.map((h, i) => (
        <span key={i} style={{ height: `${h}%` }} className={i === 5 ? "hi" : undefined} />
      ))}
    </div>
  );
}

export function Landing() {
  return (
    <div className="lp">
      <header className="lp-nav">
        <div className="lp-wrap lp-nav-inner">
          <Link to="/" className="brand">
            <BrandMark /> <span>NotebookOS</span>
          </Link>
          <nav className="lp-links" aria-label="Sections">
            <a href="#how">How it works</a>
            <a href="#features">Features</a>
            <a href="#trust">Trust</a>
            <a href="#faq">FAQ</a>
          </nav>
          <div className="lp-nav-actions">
            <Link to="/signin" className="btn btn-ghost btn-sm lp-signin">
              Sign in
            </Link>
            <Link to="/signin" className="btn btn-primary btn-sm">
              Get started
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="lp-hero-band">
          <div className="lp-wrap lp-hero">
            <div className="lp-hero-copy">
              <p className="lp-pill">
                <span className="lp-pill-dot" /> Reads English, Hausa and everything in between
              </p>
              <h1>
                Your business already has a database. <span className="lp-accent">It’s just handwritten.</span>
              </h1>
              <p className="lp-lead">
                NotebookOS turns a photo of your notebook, or a quick voice note, into clean business records. See your
                sales, expenses and who owes you, without giving up the notebook you trust.
              </p>
              <div className="row lp-cta">
                <Link to="/signin" className="btn btn-primary btn-lg">
                  Get started free <Icon.arrowRight />
                </Link>
                <a href="#how" className="btn btn-lg btn-outline">
                  See how it works
                </a>
              </div>
              <ul className="lp-ticks">
                <li>
                  <Icon.check /> No app to install
                </li>
                <li>
                  <Icon.check /> You confirm every entry
                </li>
                <li>
                  <Icon.check /> Works on any phone
                </li>
              </ul>
            </div>
            <HeroVisual />
          </div>
          <div className="lp-wrap lp-types" aria-label="Entry types NotebookOS records">
            <span className="tiny">Records every kind of entry</span>
            <ul>
              {ENTRY_TYPES.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </div>
        </section>

        <section className="lp-wrap lp-section">
          <div className="lp-head">
            <p className="lp-eyebrow">The problem</p>
            <h2>The notebook works, until you need an answer from it.</h2>
            <p>
              Millions of small traders record every sale, credit, repayment, expense and restock by hand. The record is
              complete. It just can’t be asked a question.
            </p>
          </div>
          <ul className="lp-gaps">
            {GAPS.map((g, i) => (
              <li key={g.title}>
                <span className="lp-gap-num">{String(i + 1).padStart(2, "0")}</span>
                <h3>{g.title}</h3>
                <p>{g.body}</p>
              </li>
            ))}
          </ul>
        </section>

        <section id="how" className="lp-band">
          <div className="lp-wrap lp-section">
            <div className="lp-head lp-head-center">
              <p className="lp-eyebrow">How it works</p>
              <h2>From a notebook page to clear records in minutes.</h2>
              <p>Keep writing the way you always have. NotebookOS does the reading, you stay in charge.</p>
            </div>
            <ol className="lp-steps">
              {STEPS.map((s, i) => (
                <li key={s.title}>
                  <div className="lp-step-top">
                    <span className="lp-step-icon">
                      <s.icon />
                    </span>
                    <span className="lp-step-num">Step {i + 1}</span>
                  </div>
                  <h3>{s.title}</h3>
                  <p>{s.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="features" className="lp-wrap lp-section">
          <div className="lp-head">
            <p className="lp-eyebrow">Features</p>
            <h2>Everything your notebook knows, finally at your fingertips.</h2>
          </div>
          <div className="lp-bento">
            <article className="lp-tile lp-tile-wide">
              <div>
                <span className="lp-tile-icon">
                  <Icon.chart />
                </span>
                <h3>A live view of your business</h3>
                <p>
                  Sales, expenses, stock purchases, money collected and net cash flow, updated the moment you confirm a
                  page.
                </p>
              </div>
              <div className="lp-tile-demo">
                <div className="lp-mini-stats" aria-hidden="true">
                  <div>
                    <span>Sales this week</span>
                    <strong>₦312,500</strong>
                  </div>
                  <div>
                    <span>Owed to you</span>
                    <strong>₦40,000</strong>
                  </div>
                </div>
                <MiniBars />
              </div>
            </article>
            <article className="lp-tile">
              <span className="lp-tile-icon">
                <Icon.mic />
              </span>
              <h3>Speak it, snap it, or type it</h3>
              <p>Busy at the stall? Record a voice note. At the end of the day, photograph the page.</p>
            </article>
            <article className="lp-tile">
              <span className="lp-tile-icon">
                <Icon.user />
              </span>
              <h3>Know who owes you</h3>
              <p>Every credit and repayment is matched to a customer, so outstanding debt is always one tap away.</p>
            </article>
            <article className="lp-tile">
              <span className="lp-tile-icon">
                <Icon.globe />
              </span>
              <h3>Speaks your language</h3>
              <p>Understands English, Hausa and mixed entries, including shorthand like “20k” and “bashi”.</p>
            </article>
            <article className="lp-tile lp-tile-accent">
              <span className="lp-tile-icon">
                <Icon.doc />
              </span>
              <h3>A summary you can hand to a lender</h3>
              <p>Create a clean one-page report of your confirmed records and share it with a private link.</p>
              <div className="lp-share" aria-hidden="true">
                <Icon.link /> Share link · /r/•••••••• <span>Read-only</span>
              </div>
            </article>
          </div>
        </section>

        <section id="trust" className="lp-band">
          <div className="lp-wrap lp-section lp-split">
            <div>
              <div className="lp-head">
                <p className="lp-eyebrow">Built for trust</p>
                <h2>Money records have to be right. So you can check every figure.</h2>
                <p>NotebookOS proposes. You decide. Every number on your dashboard leads back to your own handwriting.</p>
              </div>
              <dl className="lp-principles">
                {PRINCIPLES.map((p) => (
                  <div key={p.title}>
                    <dt>
                      <Icon.check /> {p.title}
                    </dt>
                    <dd>{p.body}</dd>
                  </div>
                ))}
              </dl>
            </div>
            <Trace />
          </div>
        </section>

        <section id="security" className="lp-wrap lp-section">
          <div className="lp-head">
            <p className="lp-eyebrow">Privacy & security</p>
            <h2>Your books stay yours.</h2>
            <p>Your records are your business. NotebookOS is built so that only you decide who sees them.</p>
          </div>
          <ul className="lp-security">
            {SECURITY.map((s) => (
              <li key={s.title}>
                <span className="lp-tile-icon">
                  <s.icon />
                </span>
                <h3>{s.title}</h3>
                <p>{s.body}</p>
              </li>
            ))}
          </ul>
        </section>

        <section id="faq" className="lp-band">
          <div className="lp-wrap lp-section lp-faq-wrap">
            <div className="lp-head">
              <p className="lp-eyebrow">FAQ</p>
              <h2>Questions traders ask us.</h2>
            </div>
            <div className="lp-faq">
              {FAQ.map((f) => (
                <details key={f.q}>
                  <summary>
                    {f.q}
                    <span className="lp-faq-icon" aria-hidden="true" />
                  </summary>
                  <p>{f.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        <section className="lp-wrap lp-final-wrap">
          <div className="lp-final">
            <h2>Turn today’s page into tomorrow’s answers.</h2>
            <p>Sign in with your phone number and capture your first notebook page in under a minute.</p>
            <div className="row lp-cta-center">
              <Link to="/signin" className="btn btn-lg lp-btn-light">
                Get started free <Icon.arrowRight />
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="lp-footer">
        <div className="lp-wrap lp-footer-inner">
          <div className="lp-footer-brand">
            <span className="brand">
              <BrandMark /> NotebookOS
            </span>
            <p className="small muted">Business records for traders who keep their books on paper.</p>
          </div>
          <nav className="lp-footer-cols" aria-label="Footer">
            <div>
              <span className="lp-footer-h">Product</span>
              <a href="#how">How it works</a>
              <a href="#features">Features</a>
              <a href="#security">Security</a>
            </div>
            <div>
              <span className="lp-footer-h">Company</span>
              <a href="#faq">FAQ</a>
              <a href={REPO_URL}>GitHub</a>
              <Link to="/signin">Sign in</Link>
            </div>
          </nav>
        </div>
        <div className="lp-wrap lp-footer-base tiny">
          <span>© {new Date().getFullYear()} NotebookOS</span>
          <span>Open source under the MIT license</span>
        </div>
      </footer>
    </div>
  );
}

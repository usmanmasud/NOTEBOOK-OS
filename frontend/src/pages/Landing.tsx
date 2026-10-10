import { Link } from "react-router-dom";
import { BrandMark } from "../components/Layout";
import { Icon } from "../components/ui";

const REPO_URL = "https://github.com/usmanmasud/NOTEBOOK-OS";

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
    body: "Each line becomes a record: a sale, goods on credit (bashi), a repayment, an expense or a restock. Every field gets a confidence score.",
  },
  {
    icon: Icon.check,
    title: "Confirm",
    body: "Anything uncertain is highlighted next to the original line. You correct it and confirm. Only confirmed records count.",
  },
  {
    icon: Icon.chart,
    title: "Use",
    body: "See sales, expenses and outstanding debt on a dashboard, and share a one-page summary through a link you can switch off.",
  },
];

const PRINCIPLES = [
  {
    title: "You have the final say",
    body: "Nothing the AI reads becomes a business record until you confirm it.",
  },
  {
    title: "Every number shows its source",
    body: "Click a figure to see the records behind it and the exact line on the notebook photo.",
  },
  {
    title: "Unclear stays unclear",
    body: "A smudged value is left blank and flagged, never guessed. Every amount and name is checked against the source text.",
  },
  {
    title: "Code does the arithmetic",
    body: "Totals are calculated by ordinary application code, not by a language model, so the same records always give the same numbers.",
  },
];

const STACK = [
  { name: "ECS", role: "Web app and API" },
  { name: "RDS for MySQL", role: "Users, uploads, records, reports" },
  { name: "DCS Redis", role: "Sessions, sign-in codes, rate limits" },
  { name: "OBS", role: "Notebook photos and voice notes" },
  { name: "OCR and SIS", role: "Handwriting and speech to text" },
  { name: "ModelArts", role: "Language model for interpretation" },
];

function HeroVisual() {
  return (
    <figure className="lp-visual">
      <div className="lp-page">
        <img
          src="/landing-notebook.webp"
          width={930}
          height={690}
          alt="A fictional handwritten notebook page listing sales, an expense, a restock and one smudged credit entry for Musa."
        />
        <span className="lp-mark" aria-hidden="true">
          <span className="lp-mark-tag">Read at 61%</span>
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
            <span className="v">Debt</span>
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
      <figcaption className="tiny">
        A sample page from the demo. The smudged line is flagged for the trader to check, not guessed.
      </figcaption>
    </figure>
  );
}

function Trace() {
  return (
    <div className="card lp-trace" aria-label="Example: where the outstanding debt figure comes from">
      <div className="section-title">Outstanding debt</div>
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
          <span className="lp-amt">₦20,000</span>
        </li>
      </ul>
      <p className="tiny">
        <Icon.trace /> Each figure opens the records and the notebook lines it was built from.
      </p>
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
            <a href="#trust">Why trust it</a>
            <a href="#technology">Technology</a>
          </nav>
          <Link to="/signin" className="btn btn-sm">
            Sign in
          </Link>
        </div>
      </header>

      <main>
        <section className="lp-wrap lp-hero">
          <div className="lp-hero-copy">
            <p className="lp-eyebrow">For traders who keep their books on paper</p>
            <h1>Your business already has a database. It’s just handwritten.</h1>
            <p className="lp-lead">
              NotebookOS turns a photo of a notebook page, or a voice note, into business records you can search and
              total. You check what it read, and only what you confirm counts.
            </p>
            <div className="row lp-cta">
              <Link to="/signin" className="btn btn-primary">
                Try the demo
              </Link>
              <a href="#how" className="btn btn-ghost">
                See how it works
              </a>
            </div>
            <p className="tiny">
              The demo account holds fictional data only. The first load can take about a minute while the server wakes
              up.
            </p>
          </div>
          <HeroVisual />
        </section>

        <section className="lp-band">
          <div className="lp-wrap lp-section">
            <div className="lp-head">
              <h2>The notebook works, until you need an answer from it.</h2>
              <p>
                Many small traders record every sale, credit, repayment, expense and restock by hand. The record is
                complete. It just can’t be asked a question.
              </p>
            </div>
            <ul className="lp-gaps">
              {GAPS.map((g) => (
                <li key={g.title}>
                  <h3>{g.title}</h3>
                  <p>{g.body}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section id="how" className="lp-wrap lp-section">
          <div className="lp-head">
            <p className="lp-eyebrow">How it works</p>
            <h2>From a page to a record in four steps.</h2>
          </div>
          <ol className="lp-steps">
            {STEPS.map((s, i) => (
              <li key={s.title}>
                <div className="lp-step-top">
                  <span className="lp-step-icon">
                    <s.icon />
                  </span>
                  <span className="lp-step-num">{String(i + 1).padStart(2, "0")}</span>
                </div>
                <h3>{s.title}</h3>
                <p>{s.body}</p>
              </li>
            ))}
          </ol>
        </section>

        <section id="trust" className="lp-band">
          <div className="lp-wrap lp-section lp-split">
            <div>
              <div className="lp-head">
                <p className="lp-eyebrow">Why trust it</p>
                <h2>Built so you can check every figure.</h2>
                <p>Money records have to be right. The AI proposes, and the trader decides.</p>
              </div>
              <dl className="lp-principles">
                {PRINCIPLES.map((p) => (
                  <div key={p.title}>
                    <dt>{p.title}</dt>
                    <dd>{p.body}</dd>
                  </div>
                ))}
              </dl>
            </div>
            <Trace />
          </div>
        </section>

        <section id="technology" className="lp-wrap lp-section">
          <div className="lp-head">
            <p className="lp-eyebrow">Technology</p>
            <h2>Designed for Huawei Cloud.</h2>
            <p>
              A React web app that runs in a phone browser, backed by a FastAPI service. Each AI step sits behind a
              swappable provider with an offline fallback, so the app keeps working when a service is unavailable.
            </p>
          </div>
          <ul className="lp-stack">
            {STACK.map((s) => (
              <li key={s.name}>
                <strong>{s.name}</strong>
                <span>{s.role}</span>
              </li>
            ))}
          </ul>
          <div className="notice lp-status">
            <Icon.info />
            <div>
              <strong>Where the project stands.</strong> NotebookOS is a hackathon MVP built for the Huawei ICT
              Competition, Innovation track. The full flow works end to end in the live demo, which currently runs on
              interim hosting. The Huawei Cloud services are implemented but not yet verified against live accounts,
              and accuracy on real notebooks has not been measured. The{" "}
              <a href={`${REPO_URL}#status-what-is-and-isnt-verified`}>status table</a> lists what is and isn’t
              verified.
            </div>
          </div>
        </section>

        <section className="lp-wrap lp-final">
          <h2>See it read a notebook page.</h2>
          <p>Open the demo account, pick a sample page, and follow one figure back to the line it came from.</p>
          <Link to="/signin" className="btn btn-primary">
            Try the demo
          </Link>
        </section>
      </main>

      <footer className="lp-footer">
        <div className="lp-wrap lp-footer-inner">
          <span className="brand">
            <BrandMark /> NotebookOS
          </span>
          <span className="tiny">Built for the Huawei ICT Competition, Innovation track. MIT licensed.</span>
          <a className="small" href={REPO_URL}>
            Source on GitHub
          </a>
        </div>
      </footer>
    </div>
  );
}

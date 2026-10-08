# Demo video script (preliminary round, about 5 minutes)

**For:** the team member recording the competition demo video.
**Record:** a phone-sized browser window (or a real phone) on
https://notebook-os-xi.vercel.app, plus a printed copy of
`samples/notebooks/notebook_a_page2.png`.

**Before recording:**
- Open the site 3 minutes early so the free backend wakes up.
- Sign in with *Open the demo account*.
- On the Capture screen, click **Reset demo data**.

Everything in the demo is fictional. Keep these rules while recording:
- Never say NotebookOS has users, pilots or partners. It has none yet.
- Only say ModelArts or Huawei OCR is used once it actually is (see the last section).

---

## 0:00–0:35 · The problem (talking head or slides)

> "Across our markets, many small traders keep their whole business in a notebook:
> sales, goods given on credit (what Hausa traders call *bashi*), repayments,
> expenses. The notebook works. But you can't add it up, you can't see who still owes
> you, and a lender can't read it."

Show: the printed notebook page, held up to the camera.

## 0:35–1:00 · The idea

> "NotebookOS turns that notebook into structured, searchable business records,
> without asking the trader to stop using the notebook. AI reads the page, the trader
> checks what it read, and every number on the dashboard can be traced back to the line
> it came from."

Show: the sign-in screen with the line "Your business already has a database. It's just
handwritten."

## 1:00–3:45 · Live demo (screen recording)

1. **Capture** (1:00). Tap **Demo samples → Notebook A — page 2**.
   > "I'm uploading this notebook page. NotebookOS reads it, interprets the mixed
   > Hausa and English, and checks the result."
2. **Review** (1:20). Pause on the photo with the boxes around each line.
   > "Every line the AI read is boxed on the original photo. The total written on the
   > page, 63,000 naira, matches the sales it found."

   Point at **Musa: 61%, highlighted**.
   > "This line is smudged. The AI reads Musa, 20,000 naira, debt. But it can't read
   > the quantity, so instead of guessing it marks it unclear and asks me."
3. **Correct** (1:50). **Edit → Quantity 2 → Save.** "You set this" appears.
   > "Nothing the AI produces counts until a person confirms it."
4. **Confirm** (2:10). **Confirm 5 records** → the Dashboard opens.
   > "These figures are calculated by the application from confirmed records only. The
   > AI never does the arithmetic."
5. **Evidence** (2:30). Tap **Outstanding Debt ₦40,000**.
   > "This number didn't come from nowhere. Musa, 20,000, page 2, row 4. Here's the
   > original text, the AI's 61% confidence, my correction, and my confirmation. And
   > here's the exact line, highlighted on the photo."

   Scroll to Aisha.
   > "Aisha's debt comes from page 5. It's labelled as pre-loaded demo history."
6. **Report** (3:05). Go to **Report**, tick consent, then **Generate report**.
   > "A one-page summary for a lender. It says clearly that this is a summary of
   > confirmed records, not a credit score."

   **Copy share link** → open it in a private window.
   > "The link is read-only and needs no login. Customer names and photos aren't shared,
   > and I can revoke the link at any time."
7. **Fallback** (3:35, optional). Typed entry: `Musa 20k bashi`.
   > "If there's no photo or no signal for AI, the trader can type or speak it and the
   > same checks apply."

## 3:45–4:30 · How it works

Show: the architecture slide.

> "The pipeline has four stages: read, understand, validate, summarise. Reading and
> understanding are AI. Validation is deterministic: it checks that every amount and
> name the AI proposes actually appears in the source text. Summaries are plain code.
> Provenance links each record to its page, row and pixel location on the photo."

Name the Huawei technologies exactly as they are at the time of recording (see below).

## 4:30–5:00 · Value and close

> "Nothing in the core is tied to one city. Currency, language vocabulary and date
> format are configuration. NotebookOS doesn't ask informal businesses to stop using
> the notebook they trust. It makes that notebook computable."

---

## Wording for the Huawei part: pick the true one

| Situation when recording | Say |
|---|---|
| ModelArts + Huawei OCR integrated and working | "Pages are read by Huawei Cloud OCR, interpreted by a model on Huawei ModelArts, and stored in Huawei Cloud RDS." |
| Not yet integrated | "In this demo the sample page is read by an offline demo reader. In our Huawei deployment, Huawei Cloud OCR reads the page and ModelArts interprets it. That integration is in progress." |

The competition requires Huawei AI technology such as ModelArts. Make sure it is
genuinely integrated before the final submission.

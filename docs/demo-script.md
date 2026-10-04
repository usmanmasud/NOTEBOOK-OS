# Judge demo script (4 minutes)

**Before you start:** sign in with *Open the demo account*. Go to Capture and choose
*Reset demo data*. Keep the Dashboard open in a second tab. The demo runs offline. The
bundled sample pages are read by the offline demo provider and labelled *Demo reading
(offline)*. If Huawei OCR is configured, say so and show its name in the "Read (…)" line
of the review screen.

All people, businesses and amounts in the demo are fictional.

---

### 0:00–0:30 · Problem

> "Many small traders run their business from a notebook: sales, goods given on credit
> (*bashi*), repayments, expenses. The notebook is trusted, but you can't search it,
> total it, see who still owes you, or show it to a lender."

Hold up the printed **Notebook A, page 2** (`samples/notebooks/notebook_a_page2.png`).

### 0:30–0:45 · Concept

> "NotebookOS: your business already has a database. It's just handwritten. We read
> the page, the trader checks what we read, and every number can be traced back to the
> line it came from."

### 0:45–2:45 · Live demo

1. **Capture** → *Demo samples* → **Notebook A — page 2** (or upload the photo).
   > "It reads the page, interprets mixed Hausa and English, and checks the result."
2. **Review screen.** Point at:
   * the boxes drawn on the photo around every line the AI read;
   * *"The total written on the page (₦63,000) matches the sales found"*;
   * **Musa's row: 61%, highlighted.** *"The 2 is smudged. The AI won't guess, so the
     quantity is unclear."*
3. Click **Edit** on Musa → quantity **2** → **Save**. It now shows *"You set this"*.
   > "Human confirmation is the product. Nothing counts until the trader confirms it."
4. **Confirm 5 records** → the **Dashboard** updates.
5. Click **Outstanding Debt ₦40,000**.
   > "This number did not come from nowhere."

   Show **Musa ₦20,000**: page 2, row 4, original text *"Musa shinkafa 2? 20k bashi"*,
   AI 61%, quantity corrected by trader, confirmed. The line is highlighted on the
   photo. Scroll to **Aisha ₦20,000**: page 5, labelled as pre-loaded demo history.
6. **Report** → tick the consent box → **Generate report**.
   > "It's a one-page summary of confirmed records. It's not a credit score, and it
   > says so."
7. **Copy share link** → open it in a private window. It's read-only and needs no login.
   Mention that customer names and photos are not shared, and **Revoke link** stops it
   working.

### 2:45–3:20 · Architecture

Show the diagram in `docs/architecture.md`:

* Runs on **Huawei Cloud ECS**, with records in **RDS for MySQL**, sessions in **DCS
  Redis**, and notebook photos in **OBS**.
* AI sits behind provider interfaces: Huawei OCR/SIS or an LLM, with an offline rule
  engine so the system still works when a model is down.
* The AI extracts. Application code calculates. The human confirms.

Only show the Huawei console, `/api/health/dependencies` and the OBS object if the
deployment has actually been done (see `docs/deployment.md`). Don't claim it otherwise.

### 3:20–3:45 · Impact and scalability

> "Nothing in the core is specific to one city. Currency, language vocabulary, date
> format and thresholds are configuration. Adding a market's vocabulary is a JSON file,
> and the same flow works anywhere people keep handwritten business records."

Do **not** quote trader numbers, market sizes or impact statistics. None have been
measured.

### 3:45–4:00 · Closing

> "NotebookOS doesn't ask informal businesses to stop using the notebook they already
> trust. It makes that notebook computable."

---

## Fallbacks during the demo

| If… | Do |
|---|---|
| No internet | Everything above still works. The samples are read offline. |
| An uploaded real photo can't be read | The app says *"Automatic reading is temporarily unavailable…"*. Click **Enter transactions manually**. |
| Voice | Use *Demo samples → Voice note*, or *Typed entry*: `Musa 20k bashi` |
| State is messy | Capture → **Reset demo data** |

# Architecture

NotebookOS is a single web application with a clean internal split. It deliberately
avoids microservices: one FastAPI backend, one React frontend, and managed Huawei
Cloud data services.

## Production architecture (Huawei Cloud)

```mermaid
flowchart LR
  U[Trader phone<br/>browser] -->|HTTPS| ELB[Huawei ELB<br/>HTTPS listener]
  subgraph VPC[Huawei Cloud VPC]
    ELB --> ECS
    subgraph ECS[Huawei Cloud ECS]
      NGINX[nginx<br/>React static app<br/>/api reverse proxy] --> API[FastAPI backend<br/>uvicorn workers]
    end
    API --> RDS[(RDS for MySQL<br/>private subnet)]
    API --> DCS[(DCS for Redis<br/>private subnet)]
  end
  API --> OBS[(OBS bucket<br/>private)]
  API --> AI[AI pipeline providers<br/>Huawei OCR · Huawei SIS<br/>OpenAI-compatible LLM<br/>rule-based + offline fallback]
  RDS --> DASH[Dashboard metrics]
  RDS --> REPORT[Business report]
  OBS --> EVIDENCE[Evidence trace<br/>original photos]
```

| Huawei Cloud service | What it actually does in NotebookOS |
|---|---|
| **ECS** | Runs the two containers: nginx (frontend and `/api` proxy) and the FastAPI backend |
| **RDS for MySQL** | System of record: users, uploads, source pages, records, people, reports |
| **DCS for Redis** | Session tokens (hashed), OTP challenges, rate-limit counters, shared by all workers |
| **OBS** | Original notebook photos and voice notes. The bucket is private and files are streamed through the authenticated API. |
| **ELB** | Public HTTPS termination and health checks (`/health`) |
| **OCR / SIS** | Optional READ-stage providers behind `OCRProvider` and `SpeechProvider` |

## Backend modules

```
app/
  api/          HTTP routers (auth, uploads, records, dashboard, reports, meta, health)
  auth/         OTP + session service, auth/rate-limit dependencies
  core/         config, database, KV store (Redis/memory), file storage (local/OBS), logging
  models/       SQLAlchemy entities
  providers/    OCRProvider / SpeechProvider / LLMProvider interfaces + implementations
  extraction/   UNDERSTAND stage: vocab packs, normalisers, rule-based + LLM interpreters
  validation/   VALIDATE stage: deterministic checks, confidence levels, written-total check
  services/     pipeline orchestration, uploads, human-in-the-loop record operations
  analytics/    SUMMARIZE stage: pure, deterministic metric functions
  provenance/   record → source trace, serialisation
  reports/      report snapshot, narrative, share tokens
  demo/         fictional demo account seeding
```

## Data model

```mermaid
erDiagram
  users ||--o{ uploads : owns
  users ||--o{ records : owns
  users ||--o{ people : "debtors/customers"
  users ||--o{ reports : generates
  uploads ||--o{ source_pages : has
  uploads ||--o{ records : "extracted from"
  source_pages ||--o{ records : "evidence for"
  people ||--o{ records : "confirmed person"
```

* `records.status`: `AI_EXTRACTED` → `NEEDS_REVIEW` → `CONFIRMED` / `REJECTED`. **Only
  `CONFIRMED` records feed metrics and reports.**
* Provenance columns on `records`: `upload_id`, `source_page_id`, `source_reference`
  (`page-2-row-4`), `original_text`, `bbox_*` (fractions of the page), `confidence`,
  `field_confidence`, `ai_original` (the AI's untouched proposal, kept for audit), and
  `edited` / `confirmed_at`.
* `source_pages.lines` keeps every OCR line with its confidence and bounding box. These
  include lines that produced no record, such as headings and written totals.
* `reports.snapshot` freezes the figures at generation time, so a shared link stays stable.
* Primary keys are random UUIDs, which are not enumerable.

## AI pipeline

```mermaid
flowchart TD
  A[Photo / voice note / typed text] --> R{READ}
  R -->|photo| OCR[OCRProvider chain<br/>huawei → demo fixture]
  R -->|voice| STT[SpeechProvider chain<br/>huawei SIS → demo fixture]
  R -->|typed| TXT[Lines as typed]
  OCR --> L[Lines + confidence + bounding boxes]
  STT --> L
  TXT --> L
  L --> U{UNDERSTAND}
  U -->|LLM configured| LLM[LLMProvider<br/>strict JSON schema<br/>records must cite line ids]
  U -->|no LLM / failure / bad JSON| RULES[Rule-based interpreter<br/>vocab packs en + ha]
  LLM --> C[Candidate records<br/>nulls for unclear values]
  RULES --> C
  C --> V{VALIDATE}
  V --> V1[Required fields, types, dates,<br/>suspicious amounts]
  V --> V2[Amount and name must appear<br/>in the source text]
  V --> V3[Written total vs extracted sales]
  V1 & V2 & V3 --> RV[REVIEW: trader edits / confirms / rejects]
  RV -->|CONFIRMED only| S{SUMMARIZE}
  S --> M[Deterministic metrics<br/>Decimal arithmetic in code]
  M --> D[Dashboard + evidence]
  M --> REP[Report snapshot<br/>optional LLM wording, number-checked]
```

## User journey

```mermaid
journey
  title A trader's day with NotebookOS
  section Capture
    Writes sales and credit in notebook: 5: Trader
    Photographs the page: 4: Trader
  section Review
    Sees what the AI read, uncertain fields highlighted: 4: Trader
    Corrects an unclear quantity: 3: Trader
    Confirms the page: 5: Trader
  section Use
    Checks who owes money on the dashboard: 5: Trader
    Taps a number to see the original notebook line: 5: Trader
    Shares a read-only report link with a lender: 4: Trader, Lender
```

## Judge demo flow

```mermaid
sequenceDiagram
  participant J as Presenter
  participant FE as NotebookOS (browser)
  participant API as FastAPI on ECS
  participant DB as RDS MySQL
  J->>FE: Open demo account
  J->>FE: Upload Notebook A page 2
  FE->>API: POST /api/uploads/photo
  API-->>FE: 202 PROCESSING
  API->>API: READ → UNDERSTAND → VALIDATE (background task)
  FE->>API: poll GET /api/uploads/{id}
  API-->>FE: REVIEW + records (Musa 61%, quantity unclear)
  J->>FE: Edit quantity = 2, Confirm 5 records
  FE->>API: PATCH /api/records/{id}, POST /api/uploads/{id}/confirm
  API->>DB: status = CONFIRMED
  J->>FE: Dashboard → Outstanding Debt ₦40,000
  FE->>API: GET /api/dashboard/evidence/outstanding_debt
  API-->>FE: Musa (page 2 row 4) + Aisha (page 5 row 3) with source boxes
  J->>FE: Generate report → Copy share link
  FE->>API: POST /api/reports, GET /api/reports/{token} (public)
```

## Design decisions and assumptions

* **Monolith with background tasks.** Processing runs as a FastAPI background task, and
  the client polls the upload's status. That is enough for an MVP. A queue (for example
  Huawei DMS) can replace it without changing the API.
* **"Debt" means credit given to a customer.** `DEBT` records increase what customers
  owe the trader. `PAYMENT` records are repayments from customers. Money the trader owes
  suppliers is not modelled yet (use `EXPENSE`/`RESTOCK` or `OTHER`).
* **Total Sales means cash sales** (`SALE` records). Credit given is reported separately
  as *Credit Given*.
* **Outstanding debt** is per person: `max(credit − repayments, 0)`, summed. People are
  matched by case- and whitespace-insensitive name.
* **Dates** written as a page heading apply to the lines below them. A missing year is
  taken from the upload date, and that field is given lower confidence.
* **Editing a confirmed record** returns it to review. It must be confirmed again before
  it counts.
* **Deleting an upload** deletes its stored file and every record extracted from it. The
  UI warns how many confirmed records will be removed.

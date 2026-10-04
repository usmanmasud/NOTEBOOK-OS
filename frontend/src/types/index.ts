export type RecordType = "SALE" | "DEBT" | "EXPENSE" | "RESTOCK" | "PAYMENT" | "OTHER";
export type RecordStatus = "AI_EXTRACTED" | "NEEDS_REVIEW" | "CONFIRMED" | "REJECTED";
export type UploadStatus = "UPLOADED" | "PROCESSING" | "REVIEW" | "CONFIRMED" | "FAILED";
export type UploadType = "PHOTO" | "VOICE" | "TEXT";
export type ConfidenceLevel = "high" | "review" | "low";

export interface User {
  id: string;
  phone: string;
  name: string | null;
  business_name: string | null;
  is_demo: boolean;
}

export interface BBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Issue {
  field: string;
  code: string;
  message: string;
  severity: "error" | "warning";
}

export interface Source {
  upload_id: string;
  upload_type: UploadType | null;
  uploaded_at: string | null;
  original_filename: string | null;
  page_id: string | null;
  page_number: number | null;
  reference: string | null;
  original_text: string | null;
  bbox: BBox | null;
  has_image: boolean;
  read_by: string | null;
  read_is_demo_fixture: boolean;
  interpreted_by: string | null;
  seeded_demo_history: boolean;
}

export interface BusinessRecord {
  id: string;
  upload_id: string;
  date: string | null;
  type: RecordType | null;
  item: string | null;
  quantity: number | null;
  amount: number | null;
  person: string | null;
  notes: string | null;
  confidence: number;
  confidence_level: ConfidenceLevel;
  field_confidence: Record<string, number>;
  validation_issues: Issue[];
  human_fields: string[];
  manual_entry: boolean;
  ai_original: Record<string, unknown> | null;
  edited: boolean;
  status: RecordStatus;
  confirmed_at: string | null;
  source: Source;
}

export interface OcrLine {
  index: number;
  text: string;
  confidence: number;
  bbox: BBox | null;
}

export interface Page {
  id: string;
  page_number: number;
  width: number | null;
  height: number | null;
  has_image: boolean;
  lines: OcrLine[];
}

export interface TotalCheck {
  page_number: number;
  reference: string;
  written_total: string;
  extracted_sales: string;
  matches: boolean;
}

export interface Upload {
  id: string;
  type: UploadType;
  status: UploadStatus;
  original_filename: string | null;
  mime_type: string | null;
  has_file: boolean;
  raw_text?: string | null;
  error_message: string | null;
  pipeline: {
    read_provider?: string;
    read_is_demo_fixture?: boolean;
    interpreter?: string;
    interpreter_fallback_reason?: string | null;
    lines_read?: number;
    records_extracted?: number;
    records_flagged?: number;
    total_checks?: TotalCheck[];
    seeded_demo_history?: boolean;
  };
  created_at: string;
  processed_at: string | null;
  record_counts: Record<RecordStatus, number>;
  pages?: Page[];
}

export interface Metric {
  label: string;
  value: number;
}

export type MetricKey =
  | "total_sales"
  | "credit_given"
  | "debt_collected"
  | "outstanding_debt"
  | "total_expenses"
  | "stock_purchases"
  | "net_cash_flow"
  | "transactions";

export interface TrendPoint {
  period: string;
  sales: number;
  expenses: number;
  credit: number;
  collected: number;
}

export interface Pattern {
  kind: string;
  title: string;
  detail: string;
  record_ids: string[];
}

export interface Dashboard {
  period: { start: string | null; end: string | null };
  metrics: Record<MetricKey, Metric>;
  debtors: { person: string; credit_given: number; repaid: number; outstanding: number }[];
  stock: { item: string; in: number; out: number; net: number }[];
  items: { item: string; amount: number; count: number }[];
  trend: TrendPoint[];
  trend_granularity: "day" | "week";
  undated_records: number;
  recent: BusinessRecord[];
  pending_review: number;
  patterns: Pattern[];
  basis: string;
}

export interface Evidence {
  metric: MetricKey;
  label: string;
  value: number | null;
  person: string | null;
  explanation: string;
  records: BusinessRecord[];
}

export interface ReportSnapshot {
  business_name: string;
  owner_name: string | null;
  currency: string;
  locale: string;
  period: { start: string | null; end: string | null };
  metrics: Record<MetricKey, number>;
  repayment: { customers_with_balance: number; customers_fully_repaid: number };
  activity: {
    by_type: Record<string, { count: number; amount: number }>;
    first_date: string | null;
    last_date: string | null;
    active_days: number;
    undated_records: number;
  };
  trend: { period: string; sales: number; expenses: number }[];
  trend_granularity: "day" | "week";
  sources: {
    notebook_photos: number;
    voice_notes: number;
    typed_entries: number;
    records_corrected_by_trader: number;
    records_entered_manually: number;
    records_preloaded_demo_history?: number;
  };
  narrative: string;
  evidence_statement: string;
  disclaimer: string;
}

export interface Report {
  id: string;
  title: string;
  status: "ACTIVE" | "REVOKED";
  generated_at: string;
  revoked_at: string | null;
  snapshot: ReportSnapshot;
  share_token: string;
  share_url: string;
}

export interface PublicReport {
  title: string;
  generated_at: string;
  snapshot: ReportSnapshot;
}

export interface Sample {
  id: string;
  type: UploadType;
  title: string;
  mime_type: string;
}

export interface AppConfig {
  app_name: string;
  currency: string;
  locale: string;
  languages: string[];
  demo_mode: boolean;
  confidence: { high: number; review: number };
  providers: { ocr: string[]; speech: string[]; llm: string };
  limits: { photo_mb: number; voice_mb: number };
}

export type EditableFields = Partial<
  Pick<BusinessRecord, "date" | "type" | "item" | "quantity" | "amount" | "person" | "notes">
>;

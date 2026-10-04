import { describe, expect, it } from "vitest";
import { fieldFlag } from "../components/RecordCard";
import type { BusinessRecord } from "../types";
import { configureFormatting, levelFor, money, referenceLabel } from "./format";

const T = { high: 0.85, review: 0.6 };

function rec(over: Partial<BusinessRecord>): BusinessRecord {
  return {
    id: "r1", upload_id: "u1", date: null, type: "DEBT", item: null, quantity: null, amount: 20000, person: "Musa",
    notes: null, confidence: 0.61, confidence_level: "review", field_confidence: {}, validation_issues: [],
    human_fields: [], manual_entry: false, ai_original: {}, edited: false, status: "NEEDS_REVIEW", confirmed_at: null,
    source: {
      upload_id: "u1", upload_type: "PHOTO", uploaded_at: null, original_filename: null, page_id: null, page_number: 2,
      reference: "page-2-row-4", original_text: "Musa 20k bashi", bbox: null, has_image: true, read_by: null,
      read_is_demo_fixture: false, interpreted_by: "rules", seeded_demo_history: false,
    },
    ...over,
  };
}

describe("formatting", () => {
  it("formats money for the configured market", () => {
    configureFormatting({ currency: "NGN", locale: "en-NG" });
    expect(money(20000)).toContain("20,000");
    expect(money(null)).toBe("—");
    configureFormatting({ currency: "KES", locale: "en-KE" });
    expect(money(1500)).toContain("1,500");
    configureFormatting({ currency: "NGN", locale: "en-NG" });
  });

  it("maps confidence to levels using configurable thresholds", () => {
    expect(levelFor(0.9, T)).toBe("high");
    expect(levelFor(0.61, T)).toBe("review");
    expect(levelFor(0.3, T)).toBe("low");
  });

  it("renders provenance references for people", () => {
    expect(referenceLabel("page-2-row-4")).toBe("Page 2, row 4");
    expect(referenceLabel("manual-entry")).toBe("Typed by you");
  });
});

describe("field highlighting", () => {
  it("flags validation errors first", () => {
    const r = rec({ amount: null, validation_issues: [{ field: "amount", code: "missing", message: "", severity: "error" }] });
    expect(fieldFlag(r, "amount", T)).toBe("error");
  });
  it("flags unreadable values as low confidence", () => {
    expect(fieldFlag(rec({ field_confidence: { quantity: 0.2 } }), "quantity", T)).toBe("low");
  });
  it("flags uncertain values for review and leaves confident ones alone", () => {
    const r = rec({ field_confidence: { amount: 0.7, person: 0.95 } });
    expect(fieldFlag(r, "amount", T)).toBe("review");
    expect(fieldFlag(r, "person", T)).toBeNull();
  });
  it("marks human-corrected fields", () => {
    expect(fieldFlag(rec({ human_fields: ["quantity"], quantity: 2, field_confidence: { quantity: 0.2 } }), "quantity", T)).toBe("human");
  });
  it("does not flag absent optional fields", () => {
    expect(fieldFlag(rec({}), "item", T)).toBeNull();
  });
});

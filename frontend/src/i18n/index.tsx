/**
 * Minimal localisation. English is complete; other languages fall back to English
 * for any missing key, so a new language can be added one string at a time.
 * The Hausa strings are a starting point and need review by a native speaker.
 */
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

const en = {
  "type.SALE": "Sale",
  "type.DEBT": "Debt (credit given)",
  "type.EXPENSE": "Expense",
  "type.RESTOCK": "Restock",
  "type.PAYMENT": "Debt repayment",
  "type.OTHER": "Other",
  "short.SALE": "Sale",
  "short.DEBT": "Credit",
  "short.EXPENSE": "Expense",
  "short.RESTOCK": "Restock",
  "short.PAYMENT": "Repaid",
  "short.OTHER": "Other",
  "status.AI_EXTRACTED": "AI suggestion",
  "status.NEEDS_REVIEW": "Needs review",
  "status.CONFIRMED": "Confirmed",
  "status.REJECTED": "Rejected",
  "nav.capture": "Capture",
  "nav.history": "Records",
  "nav.dashboard": "Dashboard",
  "nav.report": "Report",
  "field.date": "Date",
  "field.type": "Type",
  "field.item": "Item",
  "field.quantity": "Quantity",
  "field.amount": "Amount",
  "field.person": "Person",
  "field.notes": "Notes",
  "action.confirm": "Confirm",
  "action.reject": "Reject",
  "action.edit": "Edit",
  "action.save": "Save",
  "action.cancel": "Cancel",
};

type Key = keyof typeof en;

const ha: Partial<Record<Key, string>> = {
  "type.SALE": "Sayarwa",
  "type.DEBT": "Bashi",
  "type.EXPENSE": "Kashe kuɗi",
  "type.RESTOCK": "Sayo kaya",
  "type.PAYMENT": "Biyan bashi",
  "type.OTHER": "Wani abu",
  "short.SALE": "Sayarwa",
  "short.DEBT": "Bashi",
  "status.CONFIRMED": "An tabbatar",
  "action.confirm": "Tabbatar",
  "action.cancel": "Soke",
};

const dictionaries: Record<string, Partial<Record<Key, string>>> = { en, ha };
export const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "ha", label: "Hausa (partial)" },
];

interface I18n {
  lang: string;
  setLang: (lang: string) => void;
  t: (key: Key) => string;
}

const Ctx = createContext<I18n>({ lang: "en", setLang: () => {}, t: (k) => en[k] });

function storedLang(): string {
  try {
    return localStorage.getItem("notebookos.lang") || "en";
  } catch {
    return "en";
  }
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState(storedLang);
  const setLang = useCallback((next: string) => {
    setLangState(next);
    try {
      localStorage.setItem("notebookos.lang", next);
    } catch {
      /* ignore */
    }
  }, []);
  const t = useCallback((key: Key) => dictionaries[lang]?.[key] ?? en[key], [lang]);
  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useI18n = () => useContext(Ctx);

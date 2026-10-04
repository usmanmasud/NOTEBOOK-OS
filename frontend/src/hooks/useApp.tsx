import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, onUnauthorized, session } from "../services/api";
import type { AppConfig, User } from "../types";
import { configureFormatting } from "../utils/format";

interface AppState {
  user: User | null;
  config: AppConfig | null;
  ready: boolean;
  signIn: (token: string, user: User) => void;
  signOut: () => Promise<void>;
  setUser: (user: User) => void;
}

const Ctx = createContext<AppState | null>(null);

const FALLBACK_CONFIG: AppConfig = {
  app_name: "NotebookOS",
  currency: "NGN",
  locale: "en-NG",
  languages: ["en"],
  demo_mode: false,
  confidence: { high: 0.85, review: 0.6 },
  providers: { ocr: [], speech: [], llm: "rules" },
  limits: { photo_mb: 10, voice_mb: 15 },
};

export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    api
      .config()
      .then((c) => {
        setConfig(c);
        configureFormatting(c);
      })
      .catch(() => setConfig(FALLBACK_CONFIG));
    if (!session.get()) {
      setReady(true);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch(() => session.set(null))
      .finally(() => setReady(true));
  }, []);

  useEffect(() => onUnauthorized(() => setUser(null)), []);

  const signIn = useCallback((token: string, u: User) => {
    session.set(token);
    setUser(u);
  }, []);

  const signOut = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      /* already signed out */
    }
    session.set(null);
    setUser(null);
  }, []);

  return (
    <Ctx.Provider value={{ user, config: config ?? FALLBACK_CONFIG, ready, signIn, signOut, setUser }}>
      {children}
    </Ctx.Provider>
  );
}

export function useApp(): AppState & { config: AppConfig } {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useApp outside AppProvider");
  return ctx as AppState & { config: AppConfig };
}

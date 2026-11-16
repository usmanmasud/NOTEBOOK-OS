import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, ApiError, onUnauthorized, session } from "../services/api";
import type { AppConfig, User } from "../types";
import { configureFormatting } from "../utils/format";

interface AppState {
  user: User | null;
  config: AppConfig | null;
  /** False until /api/config has answered (or every retry has failed). */
  configLoaded: boolean;
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
  login_methods: [],
  confidence: { high: 0.85, review: 0.6 },
  providers: { ocr: [], speech: [], llm: "rules" },
  limits: { photo_mb: 10, voice_mb: 15 },
};

/** Retry network failures and 5xx responses (up to ~30 s); client errors fail at once. */
async function withRetry<T>(fn: () => Promise<T>, cancelled: () => boolean, delays = [1000, 2000, 4000, 8000, 15000]): Promise<T> {
  for (let attempt = 0; ; attempt++) {
    try {
      return await fn();
    } catch (e) {
      // status 0 = network failure or timeout; 5xx = server trouble. Both are worth retrying.
      const retriable = !(e instanceof ApiError) || e.status === 0 || e.status >= 500;
      if (!retriable || attempt >= delays.length || cancelled()) throw e;
      await new Promise((r) => setTimeout(r, delays[attempt]));
    }
  }
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    // A cold server or a brief network drop must not leave the app without its settings
    // (no sign-in options) or sign the user out, so retry before giving up.
    withRetry(() => api.config(), () => cancelled)
      .then((c) => {
        if (cancelled) return;
        setConfig(c);
        configureFormatting(c);
      })
      .catch(() => !cancelled && setConfig(FALLBACK_CONFIG));
    if (!session.get()) {
      setReady(true);
      return;
    }
    withRetry(() => api.me(), () => cancelled)
      .then((u) => !cancelled && setUser(u))
      .catch((e) => {
        // Only a rejected session signs the user out; a network failure keeps it for next time.
        if (e instanceof ApiError && e.status === 401) session.set(null);
      })
      .finally(() => !cancelled && setReady(true));
    return () => {
      cancelled = true;
    };
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
    <Ctx.Provider value={{ user, config: config ?? FALLBACK_CONFIG, configLoaded: config !== null, ready, signIn, signOut, setUser }}>
      {children}
    </Ctx.Provider>
  );
}

export function useApp(): AppState & { config: AppConfig } {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useApp outside AppProvider");
  return ctx as AppState & { config: AppConfig };
}

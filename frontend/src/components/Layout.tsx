import { NavLink, Outlet } from "react-router-dom";
import { useApp } from "../hooks/useApp";
import { LANGUAGES, useI18n } from "../i18n";
import { Icon } from "./ui";

export function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="#14532d" />
      <path d="M9 8h12a2 2 0 0 1 2 2v14H11a2 2 0 0 1-2-2z" fill="#fefce8" />
      <path d="M12 13h8M12 17h8M12 21h5" stroke="#14532d" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function Layout() {
  const { user, signOut } = useApp();
  const { t, lang, setLang } = useI18n();
  const links = [
    { to: "/", label: t("nav.capture"), icon: Icon.camera, end: true },
    { to: "/records", label: t("nav.history"), icon: Icon.list },
    { to: "/dashboard", label: t("nav.dashboard"), icon: Icon.chart },
    { to: "/report", label: t("nav.report"), icon: Icon.doc },
  ];
  return (
    <div className="app">
      <header className="topbar">
        <NavLink to="/" className="brand">
          <BrandMark /> <span className="brand-name">NotebookOS</span>
        </NavLink>
        <nav className="desktop-nav" aria-label="Main">
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end}>
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="topbar-right">
          {user?.is_demo && (
            <span className="demo-pill" title="Demo account with fictional data">
              <span className="only-wide">Demo account · fictional data</span>
              <span className="only-narrow">Demo · fictional</span>
            </span>
          )}
          <label className="visually-hidden" htmlFor="lang">
            Language
          </label>
          <select id="lang" className="input btn-sm lang-select" style={{ width: "auto", minHeight: 34 }} value={lang} onChange={(e) => setLang(e.target.value)}>
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
          <button className="btn btn-ghost btn-sm" onClick={signOut}>
            Sign out
          </button>
        </div>
      </header>
      <main className="main">
        <Outlet />
      </main>
      <nav className="tabs" aria-label="Main">
        {links.map((l) => (
          <NavLink key={l.to} to={l.to} end={l.end}>
            <l.icon />
            {l.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

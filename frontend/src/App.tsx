import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Loading } from "./components/ui";
import { AppProvider, useApp } from "./hooks/useApp";
import { I18nProvider } from "./i18n";
import { Capture } from "./pages/Capture";
import { Dashboard } from "./pages/Dashboard";
import { MetricEvidence, RecordEvidence } from "./pages/Evidence";
import { Records } from "./pages/Records";
import { PublicReport, Reports } from "./pages/Reports";
import { Review } from "./pages/Review";
import { SignIn } from "./pages/SignIn";

function Routed() {
  const { user, ready } = useApp();
  if (!ready) return <Loading />;
  return (
    <Routes>
      {/* Public, read-only shared report: no login required. */}
      <Route path="/reports/:token" element={<PublicReport />} />
      {!user ? (
        <Route path="*" element={<SignIn />} />
      ) : (
        <Route element={<Layout />}>
          <Route index element={<Capture />} />
          <Route path="records" element={<Records />} />
          <Route path="uploads/:id" element={<Review />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="evidence/record/:recordId" element={<RecordEvidence />} />
          <Route path="evidence/:metric" element={<MetricEvidence />} />
          <Route path="report" element={<Reports />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      )}
    </Routes>
  );
}

export function App() {
  return (
    <I18nProvider>
      <AppProvider>
        <BrowserRouter>
          <Routed />
        </BrowserRouter>
      </AppProvider>
    </I18nProvider>
  );
}

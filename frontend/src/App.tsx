import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate, Link } from "react-router-dom";

import ErrorBanner from "./components/ErrorBanner";
import LoginPage from "./pages/LoginPage";
import InvoicesPage from "./pages/InvoicesPage";
import SurveyPage from "./pages/SurveyPage";
import ReportPage from "./pages/ReportPage";

import { API } from "./config";
import { AppContext, type AppContextType, type InvoiceItem, type ReportType, type Question, type AnswerValue } from "./context/AppContext";
import { dbGet, dbSet, dbClear } from "./utils/db";

const now = new Date();
const currentYear = now.getFullYear();
const currentMonth = now.getMonth() + 1;

export default function App() {
  return (
    <BrowserRouter>
      <AppProvider />
    </BrowserRouter>
  );
}

function AppProvider() {
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem("access_token") || "");
  const [refreshToken, setRefreshToken] = useState(() => localStorage.getItem("refresh_token") || "");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [startYear, setStartYear] = useState(String(currentYear));
  const [startMonth, setStartMonth] = useState(String(currentMonth - 2 > 0 ? currentMonth - 2 : 1).padStart(2, "0"));
  const [endYear, setEndYear] = useState(String(currentYear));
  const [endMonth, setEndMonth] = useState(String(currentMonth).padStart(2, "0"));
  const [year, setYear] = useState(String(currentYear));
  const [month, setMonth] = useState(String(currentMonth).padStart(2, "0"));
  const [items, setItems] = useState<InvoiceItem[]>([]);
  const [carrierId, setCarrierId] = useState("");
  const [email, setEmail] = useState("");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, AnswerValue>>({});
  const [report, setReport] = useState<ReportType | null>(null);
  const [qsSessionId, setQsSessionId] = useState("");
  const [error, setError] = useState("");
  const [appReady, setAppReady] = useState(false);

  useEffect(() => {
    localStorage.setItem("access_token", accessToken);
  }, [accessToken]);

  useEffect(() => {
    localStorage.setItem("refresh_token", refreshToken);
  }, [refreshToken]);

  useEffect(() => {
    if (items.length > 0) dbSet("items", items);
  }, [items]);

  const logout = () => {
    setAccessToken("");
    setRefreshToken("");
    setCarrierId("");
    setEmail("");
    setPhone("");
    setItems([]);
    setQuestions([]);
    setAnswers({});
    setReport(null);
    setQsSessionId("");
    dbClear();
  };

  useEffect(() => {
    (async () => {
      const stored = await dbGet<InvoiceItem[]>("items");
      if (stored) setItems(stored);

      let tok = localStorage.getItem("access_token");
      if (!tok) { setAppReady(true); return; }
      setAccessToken(tok);
      setRefreshToken(localStorage.getItem("refresh_token") || "");
      try {
        const me = await fetch(`${API}/scraper/me`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": `Bearer ${tok}` },
        });
        if (me.ok) {
          const info = await me.json() as { carrier_id?: string; email?: string; phone?: string };
          setCarrierId(info.carrier_id || "");
          setEmail(info.email || "");
          setPhone(info.phone || "");
          setAppReady(true);
          return;
        }
        const rt = localStorage.getItem("refresh_token");
        if (!rt) { logout(); setAppReady(true); return; }
        const ref = await fetch(`${API}/scraper/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: rt }),
        });
        if (!ref.ok) { logout(); setAppReady(true); return; }
        const data = await ref.json() as { access_token: string; refresh_token: string };
        tok = data.access_token;
        setAccessToken(tok);
        setRefreshToken(data.refresh_token);
        const me2 = await fetch(`${API}/scraper/me`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": `Bearer ${tok}` },
        });
        if (me2.ok) {
          const info = await me2.json() as { carrier_id?: string; email?: string; phone?: string };
          setCarrierId(info.carrier_id || "");
          setEmail(info.email || "");
          setPhone(info.phone || "");
        } else {
          logout();
        }
      } catch {
        logout();
      }
      setAppReady(true);
    })();
  }, []);

  const links = accessToken
    ? [
        { to: "/invoices" as const, label: "發票" },
        { to: "/survey" as const, label: "問卷" },
        { to: "/report" as const, label: "報告" },
      ].filter((l) => {
        if (l.to === "/survey") return questions.length > 0;
        if (l.to === "/report") return report;
        return true;
      })
    : [];

  async function refreshAccessToken() {
    const rt = refreshToken || localStorage.getItem("refresh_token");
    if (!rt) { logout(); return null; }
    try {
      const r = await fetch(`${API}/scraper/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: rt }),
      });
      if (!r.ok) { logout(); return null; }
      const data = await r.json() as { access_token: string; refresh_token: string };
      setAccessToken(data.access_token);
      setRefreshToken(data.refresh_token);
      return data;
    } catch {
      logout();
      return null;
    }
  }

  const ctx: AppContextType = {
    accessToken, setAccessToken,
    refreshToken, setRefreshToken,
    phone, setPhone,
    password, setPassword,
    loading, setLoading,
    startYear, setStartYear,
    startMonth, setStartMonth,
    endYear, setEndYear,
    endMonth, setEndMonth,
    year, setYear,
    month, setMonth,
    items, setItems,
    carrierId, setCarrierId,
    email, setEmail,
    questions, setQuestions,
    answers, setAnswers,
    report, setReport,
    qsSessionId, setQsSessionId,
    error, setError,
    refreshAccessToken,
    logout,
  };

  return (
    <AppContext.Provider value={ctx}>
      {!appReady ? (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="w-10 h-10 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
        </div>
      ) : (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white border-b border-gray-200">
          <div className="max-w-2xl mx-auto px-4 py-4 flex items-center justify-between">
            <div>
              <h1 className="text-lg font-semibold text-gray-800">
                AI 消費幸福感分析師
              </h1>
              <p className="text-sm text-gray-500">把你的發票變成幸福地圖</p>
            </div>
            {accessToken && (
              <div className="flex items-center gap-4">
                <nav className="flex items-center gap-3 mr-4">
                  {links.map((l) => (
                    <Link
                      key={l.to}
                      to={l.to}
                      className="text-sm text-gray-500 hover:text-gray-800 transition-colors"
                    >
                      {l.label}
                    </Link>
                  ))}
                </nav>
                <button
                  onClick={logout}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  登出
                </button>
              </div>
            )}
          </div>
        </header>
        <main className="max-w-2xl mx-auto px-4 py-8">
          <ErrorBanner />
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/invoices" element={<InvoicesPage />} />
            <Route path="/survey" element={<SurveyPage />} />
            <Route path="/report" element={<ReportPage />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </main>
      </div>
      )}
    </AppContext.Provider>
  );
}

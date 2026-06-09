import { useContext, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { AppContext } from "../context/AppContext";
import { API } from "../config";

const now = new Date();
const currentYear = now.getFullYear();
const currentMonth = now.getMonth() + 1;

interface MonthOption {
  y: string;
  m: string;
}

function monthOptions(): MonthOption[] {
  const opts: MonthOption[] = [];
  for (let y = currentYear; y >= currentYear - 1; y--) {
    for (let m = 12; m >= 1; m--) {
      if (y === currentYear && m > currentMonth) continue;
      opts.push({ y: String(y), m: String(m).padStart(2, "0") });
    }
  }
  return opts;
}

export default function HomePage() {
  const ctx = useContext(AppContext);
  const navigate = useNavigate();

  useEffect(() => {
    if (!ctx?.accessToken) navigate("/login", { replace: true });
  }, [ctx?.accessToken]);

  if (!ctx) return null;
  const { year, setYear, month, setMonth, loading, setLoading, setError,
          setItems, phone, carrierId, email,
          accessToken, refreshAccessToken, logout } = ctx;

  async function doFetch(path: string, body: Record<string, unknown>) {
    let tok = accessToken;
    const headers: Record<string, string> = { "Content-Type": "application/json", "Authorization": `Bearer ${tok}` };
    let r = await fetch(`${API}${path}`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
    if (r.status === 401) {
      const refreshed = await refreshAccessToken();
      if (!refreshed) { logout(); navigate("/login"); return null; }
      tok = localStorage.getItem("access_token") || "";
      r = await fetch(`${API}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${tok}` },
        body: JSON.stringify(body),
      });
    }
    return r;
  }

  async function handleScrape() {
    setLoading(true);
    setError("");
    try {
      const r = await doFetch("/scraper/invoices", { year, month });
      if (!r) return;
      if (!r.ok) {
        const errData = await r.json() as { detail?: string };
        throw new Error(errData.detail || "爬取失敗");
      }
      const data = await r.json() as { invoices: import("../context/AppContext").InvoiceItem[] };
      setItems(data.invoices);
      navigate("/invoices");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
    setLoading(false);
  }

  const months = monthOptions();

  return (
    <div className="space-y-4">
      {carrierId && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 text-sm text-gray-700 space-y-1">
          <div>手機號碼：{phone}</div>
          <div>手機條碼：{carrierId}</div>
          {email && <div>E-mail：{email}</div>}
        </div>
      )}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-medium text-gray-800 mb-1">選擇月份</h2>
        <p className="text-sm text-gray-500 mb-4">選擇要分析的發票月份</p>
        <div className="flex gap-3 items-end">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">年</label>
            <select
              value={year}
              onChange={(e) => setYear(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {[...new Set(months.map((m) => m.y))].map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">月</label>
            <select
              value={month}
              onChange={(e) => setMonth(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {months.filter((m) => m.y === year).map((m) => (
                <option key={m.m} value={m.m}>{m.m} 月</option>
              ))}
            </select>
          </div>
          <button
            onClick={handleScrape}
            disabled={loading}
            className="py-2 px-5 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "爬取中..." : "開始爬取"}
          </button>
        </div>
      </div>
    </div>
  );
}

import { useContext, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AppContext, type InvoiceItem } from "../context/AppContext";
import { API } from "../config";

export default function LoginPage() {
  const ctx = useContext(AppContext);
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    if (ctx?.accessToken) navigate("/invoices", { replace: true });
  }, [ctx?.accessToken]);

  if (!ctx) return null;
  const { phone, setPhone, password, setPassword,
          loading, setLoading, setError,
          setAccessToken, setRefreshToken,
          setCarrierId, setEmail,
          setItems } = ctx;

  async function handleLoginAndScrape() {
    if (!phone.trim() || !password.trim()) { setError("請輸入手機號碼與密碼"); return; }
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`${API}/scraper/login-and-scrape`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, password }),
      });
      if (!r.ok) {
        const errData = await r.json() as { detail?: string };
        throw new Error(errData.detail || "登入或爬取失敗");
      }
      const data = await r.json() as {
        access_token: string; refresh_token: string;
        carrier_id: string; email: string; phone: string;
        invoices: InvoiceItem[];
      };
      setAccessToken(data.access_token);
      setRefreshToken(data.refresh_token);
      setCarrierId(data.carrier_id);
      setEmail(data.email);
      setItems(data.invoices);
      navigate("/invoices");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
    setLoading(false);
  }

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-medium text-gray-800 mb-1">登入電子發票平台</h2>
        <p className="text-sm text-gray-500 mb-4">
          使用財政部電子發票手機條碼帳密登入，將自動爬取近三個月的發票資料
        </p>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">手機號碼</label>
            <input
              type="text"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="0912345678"
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">密碼</label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="請輸入密碼"
                className="w-full px-3 py-2 pr-10 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
              >
                {showPassword ? (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" /></svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                )}
              </button>
            </div>
          </div>
          <button
            onClick={handleLoginAndScrape}
            disabled={loading}
            className="w-full py-2 px-4 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "登入並爬取中..." : "登入並爬取發票"}
          </button>
        </div>
      </div>
    </div>
  );
}

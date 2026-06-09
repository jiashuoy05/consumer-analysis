import { useContext, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { AppContext } from "../context/AppContext";
import { API } from "../config";

export default function ReportPage() {
  const ctx = useContext(AppContext);
  const navigate = useNavigate();
  const [sendEmail, setSendEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [sentMsg, setSentMsg] = useState("");

  useEffect(() => {
    if (!ctx?.accessToken) navigate("/login", { replace: true });
  }, [ctx?.accessToken, navigate]);

  useEffect(() => {
    if (ctx?.email) setSendEmail(ctx.email);
  }, [ctx?.email]);

  if (!ctx) return null;
  const { report, accessToken, qsSessionId, email, setError } = ctx;

  if (!report) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-center">
        <p className="text-gray-500 mb-4">尚未產生報告，請先完成問卷</p>
        <button
          onClick={() => navigate("/survey")}
          className="px-6 py-2 bg-purple-600 text-white rounded text-sm font-medium hover:bg-purple-700"
        >
          前往問卷
        </button>
      </div>
    );
  }

  async function sendPdfReport() {
    if (!sendEmail) { setError("請輸入 Email 地址"); return; }
    const sid = qsSessionId;
    if (!sid) { setError("請先完成問卷"); return; }
    setSending(true);
    setSentMsg("");
    setError("");
    try {
      const r = await fetch(`${API}/report/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${accessToken}` },
        body: JSON.stringify({ session_id: sid, to_email: sendEmail }),
      });
      if (!r.ok) {
        const errData = await r.json() as { detail?: string };
        throw new Error(errData.detail || "寄送失敗");
      }
      const data = await r.json() as { message: string };
      setSentMsg(data.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
    setSending(false);
  }

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-medium text-gray-800 mb-3">你的消費幸福感報告</h2>

        <div className="prose prose-sm max-w-none text-gray-700 space-y-4">
          <div>
            <p className="text-gray-500">{report.summary}</p>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-green-700 mb-2">😊 幸福消費 Top 3</h3>
            <ol className="list-decimal list-inside space-y-1 text-sm">
              {report.happy_top3.map((item: string, i: number) => (
                <li key={i}>{item}</li>
              ))}
            </ol>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-red-700 mb-2">😰 壓力消費 Top 3</h3>
            <ol className="list-decimal list-inside space-y-1 text-sm">
              {report.stress_top3.map((item: string, i: number) => (
                <li key={i}>{item}</li>
              ))}
            </ol>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-blue-700 mb-2">💡 改善建議</h3>
            <ol className="list-decimal list-inside space-y-1 text-sm">
              {report.suggestions.map((item: string, i: number) => (
                <li key={i}>{item}</li>
              ))}
            </ol>
          </div>
        </div>

        <div className="mt-6 pt-4 border-t border-gray-200">
          <label className="block text-sm font-medium text-gray-700 mb-1">寄送至 Email（Markdown 報告）</label>
          <div className="flex gap-2">
            <input
              type="email"
              value={sendEmail}
              onChange={(e) => setSendEmail(e.target.value)}
              placeholder={email || "your@email.com"}
              className="flex-1 px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={sendPdfReport}
              disabled={sending}
              className="py-2 px-4 bg-purple-600 text-white rounded text-sm font-medium hover:bg-purple-700 disabled:opacity-50"
            >
              {sending ? "寄送中..." : "寄送報告"}
            </button>
          </div>
          {sentMsg && <p className="mt-1 text-sm text-green-600">{sentMsg}</p>}
        </div>

        <div className="mt-5">
          <button
            onClick={() => navigate("/invoices")}
            className="w-full py-2 px-4 bg-gray-100 text-gray-700 rounded text-sm font-medium hover:bg-gray-200"
          >
            ← 回發票
          </button>
        </div>
      </div>
    </div>
  );
}
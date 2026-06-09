import { useContext, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { AppContext } from "../context/AppContext";
import { API } from "../config";

export default function SurveyPage() {
  const ctx = useContext(AppContext);
  const navigate = useNavigate();

  useEffect(() => {
    if (!ctx?.accessToken) navigate("/login", { replace: true });
  }, [ctx?.accessToken]);

  if (!ctx) return null;
  const { questions, answers, setAnswers, loading, setLoading, setError,
          setReport, qsSessionId } = ctx;

  function updateAnswer(q: string, val: string) {
    setAnswers((prev) => ({ ...prev, [q]: val }));
  }

  async function submitSurvey() {
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`${API}/session/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: qsSessionId,
          answers: Object.entries(answers).map(([q, a]) => ({
            question: q,
            answer: a,
          })),
        }),
      });
      if (!r.ok) {
        const errData = await r.json() as { detail?: string };
        throw new Error(errData.detail || "生成報告失敗");
      }
      const data = await r.json() as { report: import("../context/AppContext").ReportType };
      setReport(data.report);
      navigate("/report");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
    setLoading(false);
  }

  const allAnswered = questions.length > 0 && questions.every((q) => answers[q]?.trim());

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-medium text-gray-800 mb-1">消費幸福感問卷</h2>
        <p className="text-sm text-gray-500 mb-4">
          根據你的消費記錄，請回答以下 {questions.length} 個問題
        </p>

        <div className="space-y-5">
          {questions.map((q, i) => (
            <div key={i}>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {i + 1}. {q}
              </label>
              <textarea
                value={answers[q] || ""}
                onChange={(e) => updateAnswer(q, e.target.value)}
                placeholder="請輸入你的想法..."
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
              />
            </div>
          ))}
        </div>
        <div className="mt-5 flex gap-3">
          <button
            onClick={() => navigate(-1)}
            className="flex-1 py-2 px-4 bg-gray-100 text-gray-700 rounded text-sm font-medium hover:bg-gray-200"
          >
            ← 上一頁
          </button>
          <button
            onClick={submitSurvey}
            disabled={loading || !allAnswered}
            className="flex-1 py-2 px-4 bg-purple-600 text-white rounded text-sm font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "生成報告中..." : "產生消費幸福感報告"}
          </button>
        </div>
      </div>
    </div>
  );
}

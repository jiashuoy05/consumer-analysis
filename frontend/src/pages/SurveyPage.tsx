import { useContext, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { AppContext, type Question, type AnswerValue } from "../context/AppContext";
import { API } from "../config";

interface QuestionProps {
  q: Question;
  value: AnswerValue;
  onChange: (v: AnswerValue) => void;
}

function TextQuestion({ value, onChange }: QuestionProps) {
  return (
    <textarea
      value={typeof value === "string" ? value : ""}
      onChange={(e) => onChange(e.target.value)}
      placeholder="請輸入你的想法..."
      rows={3}
      className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
    />
  );
}

function SingleChoiceQuestion({ q, value, onChange }: QuestionProps) {
  return (
    <div className="space-y-2">
      {q.options.map((opt, i) => (
        <label key={i} className="flex items-center gap-2 cursor-pointer">
          <input
            type="radio"
            name={q.id}
            value={opt}
            checked={value === opt}
            onChange={() => onChange(opt)}
            className="accent-purple-600"
          />
          <span className="text-sm text-gray-700">{opt}</span>
        </label>
      ))}
    </div>
  );
}

function MultipleChoiceQuestion({ q, value, onChange }: QuestionProps) {
  const arr = Array.isArray(value) ? (value as string[]) : [];
  function toggle(opt: string) {
    if (arr.includes(opt)) {
      onChange(arr.filter((x) => x !== opt));
    } else {
      onChange([...arr, opt]);
    }
  }
  return (
    <div className="space-y-2">
      {q.options.map((opt, i) => (
        <label key={i} className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            value={opt}
            checked={arr.includes(opt)}
            onChange={() => toggle(opt)}
            className="accent-purple-600"
          />
          <span className="text-sm text-gray-700">{opt}</span>
        </label>
      ))}
    </div>
  );
}

function RatingQuestion({ value, onChange }: QuestionProps) {
  const val = typeof value === "number" ? value : 0;
  const stars = [1, 2, 3, 4, 5];
  const labels = ["非常不滿意", "不滿意", "普通", "滿意", "非常滿意"];
  return (
    <div className="flex gap-2 flex-wrap items-center">
      {stars.map((s) => (
        <button
          key={s}
          type="button"
          onClick={() => onChange(s)}
          className={`w-10 h-10 rounded-full text-sm font-medium transition-colors ${
            val >= s
              ? "bg-purple-600 text-white"
              : "bg-gray-100 text-gray-500 hover:bg-gray-200"
          }`}
          title={labels[s - 1]}
        >
          {s}
        </button>
      ))}
      {val > 0 && <span className="text-sm text-gray-500 ml-2">{labels[val - 1]}</span>}
    </div>
  );
}

function LikertQuestion({ value, onChange }: QuestionProps) {
  const val = typeof value === "number" ? value : 0;
  const levels = [
    { v: 1, label: "非常不同意" },
    { v: 2, label: "不同意" },
    { v: 3, label: "普通" },
    { v: 4, label: "同意" },
    { v: 5, label: "非常同意" },
  ];
  return (
    <div className="flex gap-1 sm:gap-2 flex-wrap">
      {levels.map((l) => (
        <button
          key={l.v}
          type="button"
          onClick={() => onChange(l.v)}
          className={`px-3 py-2 rounded text-xs font-medium transition-colors ${
            val === l.v
              ? "bg-purple-600 text-white"
              : "bg-gray-100 text-gray-500 hover:bg-gray-200"
          }`}
        >
          {l.label}
        </button>
      ))}
    </div>
  );
}

function RankingQuestion({ q, value, onChange }: QuestionProps) {
  const ranked = Array.isArray(value) ? (value as string[]) : [];
  const unranked = q.options.filter((o) => !ranked.includes(o));

  function moveUp(idx: number) {
    if (idx <= 0) return;
    const next = [...ranked];
    [next[idx - 1], next[idx]] = [next[idx], next[idx - 1]];
    onChange(next);
  }
  function moveDown(idx: number) {
    if (idx >= ranked.length - 1) return;
    const next = [...ranked];
    [next[idx], next[idx + 1]] = [next[idx + 1], next[idx]];
    onChange(next);
  }
  function addItem(opt: string) {
    onChange([...ranked, opt]);
  }
  function removeItem(opt: string) {
    onChange(ranked.filter((x) => x !== opt));
  }

  return (
    <div className="space-y-2">
      {ranked.map((opt, i) => (
        <div key={opt} className="flex items-center gap-2 bg-purple-50 border border-purple-200 rounded px-3 py-2">
          <span className="w-5 h-5 rounded-full bg-purple-600 text-white text-xs flex items-center justify-center shrink-0">
            {i + 1}
          </span>
          <span className="text-sm text-gray-700 flex-1">{opt}</span>
          <button type="button" onClick={() => moveUp(i)} disabled={i === 0}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-30 p-1">▲</button>
          <button type="button" onClick={() => moveDown(i)} disabled={i === ranked.length - 1}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-30 p-1">▼</button>
          <button type="button" onClick={() => removeItem(opt)}
            className="text-red-400 hover:text-red-600 p-1">✕</button>
        </div>
      ))}
      {unranked.length > 0 && (
        <div className="flex gap-1 flex-wrap pt-1">
          {unranked.map((opt) => (
            <button key={opt} type="button" onClick={() => addItem(opt)}
              className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs hover:bg-gray-200">
              + {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

const QUESTION_RENDERERS: Record<string, React.FC<QuestionProps>> = {
  text: TextQuestion,
  single_choice: SingleChoiceQuestion,
  multiple_choice: MultipleChoiceQuestion,
  rating: RatingQuestion,
  ranking: RankingQuestion,
  likert: LikertQuestion,
};

export default function SurveyPage() {
  const ctx = useContext(AppContext);
  const navigate = useNavigate();

  useEffect(() => {
    if (!ctx?.accessToken) navigate("/login", { replace: true });
  }, [ctx?.accessToken, navigate]);

  if (!ctx) return null;
  const { questions, answers, setAnswers, loading, setLoading, setError, setReport, qsSessionId } = ctx;

  const updateAnswer = useCallback((qId: string, val: AnswerValue) => {
    setAnswers((prev) => ({ ...prev, [qId]: val }));
  }, [setAnswers]);

  const isAnswered = useCallback((q: Question): boolean => {
    const val = answers[q.id];
    if (q.type === "multiple_choice" || q.type === "ranking") {
      return Array.isArray(val) && (val as string[]).length > 0;
    }
    if (q.type === "rating" || q.type === "likert") {
      return typeof val === "number" && val > 0;
    }
    return typeof val === "string" && val.trim().length > 0;
  }, [answers]);

  const allAnswered = questions.length > 0 && questions.every((q) => !q.required || isAnswered(q));

  async function submitSurvey() {
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`${API}/session/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: qsSessionId,
          answers: questions.map((q) => ({
            question_id: q.id,
            question_text: q.text,
            question_type: q.type,
            answer: answers[q.id] ?? "",
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

  const typeLabels: Record<string, string> = {
    text: "文字回答",
    single_choice: "單選題",
    multiple_choice: "複選題",
    rating: "評分題",
    ranking: "排序題",
    likert: "量表題",
  };

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-medium text-gray-800 mb-1">消費幸福感問卷</h2>
        <p className="text-sm text-gray-500 mb-4">
          根據你的消費記錄，請回答以下 {questions.length} 個問題
        </p>

        <div className="space-y-6">
          {questions.map((q, i) => {
            const Renderer = QUESTION_RENDERERS[q.type];
            if (!Renderer) return null;
            return (
              <div key={q.id}>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {i + 1}. {q.text}
                  {q.required && <span className="text-red-400 ml-1">*</span>}
                  <span className="text-xs text-gray-400 ml-2 font-normal">({typeLabels[q.type] || q.type})</span>
                </label>
                <Renderer q={q} value={answers[q.id]} onChange={(v) => updateAnswer(q.id, v)} />
                {q.required && !isAnswered(q) && (
                  <p className="text-xs text-red-400 mt-1">此題為必答</p>
                )}
              </div>
            );
          })}
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
import { useContext, useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { AppContext, type InvoiceItem } from "../context/AppContext";
import { API } from "../config";
import downloadBlob from "../utils/downloadBlob";

export default function InvoicesPage() {
  const ctx = useContext(AppContext);
  const navigate = useNavigate();

  useEffect(() => {
    if (!ctx?.accessToken && !ctx?.items?.length) navigate("/login", { replace: true });
  }, [ctx?.accessToken, ctx?.items]);

  if (!ctx) return null;
  const { items,
          loading, setLoading, setError, setQuestions, setAnswers,
          setQsSessionId, setReport, phone, carrierId, email } = ctx;

  const allDates = useMemo(() => {
    const dates = items.map((it) => it.invDate).filter(Boolean).sort();
    return [...new Set(dates)];
  }, [items]);

  const [filterStart, setFilterStart] = useState("");
  const [filterEnd, setFilterEnd] = useState("");

  useEffect(() => {
    if (allDates.length > 0) {
      setFilterStart(allDates[0]);
      setFilterEnd(allDates[allDates.length - 1]);
    }
  }, [items]);

  const filtered = useMemo(() => {
    if (!filterStart) return items;
    return items.filter((it) => {
      const d = it.invDate || "";
      return d >= filterStart && d <= filterEnd;
    });
  }, [items, filterStart, filterEnd]);

  async function startSurvey() {
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`${API}/session/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items: filtered, year: filterStart?.substring(0, 4) || "", month: filterStart?.substring(4, 6) || "" }),
      });
      if (!r.ok) {
        const errData = await r.json() as { detail?: string };
        throw new Error(errData.detail || "啟動問卷失敗");
      }
      const data = await r.json() as { session_id: string; questions: string[] };
      setQsSessionId(data.session_id);
      const qMap: Record<string, string> = {};
      data.questions.forEach((q) => { qMap[q] = ""; });
      setQuestions(data.questions);
      setAnswers(qMap);
      setReport(null);
      navigate("/survey");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
    setLoading(false);
  }

  const [sortDir, setSortDir] = useState<"asc" | "desc" | null>(null);

  function toggleSort() {
    if (sortDir === null || sortDir === "desc") setSortDir("asc");
    else setSortDir("desc");
  }

  const sorted: InvoiceItem[] = [...filtered].sort((a, b) => {
    if (!sortDir) return 0;
    const da = parseInt(a.invDate, 10);
    const db = parseInt(b.invDate, 10);
    return sortDir === "asc" ? da - db : db - da;
  });

  function downloadCSV() {
    const header = "發票號碼,日期,品名,金額,商家";
    const rows = sorted.map((it) =>
      [
        it.invNum,
        it.invDate,
        `"${(it.description || "").replace(/"/g, '""')}"`,
        it.amount,
        `"${(it.sellerName || "").replace(/"/g, '""')}"`,
      ].join(",")
    );
    downloadBlob([header, ...rows].join("\n"), `invoices.csv`);
  }

  const total = filtered.reduce((s, i) => s + parseFloat(i.amount || "0"), 0);

function DateFilter({ items, filterStart, filterEnd, onChangeStart, onChangeEnd }: {
  items: InvoiceItem[]; filterStart: string; filterEnd: string;
  onChangeStart: (v: string) => void; onChangeEnd: (v: string) => void;
}) {
  const dateSet = useMemo(() => new Set(items.map((it) => it.invDate).filter(Boolean)), [items]);
  const allDatesSorted = useMemo(() => [...dateSet].sort(), [dateSet]);
  const years = useMemo(() => [...new Set(allDatesSorted.map((d) => d.substring(0, 4)))].sort(), [allDatesSorted]);

  const [sYear, setSYear] = useState(filterStart?.substring(0, 4) || "");
  const [sMonth, setSMonth] = useState(filterStart?.substring(4, 6) || "");
  const [sDay, setSDay] = useState(filterStart?.substring(6, 8) || "");
  const [eYear, setEYear] = useState(filterEnd?.substring(0, 4) || "");
  const [eMonth, setEMonth] = useState(filterEnd?.substring(4, 6) || "");
  const [eDay, setEDay] = useState(filterEnd?.substring(6, 8) || "");

  const allMonths = ["01","02","03","04","05","06","07","08","09","10","11","12"];

  function daysInMonth(y: string, m: string) {
    return new Date(parseInt(y), parseInt(m), 0).getDate();
  }
  function daysList(y: string, m: string) {
    const n = daysInMonth(y, m);
    return Array.from({ length: n }, (_, i) => String(i + 1).padStart(2, "0"));
  }

  const availSMonths = useMemo(() => sYear ? allMonths : [], [sYear]);
  const availSDays = useMemo(() => sYear && sMonth ? daysList(sYear, sMonth) : [], [sYear, sMonth]);
  const availEMonths = useMemo(() => eYear ? allMonths : [], [eYear]);
  const availEDays = useMemo(() => eYear && eMonth ? daysList(eYear, eMonth) : [], [eYear, eMonth]);

  function commitStart() {
    if (sYear && sMonth && sDay) {
      const d = sYear + sMonth + sDay;
      onChangeStart(d);
      if (d > filterEnd) { setEYear(sYear); setEMonth(sMonth); setEDay(sDay); onChangeEnd(d); }
    }
  }
  function commitEnd() {
    if (eYear && eMonth && eDay) onChangeEnd(eYear + eMonth + eDay);
  }

  interface SelProps { label: string; value: string; options: string[]; onChange: (v: string) => void; disabled?: boolean; }
  function DateSel({ label, value, options, onChange, disabled }: SelProps) {
    return (
      <div>
        <label className="block text-xs text-gray-500 mb-1">{label}</label>
        <select value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled}
          className="px-2 py-1.5 border border-gray-300 rounded text-sm disabled:opacity-40">
          <option value="">--</option>
          {options.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      </div>
    );
  }

  return (
    <div className="flex gap-6 mb-4 items-end flex-wrap">
      <div className="flex gap-2 items-end">
        <span className="text-xs text-gray-500 pb-1.5">開始</span>
        <DateSel label="年" value={sYear} options={years} onChange={(v) => { setSYear(v); setSMonth(""); setSDay(""); }} />
        <DateSel label="月" value={sMonth} options={availSMonths} onChange={(v) => { setSMonth(v); const first = availSDays.length ? availSDays[0] : ""; setSDay(first); if (sYear && v && first) onChangeStart(sYear + v + first); }} />
        <DateSel label="日" value={sDay} options={availSDays} onChange={(v) => { setSDay(v); if (sYear && sMonth && v) onChangeStart(sYear + sMonth + v); }} />
      </div>
      <div className="flex gap-2 items-end">
        <span className="text-xs text-gray-500 pb-1.5">結束</span>
        <DateSel label="年" value={eYear} options={years} onChange={(v) => { setEYear(v); setEMonth(""); setEDay(""); }} />
        <DateSel label="月" value={eMonth} options={availEMonths} onChange={(v) => { setEMonth(v); setEDay(""); }} />
        <DateSel label="日" value={eDay} options={availEDays} onChange={(v) => { setEDay(v); commitEnd(); }} />
      </div>
    </div>
  );
}

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
        {items.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500 mb-4">尚未取得發票資料，請先登入</p>
            <button
              onClick={() => navigate("/login")}
              className="px-6 py-2 bg-purple-600 text-white rounded text-sm font-medium hover:bg-purple-700"
            >
              前往登入
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-medium text-gray-800">
                發票明細共 {sorted.length} 筆
              </h2>
            </div>

            {allDates.length > 1 && (
              <DateFilter
                items={items}
                filterStart={filterStart}
                filterEnd={filterEnd}
                onChangeStart={setFilterStart}
                onChangeEnd={setFilterEnd}
              />
            )}

            <div className="overflow-x-auto max-h-96 overflow-y-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-gray-500">
                    <th className="text-left py-2 pr-2 font-medium">發票號碼</th>
                    <th className="text-left py-2 pr-2 font-medium cursor-pointer select-none" onClick={toggleSort}>
                      <span className="inline-flex items-center gap-1">
                        日期
                        <svg className="w-3.5 h-3.5 text-gray-400" viewBox="0 0 16 16" fill="currentColor">
                          {sortDir === "asc" ? (
                            <path d="M8 2l4 5H4z" />
                          ) : sortDir === "desc" ? (
                            <path d="M8 14l4-5H4z" />
                          ) : (
                            <><path d="M8 2l4 5H4z" opacity="0.4" /><path d="M8 14l4-5H4z" opacity="0.4" /></>
                          )}
                        </svg>
                      </span>
                    </th>
                    <th className="text-left py-2 pr-2 font-medium">品名</th>
                    <th className="text-right py-2 pr-2 font-medium">金額</th>
                    <th className="text-left py-2 font-medium">商家</th>
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((it, i) => (
                    <tr key={i} className="border-b border-gray-100">
                      <td className="py-2 pr-2 text-gray-800">{it.invNum}</td>
                      <td className="py-2 pr-2 text-gray-600">{it.invDate}</td>
                      <td className="py-2 pr-2 text-gray-600 truncate max-w-[180px]">{it.description}</td>
                      <td className="py-2 pr-2 text-right text-gray-800">NT$ {parseFloat(it.amount || "0").toLocaleString()}</td>
                      <td className="py-2 text-gray-600 truncate max-w-[150px]">{it.sellerName}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-4 text-sm text-gray-600">
              總金額 NT$ {total.toLocaleString()}
            </div>

            <div className="mt-4 flex gap-3">
              <button
                onClick={downloadCSV}
                disabled={items.length === 0}
                className="flex-1 py-2 px-4 bg-blue-600 text-white rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                下載 CSV
              </button>
              <button
                onClick={startSurvey}
                disabled={loading || sorted.length === 0}
                className="flex-1 py-2 px-4 bg-purple-600 text-white rounded text-sm font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? "分析中..." : "開始幸福感分析"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

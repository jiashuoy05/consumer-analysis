import os
from datetime import date
from typing import TypedDict, Optional
import uuid as uuid_lib
from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from tavily import TavilyClient

load_dotenv(Path(__file__).parent.parent / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

_tavily: Optional[TavilyClient] = None

def _get_tavily() -> Optional[TavilyClient]:
    global _tavily
    if _tavily is None and TAVILY_API_KEY:
        _tavily = TavilyClient(api_key=TAVILY_API_KEY)
    return _tavily

from backend.models.schemas import (
    ClassifiedExpense, HappinessReport, Question, QuestionType,
)


class GraphState(TypedDict):
    items: list[dict]
    classified: list[ClassifiedExpense]
    questions: list[Question]
    answers: dict
    report: Optional[HappinessReport]
    error: Optional[str]


def _get_llm():
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        api_key=GEMINI_API_KEY,
        temperature=0.7,
    )


def _has_valid_api_key() -> bool:
    return bool(GEMINI_API_KEY) and GEMINI_API_KEY != "your_gemini_api_key_here"


def classify_items_with_llm(items: list[str]) -> list[str]:
    if not items:
        return []
    if not _has_valid_api_key():
        return ["其他"] * len(items)

    items_text = "\n".join(f"{i+1}. {it}" for i, it in enumerate(items))
    prompt = f"""將以下商品分類至：食, 衣, 住, 行, 育, 樂 其中一個類別。

商品清單：
{items_text}

請逐項輸出類別，每行一個，不要編號、不要說明。"""

    llm = _get_llm()
    resp = llm.invoke(prompt)
    lines = [l.strip().rstrip(",.。") for l in resp.content.strip().split("\n") if l.strip()]

    results = []
    for i, item in enumerate(items):
        cat = lines[i] if i < len(lines) and lines[i] in "食衣住行育樂" else "其他"
        results.append(cat)
    return results


def classify_expenses_node(state: GraphState) -> dict:
    items = state.get("items", [])
    if not items:
        existing = state.get("classified")
        if existing:
            return {"classified": existing}
        return {"classified": []}

    descriptions = [it.get("description", "") for it in items]
    categories = classify_items_with_llm(descriptions)

    classified = []
    for it, cat in zip(items, categories):
        classified.append(ClassifiedExpense(
            category=cat,
            description=it.get("description", ""),
            amount=it.get("amount", "0"),
            sellerName=it.get("sellerName", ""),
            invDate=it.get("invDate", ""),
            invoiceTime="",
        ))
    return {"classified": classified}


_QUESTION_GEN_PROMPT = """你是一位 empathetic 的財務幸福感教練。以下是使用者的消費明細分類：

各類別總金額：
{cat_summary}

逐筆明細：
{items_str}

請根據以上的消費模式，產生 **8 個互動式問卷問題**，混合以下題型：
1. **text** — 開放式文字回答
2. **single_choice** — 單選題（提供 3~5 個選項）
3. **multiple_choice** — 複選題（提供 4~6 個選項）
4. **rating** — 評分題（1~5 分）
5. **likert** — 李克特量表（提供 5 個同意程度選項）
6. **ranking** — 排序題（提供 4~5 個項目排序）

問題要具體、個人化（參考實際消費項目），不要泛泛而談。
每題的 id 為 q_1 ~ q_8。
直接輸出 JSON 陣列，格式如下，不要其他說明：
[
  {{
    "id": "q_1",
    "text": "問題文字",
    "type": "text",
    "options": [],
    "required": true
  }},
  {{
    "id": "q_2",
    "text": "問題文字",
    "type": "single_choice",
    "options": ["選項1", "選項2", "選項3"],
    "required": true
  }}
]"""


def generate_questions_node(state: GraphState) -> dict:
    classified = state["classified"]
    # If we already have answers (report phase), preserve existing questions
    if state.get("answers") and state.get("questions"):
        return {"questions": state["questions"]}
    cat_totals = {}
    for exp in classified:
        cat_totals.setdefault(exp.category, 0)
        cat_totals[exp.category] += float(exp.amount)

    cat_summary = "\n".join(f"  {k}: 共 ${v:.0f}" for k, v in sorted(cat_totals.items()))
    items_str = "\n".join(
        f"  - {exp.sellerName}: {exp.description} ${exp.amount}"
        for exp in classified
    )

    prompt = _QUESTION_GEN_PROMPT.format(cat_summary=cat_summary, items_str=items_str)

    llm = _get_llm()
    resp = llm.invoke(prompt)
    content = resp.content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("\n", 1)[0]
        if content.endswith("```"):
            content = content[:-3]
    import json
    try:
        questions_data = json.loads(content)
    except json.JSONDecodeError:
        questions_data = json.loads(content.replace("'", '"'))
    questions = []
    for qd in questions_data[:8]:
        q_type = QuestionType(qd.get("type", "text"))
        questions.append(Question(
            id=qd.get("id", f"q_{len(questions)+1}"),
            text=qd["text"],
            type=q_type,
            options=qd.get("options", []),
            required=qd.get("required", True),
        ))
    return {"questions": questions}


def _fg(exp, key, default=""):
    if isinstance(exp, dict):
        return exp.get(key, default)
    return getattr(exp, key, default)


def generate_report_node(state: GraphState) -> dict:
    classified = state["classified"]
    answers = state["answers"]
    questions = state.get("questions", [])

    lines = []
    for exp in classified:
        lines.append(f"  [{_fg(exp, 'category')}] {_fg(exp, 'sellerName')} - {_fg(exp, 'description')} ${_fg(exp, 'amount')}")
    classified_str = "\n".join(lines)

    cat_totals = {}
    for exp in classified:
        cat = _fg(exp, "category", "其他")
        cat_totals[cat] = cat_totals.get(cat, 0) + float(_fg(exp, "amount", 0) or 0)

    qa_lines = []
    for q in questions:
        q_id = _fg(q, "id", str(q)) if not isinstance(q, dict) else q.get("id", str(q))
        q_text = _fg(q, "text", str(q)) if not isinstance(q, dict) else q.get("text", str(q))
        a_text = answers.get(q_id, "??")
        qa_lines.append(f"Q ({q_id}): {q_text}\nA: {a_text}")
    qa_text = "\n".join(qa_lines)

    market_info = ""
    tavily = _get_tavily()
    if tavily:
        try:
            year = date.today().year
            top_cat = max(cat_totals, key=cat_totals.get) if cat_totals else ""
            searches = [
                f"台灣 平均消費支出 {year} 統計",
                f"台灣 每人每月平均{top_cat}支出 {year}",
                f"台灣{top_cat}類 月平均花費 統計",
            ]
            results = []
            for q in searches:
                r = tavily.search(query=q, max_results=1)
                if r and "results" in r:
                    for item in r["results"][:1]:
                        results.append(f"- {item.get('title','')}: {item.get('content','')}")
            if results:
                market_info = "\n搜尋到的市場參考資料：\n" + "\n".join(results[:8])
        except Exception:
            pass

    prompt = f"""以下是使用者的消費明細分類與問卷回答，請根據這些資訊產生一份「消費幸福感報告」。

消費分類與金額：
{classified_str}

各類別總金額：
{chr(10).join(f'  {k}: 共 ${v:.0f}' for k, v in sorted(cat_totals.items()))}

問卷對話（包含題型與回答）：
{qa_text}
{market_info}

請輸出以下 JSON 格式（嚴格遵守，不要多加說明）：
{{
  "happy_top3": ["幸福消費 1 說明", "幸福消費 2 說明", "幸福消費 3 說明"],
  "stress_top3": ["壓力消費 1 說明", "壓力消費 2 說明", "壓力消費 3 說明"],
  "suggestions": ["改善建議 1", "改善建議 2", "改善建議 3"],
  "summary": "整體總結"
}}"""

    llm = _get_llm()
    llm_structured = llm.with_structured_output(HappinessReport)
    resp = llm_structured.invoke(prompt)
    return {"report": resp}


def build_graph() -> StateGraph:
    builder = StateGraph(GraphState)

    builder.add_node("classify_expenses", classify_expenses_node)
    builder.add_node("generate_questions", generate_questions_node)
    builder.add_node("generate_report", generate_report_node)

    builder.set_entry_point("classify_expenses")
    builder.add_edge("classify_expenses", "generate_questions")
    builder.add_edge("generate_questions", "generate_report")
    builder.add_edge("generate_report", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


async def run_question_phase(
    items: Optional[list[dict]] = None,
) -> dict:
    graph = build_graph()
    thread_id = str(uuid_lib.uuid4())

    config = {"configurable": {"thread_id": thread_id}}

    initial_state: GraphState = {
        "items": items or [],
        "classified": [],
        "questions": [],
        "answers": {},
        "report": None,
        "error": None,
    }

    result_questions: list[Question] = []
    result_classified = []

    async for event in graph.astream(initial_state, config):
        for node_name, state_data in event.items():
            if node_name == "classify_expenses":
                result_classified = state_data.get("classified", [])
            if node_name == "generate_questions":
                result_questions = state_data.get("questions", [])
                break

    return {
        "thread_id": thread_id,
        "questions": result_questions,
        "classified": result_classified,
    }


async def run_report_phase(thread_id: str, classified: list,
                           answers: dict, questions: list) -> HappinessReport:
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}

    state: GraphState = {
        "items": [],
        "classified": classified,
        "questions": questions,
        "answers": answers,
        "report": None,
        "error": None,
    }

    async for event in graph.astream(state, config):
        for node_name, state_data in event.items():
            if node_name == "generate_report":
                report = state_data.get("report")
                if report:
                    return report

    raise Exception("Failed to generate report")

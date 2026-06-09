import os
from typing import TypedDict, Optional
import uuid as uuid_lib
from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

load_dotenv(Path(__file__).parent.parent / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

from backend.models.schemas import (
    ClassifiedExpense, HappinessReport,
)


class GraphState(TypedDict):
    items: list[dict]
    classified: list[ClassifiedExpense]
    questions: list[str]
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


def generate_questions_node(state: GraphState) -> dict:
    classified = state["classified"]
    cat_totals = {}
    for exp in classified:
        cat_totals.setdefault(exp.category, 0)
        cat_totals[exp.category] += float(exp.amount)

    cat_summary = "\n".join(f"  {k}: 共 ${v:.0f}" for k, v in sorted(cat_totals.items()))
    items_str = "\n".join(
        f"  - {exp.sellerName}: {exp.description} ${exp.amount}"
        for exp in classified
    )

    prompt = f"""你是一位 empathetic 的財務幸福感教練。以下是使用者的消費明細分類：

各類別總金額：
{cat_summary}

逐筆明細：
{items_str}

請根據以上的消費模式，產生 **5 個互動式問卷問題**，目的是了解：
1. 使用者在各項支出中的主觀感受（值得 vs 後悔）
2. 哪些消費帶來快樂、哪些帶來壓力
3. 消費是否與個人價值觀一致

問題要具體、個人化（參考實際消費項目），不要泛泛而談。直接輸出 5 個問題，每個問題一行，不要編號。"""

    llm = _get_llm()
    resp = llm.invoke(prompt)
    questions = [q.strip() for q in resp.content.strip().split("\n") if q.strip()][:5]
    return {"questions": questions}


def generate_report_node(state: GraphState) -> dict:
    classified = state["classified"]
    answers = state["answers"]

    lines = []
    for exp in classified:
        lines.append(f"  [{exp.category}] {exp.sellerName} - {exp.description} ${exp.amount}")
    classified_str = "\n".join(lines)

    qa_text = "\n".join(
        f"Q: {q}\nA: {a}" for q, a in answers.items()
    )

    prompt = f"""以下是使用者的消費明細分類與問卷回答，請根據這些資訊產生一份「消費幸福感報告」。

消費分類與金額：
{classified_str}

問卷對話：
{qa_text}

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

    result_questions = []
    result_classified = []

    async for event in graph.astream(initial_state, config):
        for node_name, state_data in event.items():
            if node_name == "generate_questions":
                result_questions = state_data.get("questions", [])
                result_classified = state_data.get("classified", [])
                break

    return {
        "thread_id": thread_id,
        "questions": result_questions,
        "classified": result_classified,
    }


async def run_report_phase(thread_id: str, classified: list,
                           answers: dict) -> HappinessReport:
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}}

    state: GraphState = {
        "items": [],
        "classified": classified,
        "questions": list(answers.keys()),
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

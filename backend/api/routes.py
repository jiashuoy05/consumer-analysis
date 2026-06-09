import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from backend.services.llm_service import run_question_phase, run_report_phase
from backend.services.report_generator import send_email, format_report_markdown
from backend.models.schemas import QuestionnaireAnswer, Question

router = APIRouter()

_sessions: dict[str, dict] = {}


class InvoiceItem(BaseModel):
    invNum: str
    invDate: str
    description: str
    amount: str
    sellerName: str
    quantity: Optional[str] = ""
    unitPrice: Optional[str] = ""


class StartRequest(BaseModel):
    items: list[InvoiceItem] = []
    start_date: str = ""
    end_date: str = ""


class AnswerRequest(BaseModel):
    session_id: str
    answers: list[QuestionnaireAnswer]


class SendReportRequest(BaseModel):
    session_id: str
    to_email: str = ""


@router.post("/session/start")
async def start_session(req: StartRequest):
    try:
        result = await run_question_phase(
            items=[it.model_dump() for it in req.items],
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    questions = result["questions"]

    _sessions[result["thread_id"]] = {
        "classified": result["classified"],
        "questions": questions,
        "start_date": req.start_date,
        "end_date": req.end_date,
    }

    return {
        "session_id": result["thread_id"],
        "questions": [q.model_dump() for q in questions],
    }


@router.post("/session/answer")
async def submit_answers(req: AnswerRequest):
    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    answers_dict = {}
    for a in req.answers:
        answers_dict[a.question_id] = a.answer

    questions = session.get("questions", [])

    try:
        report = await run_report_phase(
            req.session_id,
            session["classified"],
            answers_dict,
            questions,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    session["answers"] = answers_dict
    session["report"] = report.model_dump()

    report_md = format_report_markdown(report.model_dump(), session["classified"], answers_dict, questions)

    return {"report": report.model_dump(), "report_md": report_md}


@router.post("/report/send")
async def send_report(req: SendReportRequest, authorization: str = Header(...)):
    from backend.api.scraper_routes import _get_session as get_scraper_session, _extract_token

    token = _extract_token(authorization)

    survey_sess = _sessions.get(req.session_id)
    if not survey_sess:
        raise HTTPException(status_code=404, detail="Survey session not found")

    classified = survey_sess.get("classified", [])
    answers = survey_sess.get("answers", {})
    report = survey_sess.get("report", {})

    if not report:
        raise HTTPException(status_code=400, detail="Report not yet generated, please submit answers first")

    scraper_sess = get_scraper_session(token)
    user_email = req.to_email or scraper_sess.get("email", "")

    if not user_email:
        raise HTTPException(status_code=400, detail="No email found for this account, please provide to_email")

    sd, ed = survey_sess.get("start_date", ""), survey_sess.get("end_date", "")
    period = f"{sd}-{ed}" if sd and ed else ""

    questions = survey_sess.get("questions", [])
    report_md = format_report_markdown(report, classified, answers, questions, period)
    send_email(user_email, report_md, period=period)

    return {
        "success": True,
        "message": f"報告已寄送至 {user_email}",
    }

import os
import uuid as uuid_lib
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.services.llm_service import run_question_phase, run_report_phase
from backend.services.report_generator import (
    generate_pie_chart,
    create_report_docx,
    create_report_pdf,
    send_email,
    cleanup,
)
from backend.models.schemas import QuestionnaireAnswer

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
    year: str = ""
    month: str = ""


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

    _sessions[result["thread_id"]] = {
        "classified": result["classified"],
        "questions": result["questions"],
        "year": req.year,
        "month": req.month,
    }

    return {
        "session_id": result["thread_id"],
        "questions": result["questions"],
    }


@router.post("/session/answer")
async def submit_answers(req: AnswerRequest):
    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    answers_dict = {a.question: a.answer for a in req.answers}

    try:
        report = await run_report_phase(
            req.session_id,
            session["classified"],
            answers_dict,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    session["answers"] = answers_dict
    session["report"] = report.model_dump()

    return {"report": report.model_dump()}


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

    chart_path = None
    pdf_path = None
    docx_path = None

    y, m = survey_sess.get("year", ""), survey_sess.get("month", "")
    period = f"{y}-{m}" if y and m else ""

    try:
        chart_path = generate_pie_chart(classified)
        docx_path = create_report_docx(report, classified, answers, chart_path, period)
        pdf_path = create_report_pdf(report, classified, answers, chart_path, period)
        send_email(user_email, pdf_path, period=period)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

    survey_sess["docx_path"] = docx_path
    survey_sess["pdf_path"] = pdf_path

    return {
        "success": True,
        "message": f"報告已寄送至 {user_email}",
        "download_url": f"/report/download/{req.session_id}/docx",
    }


@router.get("/report/download/{session_id}/{fmt}")
async def download_report(session_id: str, fmt: str):
    if fmt not in ("docx", "pdf"):
        raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}")

    sess = _sessions.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    report = sess.get("report")
    if not report:
        raise HTTPException(status_code=400, detail="Report not yet generated, please submit answers first")

    classified = sess.get("classified", [])
    answers = sess.get("answers", {})

    ym = f"{sess.get('year', '')}-{sess.get('month', '')}"
    period = ym if ym and ym != "-" else ""
    prefix = f"{ym}_" if period else ""

    path = sess.get(f"{fmt}_path")
    if not path or not os.path.exists(path):
        try:
            chart_path = generate_pie_chart(classified)
            if fmt == "docx":
                path = create_report_docx(report, classified, answers, chart_path, period)
            else:
                path = create_report_pdf(report, classified, answers, chart_path, period)
            sess[f"{fmt}_path"] = path
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

    if fmt == "docx":
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"{prefix}happiness_report.docx"
    else:
        media_type = "application/pdf"
        filename = f"{prefix}happiness_report.pdf"

    return FileResponse(path, media_type=media_type, filename=filename)


@router.get("/health")
async def health():
    return {"status": "ok"}


import time
import uuid as uuid_lib

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from backend.services.scraper import login_and_scrape, validate_login


router = APIRouter()

_sessions: dict[str, dict] = {}

ACCESS_TTL = 1800       # 30 min
REFRESH_TTL = 86400     # 1 day


class LoginRequest(BaseModel):
    phone: str
    password: str


class ScrapeRequest(BaseModel):
    start_year: str = ""
    start_month: str = ""
    end_year: str = ""
    end_month: str = ""


class LoginAndScrapeRequest(BaseModel):
    phone: str
    password: str
    start_year: str = ""
    start_month: str = ""
    end_year: str = ""
    end_month: str = ""


class RefreshRequest(BaseModel):
    refresh_token: str


class MeRequest(BaseModel):
    pass


def _now():
    return time.time()


@router.post("/scraper/login")
async def login(req: LoginRequest):
    try:
        user_info = await validate_login(req.phone, req.password, headless=True)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

    session_id = str(uuid_lib.uuid4())
    refresh_token = str(uuid_lib.uuid4())
    now = _now()

    _sessions[session_id] = {
        "phone": req.phone,
        "password": req.password,
        "carrier_id": user_info.get("carrier_id", ""),
        "email": user_info.get("email", ""),
        "created_at": now,
        "refresh_token": refresh_token,
    }

    return {
        "access_token": session_id,
        "refresh_token": refresh_token,
        "expires_in": ACCESS_TTL,
        "carrier_id": user_info.get("carrier_id", ""),
        "email": user_info.get("email", ""),
        "phone": user_info.get("phone", ""),
    }


@router.post("/scraper/login-and-scrape")
async def login_and_scrape_endpoint(req: LoginAndScrapeRequest):
    try:
        result = await login_and_scrape(
            req.phone, req.password, headless=True,
            start_year=req.start_year, start_month=req.start_month,
            end_year=req.end_year, end_month=req.end_month,
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

    session_id = str(uuid_lib.uuid4())
    refresh_token = str(uuid_lib.uuid4())
    now = _now()

    _sessions[session_id] = {
        "phone": req.phone,
        "password": req.password,
        "carrier_id": result.get("carrier_id", ""),
        "email": result.get("email", ""),
        "created_at": now,
        "refresh_token": refresh_token,
    }

    return {
        "access_token": session_id,
        "refresh_token": refresh_token,
        "expires_in": ACCESS_TTL,
        "carrier_id": result.get("carrier_id", ""),
        "email": result.get("email", ""),
        "phone": result.get("phone", ""),
        "invoices": result["invoices"],
        "total": len(result["invoices"]),
    }


@router.post("/scraper/refresh")
async def refresh(req: RefreshRequest):
    for sid, sess in _sessions.items():
        if sess.get("refresh_token") == req.refresh_token:
            if _now() - sess.get("created_at", 0) > REFRESH_TTL:
                del _sessions[sid]
                raise HTTPException(status_code=401, detail="Refresh token expired, please login again")

            new_sid = str(uuid_lib.uuid4())
            _sessions[new_sid] = sess
            _sessions[new_sid]["created_at"] = _now()
            _sessions[new_sid]["refresh_token"] = str(uuid_lib.uuid4())
            del _sessions[sid]

            return {
                "access_token": new_sid,
                "refresh_token": _sessions[new_sid]["refresh_token"],
                "expires_in": ACCESS_TTL,
            }

    raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/scraper/me")
async def get_me(authorization: str = Header(...)):
    token = _extract_token(authorization)
    session = _get_session(token)
    return {
        "carrier_id": session.get("carrier_id", ""),
        "email": session.get("email", ""),
        "phone": session.get("phone", ""),
    }


def _extract_token(authorization: str) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    return authorization[len("Bearer "):]


def _get_session(access_token: str) -> dict:
    sess = _sessions.get(access_token)
    if not sess:
        raise HTTPException(status_code=401, detail="Access token not found")
    if _now() - sess.get("created_at", 0) > ACCESS_TTL:
        del _sessions[access_token]
        raise HTTPException(status_code=401, detail="Access token expired, please refresh")
    return sess


@router.post("/scraper/invoices")
async def scrape_invoices(req: ScrapeRequest, authorization: str = Header(...)):
    token = _extract_token(authorization)
    session = _get_session(token)

    try:
        result = await login_and_scrape(
            session["phone"], session["password"], headless=True,
            start_year=req.start_year, start_month=req.start_month,
            end_year=req.end_year, end_month=req.end_month,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "success": True,
        "invoices": result["invoices"],
        "total": len(result["invoices"]),
        "carrier_id": result.get("carrier_id", ""),
        "email": result.get("email", ""),
        "phone": result.get("phone", ""),
    }

"""
app/routers/startup.py
----------------------
Startup page must require login.

How we check login:
- Read cookie: SESSION_COOKIE_NAME (tt_session)
- Unsign it to get session_uuid
- If missing/invalid -> redirect to /login
"""

import os
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from app.settings import settings
from core.session import unsign_session_token

from repo.config_repo import get_app_title
from core.auth_context import get_current_user
from repo.provider_repo import list_active_llm_providers, get_active_default_llm_provider

load_dotenv()

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "tt_session")


@router.get("/", response_class=HTMLResponse)
def startup_page(request: Request):
    """
    GET /

    If user has valid signed session cookie -> show startup.html
    Else -> redirect /login
    """
    token = request.cookies.get(COOKIE_NAME)
    session_uuid = unsign_session_token(token) if token else None

    if not session_uuid:
        return RedirectResponse(url="/login", status_code=302)

    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    providers = list_active_llm_providers()
    default_provider = get_active_default_llm_provider()
    default_provider_code = (default_provider or {}).get("provider_code") or ""

    return templates.TemplateResponse(
        "startup.html",
        {
            "request": request,
            "title": get_app_title(),
            "current_user": user,
            "llm_providers": providers,
            "default_llm_provider_code": default_provider_code,
        },
    )

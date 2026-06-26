"""
app/routers/auth.py
-------------------
DB-backed login implementation.

Flow (Browser -> FastAPI -> DB -> Cookie -> Redirect):

1) Browser GET /login
   -> login_page() returns login.html

2) Browser POST /login (form submit)
   -> login_submit() reads form fields (username/password)
   -> repo.user_repo.get_user_by_username() checks DB
   -> repo.session_repo.create_chat_session() inserts chat_session row
   -> core.session.sign_session_uuid() creates signed cookie token
   -> Set cookie in response, redirect to "/"
"""

import os
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from repo.user_repo import get_user_by_username
from repo.session_repo import create_chat_session
from core.session import sign_session_uuid

load_dotenv()

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "tt_session")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """
    GET /login -> renders login.html

    Jinja2 variables:
      - title -> shown on page
      - error -> shown only if not None
    """
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "title": "Login", "error": None},
    )


@router.post("/login")
async def login_submit(request: Request):
    """
    POST /login

    Reads HTML form values:
      <input name="username"> -> form["username"]
      <input name="password"> -> form["password"]

    Then:
      - validate user in DB
      - create chat_session
      - set signed cookie
      - redirect to "/"
    """
    form = await request.form()
    username = (form.get("username") or "").strip()
    password = (form.get("password") or "").strip()

    # 1) DB lookup user
    user = get_user_by_username(username)

    # 2) Validate user exists + active
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "title": "Login", "error": "User not found"},
            status_code=401,
        )

    if int(user.get("is_active") or 0) != 1:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "title": "Login", "error": "User is inactive"},
            status_code=401,
        )

    # 3) Password check (temporary)
    # Your DB currently has blank password_hash.
    # Industry best practice (later): store bcrypt hash and verify properly.
    # 3) Password check (bcrypt-based)
    pw_hash = (user.get("password_hash") or "").strip()

    # If password hash is missing, user setup is incomplete
    if not pw_hash:
        return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "title": "Login",
            "error": "Password is not set for this user. Contact administrator.",
        },
        status_code=401,
    )

    from core.passwords import verify_password

    if not verify_password(password, pw_hash):
        return templates.TemplateResponse(
        "login.html",
        {"request": request, "title": "Login", "error": "Invalid password"},
        status_code=401,
    )

    # 4) Create chat session row
    # interaction_mode is locked to GUI/LLM. On login we default to GUI.
    sess = create_chat_session(user_id=int(user["user_id"]), interaction_mode="GUI")

    # 5) Sign session_uuid and store in cookie
    token = sign_session_uuid(sess["session_uuid"])

    # 6) Redirect to startup page
    resp = RedirectResponse(url="/", status_code=302)

    # Cookie details:
    # - httponly=True means JS cannot read it (more secure)
    # - samesite="lax" good default for normal web apps
    resp.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
    )

    return resp

@router.get("/logout")
def logout(request: Request):
    """
    GET /logout

    Data flow:
    - Browser calls /logout
    - We read signed cookie token (tt_session)
    - core.session.unsign_session_token(token) returns session_uuid OR None
    - If session_uuid exists, close session in DB
    - Clear cookie
    - Redirect to /login
    """
    token = request.cookies.get(COOKIE_NAME)

    # Convert signed cookie token -> session_uuid
    from core.session import unsign_session_token
    session_uuid = unsign_session_token(token) if token else None

    # If cookie is valid, close session in DB
    if session_uuid:
        from repo.session_repo import close_chat_session_by_uuid
        close_chat_session_by_uuid(session_uuid)

    # Always clear cookie (even if invalid) and redirect to login
    resp = RedirectResponse(url="/login", status_code=302)

    # delete_cookie removes cookie from browser
    resp.delete_cookie(key=COOKIE_NAME)

    return resp

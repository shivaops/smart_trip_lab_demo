"""
app/routers/profile.py
----------------------
Traveler CRUD page.

Primary route:
- /travelers

Legacy compatibility:
- /profile still works and redirects / posts into /travelers flow

This router uses the NEW user_travel_document table only.
No dependency on:
- user_preference
- travel_doc_type_rule
- old preference/travel-doc repos
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import datetime
import re

from core.auth_context import get_current_user
from repo.config_repo import get_app_title
from repo.travelers_repo import (
    list_travelers,
    get_traveler_by_id,
    insert_traveler,
    update_traveler,
    toggle_traveler_active,
    set_primary_traveler,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _parse_date(value: str):
    s = (value or "").strip()
    if not s:
        return None
    try:
        return datetime.date.fromisoformat(s)
    except Exception:
        return None


def _full_years_between(dob: datetime.date, ref: datetime.date) -> int:
    years = ref.year - dob.year
    if (ref.month, ref.day) < (dob.month, dob.day):
        years -= 1
    return years


def _validate_traveler_form(form_data: dict) -> str | None:
    today = datetime.date.today()

    required_labels = [
        ("traveler_type", "Traveller Type"),
        ("document_type", "Document Type"),
        ("document_number", "Document Number"),
        ("first_name", "First Name"),
        ("last_name", "Last Name"),
        ("date_of_birth", "Date of Birth"),
        ("gender", "Gender"),
        ("nationality_iso2", "Nationality"),
        ("issuing_country_iso2", "Issuing Country"),
        ("issue_date", "Issue Date"),
        ("expiry_date", "Expiry Date"),
    ]
    for key, label in required_labels:
        if not str(form_data.get(key) or "").strip():
            return f"{label} is required."

    first_name = str(form_data.get("first_name") or "").strip()
    last_name = str(form_data.get("last_name") or "").strip()
    if not re.fullmatch(r"[A-Za-z][A-Za-z .'-]{0,49}", first_name):
        return "First Name must start with a letter and contain only letters, spaces, apostrophe, dot or hyphen."
    if not re.fullmatch(r"[A-Za-z][A-Za-z .'-]{0,49}", last_name):
        return "Last Name must start with a letter and contain only letters, spaces, apostrophe, dot or hyphen."

    for key, label in [("issuing_country_iso2", "Issuing Country"), ("nationality_iso2", "Nationality")]:
        value = str(form_data.get(key) or "").strip().upper()
        if len(value) != 2 or not value.isalpha():
            return f"{label} must be 2 letters (example: IN)."

    dob = _parse_date(form_data.get("date_of_birth") or "")
    if not dob:
        return "Date of Birth must be a valid date."
    if dob > today:
        return "Date of Birth cannot be in the future."

    issue_date = _parse_date(form_data.get("issue_date") or "")
    if not issue_date:
        return "Issue Date must be a valid date."

    expiry_date = _parse_date(form_data.get("expiry_date") or "")
    if not expiry_date:
        return "Expiry Date must be a valid date."

    if issue_date > today:
        return "Issue Date cannot be in the future."
    if expiry_date <= today:
        return "Travel document is already expired or expires today. Please enter a valid future expiry date."
    if issue_date > expiry_date:
        return "Issue Date cannot be later than Expiry Date."

    traveler_type = str(form_data.get("traveler_type") or "").strip().title()
    age = _full_years_between(dob, today)
    if traveler_type == "Infant" and age >= 2:
        return "Infant Date of Birth is not valid. Infant age must be below 2 years."
    if traveler_type == "Child" and (age < 2 or age >= 12):
        return "Child Date of Birth is not valid. Child age must be between 2 and 11 years."
    if traveler_type == "Adult" and age < 12:
        return "Adult Date of Birth is not valid. Adult age must be 12 years or above."

    email = str(form_data.get("email") or "").strip()
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return "Email format is invalid."

    phone = str(form_data.get("phone") or "").strip()
    if phone and not re.fullmatch(r"\+?[0-9]{6,20}", phone):
        return "Phone must contain only digits with optional leading + and length between 6 and 20."

    return None


def _blank_form() -> dict:
    return {
        "document_id": "",
        "return_to": "",
        "agent_fsr_id": "",
        "traveler_type": "Adult",
        "document_type": "Passport",
        "document_number": "",
        "issuing_country_iso2": "",
        "issue_date": "",
        "expiry_date": "",
        "first_name": "",
        "last_name": "",
        "date_of_birth": "",
        "gender": "",
        "nationality_iso2": "",
        "email": "",
        "phone": "",
        "phone_iso_code": "",
        "phone_std_code": "",
        "preferred_currency": "INR",
        "preferred_language": "en",
        "seat_preference": "Any",
        "meal_preference": "Standard",
        "notify_email": "1",
        "notify_sms": "0",
        "is_primary": "",
        "is_active": "1",
    }


def _render_page(
    request: Request,
    current_user: dict,
    form_data: dict | None = None,
    edit_mode: bool = False,
    page_msg: str | None = None,
    page_error: str | None = None,
    status_code: int = 200,
):
    user_id = int(current_user["user_id"])
    travelers = list_travelers(user_id)
    effective_form = form_data or _blank_form()

    return templates.TemplateResponse(
        "travelers.html",
        {
            "request": request,
            "title": get_app_title(),
            "current_user": current_user,
            "travelers": travelers,
            "form_data": effective_form,
            "edit_mode": edit_mode,
            "page_msg": page_msg,
            "page_error": page_error,
            "return_to": effective_form.get("return_to", ""),
            "traveler_type_options": ["Adult", "Child", "Infant"],
            "document_type_options": ["Passport", "Visa", "National ID", "Driving License"],
            "gender_options": ["Male", "Female", "Other"],
            "currency_options": ["INR", "USD", "BHD", "AED", "EUR", "GBP"],
            "language_options": ["en", "hi", "ar"],
            "seat_options": ["Window", "Aisle", "Any"],
            "meal_options": ["Standard", "Vegetarian", "Vegan", "Halal", "Kosher", "Diabetic"],
        },
        status_code=status_code,
    )


def _load_travelers_page(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)

    edit_id = request.query_params.get("edit_id")
    page_msg = request.query_params.get("msg")
    page_error = request.query_params.get("error")
    return_to = (request.query_params.get("return_to") or "").strip()
    agent_fsr_id = (request.query_params.get("agent_fsr_id") or "").strip()

    form_data = _blank_form()
    form_data["return_to"] = return_to
    form_data["agent_fsr_id"] = agent_fsr_id
    edit_mode = False

    if edit_id:
        row = get_traveler_by_id(int(current_user["user_id"]), int(edit_id))
        if row:
            edit_mode = True
            form_data = {
                "document_id": str(row.get("document_id") or ""),
                "return_to": return_to,
                "agent_fsr_id": agent_fsr_id,
                "traveler_type": str(row.get("traveler_type") or "Adult"),
                "document_type": str(row.get("document_type") or "Passport"),
                "document_number": str(row.get("document_number") or ""),
                "issuing_country_iso2": str(row.get("issuing_country_iso2") or ""),
                "issue_date": str(row.get("issue_date") or ""),
                "expiry_date": str(row.get("expiry_date") or ""),
                "first_name": str(row.get("first_name") or ""),
                "last_name": str(row.get("last_name") or ""),
                "date_of_birth": str(row.get("date_of_birth") or ""),
                "gender": str(row.get("gender") or ""),
                "nationality_iso2": str(row.get("nationality_iso2") or ""),
                "email": str(row.get("email") or ""),
                "phone": str(row.get("phone") or ""),
                "phone_iso_code": str(row.get("phone_iso_code") or ""),
                "phone_std_code": str(row.get("phone_std_code") or ""),
                "preferred_currency": str(row.get("preferred_currency") or "INR"),
                "preferred_language": str(row.get("preferred_language") or "en"),
                "seat_preference": str(row.get("seat_preference") or "Any"),
                "meal_preference": str(row.get("meal_preference") or "Standard"),
                "notify_email": "1" if int(row.get("notify_email") or 0) == 1 else "0",
                "notify_sms": "1" if int(row.get("notify_sms") or 0) == 1 else "0",
                "is_primary": "1" if int(row.get("is_primary") or 0) == 1 else "",
                "is_active": "1" if int(row.get("is_active") or 0) == 1 else "0",
            }

    return _render_page(
        request=request,
        current_user=current_user,
        form_data=form_data,
        edit_mode=edit_mode,
        page_msg=page_msg,
        page_error=page_error,
    )


@router.get("/travelers", response_class=HTMLResponse)
def travelers_page(request: Request):
    return _load_travelers_page(request)


@router.get("/profile", response_class=HTMLResponse)
def profile_page_legacy(request: Request):
    qs = str(request.url.query or "").strip()
    url = "/travelers"
    if qs:
        url = f"{url}?{qs}"
    return RedirectResponse(url=url, status_code=302)


def _save_traveler(request: Request, form_data: dict, current_user: dict):
    error = _validate_traveler_form(form_data)
    if error:
        return _render_page(
            request=request,
            current_user=current_user,
            form_data=form_data,
            edit_mode=bool(form_data["document_id"]),
            page_error=error,
            status_code=400,
        )

    user_id = int(current_user["user_id"])

    issue_date_val = form_data["issue_date"] or None
    email_val = form_data["email"] or None
    phone_val = form_data["phone"] or None
    phone_iso_code_val = form_data["phone_iso_code"] or None
    phone_std_code_val = form_data["phone_std_code"] or None
    preferred_currency_val = form_data["preferred_currency"] or None
    preferred_language_val = form_data["preferred_language"] or None
    seat_preference_val = form_data["seat_preference"] or None
    meal_preference_val = form_data["meal_preference"] or None
    notify_email_val = 1 if form_data["notify_email"] == "1" else 0
    notify_sms_val = 1 if form_data["notify_sms"] == "1" else 0
    is_primary_val = 1 if form_data["is_primary"] == "1" else 0
    is_active_val = 1 if form_data["is_active"] == "1" else 0
    return_to = (form_data.get("return_to") or "").strip()
    agent_fsr_id = (form_data.get("agent_fsr_id") or "").strip()

    if form_data["document_id"]:
        update_traveler(
            user_id,
            int(form_data["document_id"]),
            form_data["traveler_type"],
            form_data["document_type"],
            form_data["document_number"],
            form_data["issuing_country_iso2"],
            issue_date_val,
            form_data["expiry_date"],
            form_data["first_name"],
            form_data["last_name"],
            form_data["date_of_birth"],
            form_data["gender"],
            form_data["nationality_iso2"],
            email_val,
            phone_val,
            phone_iso_code_val,
            phone_std_code_val,
            preferred_currency_val,
            preferred_language_val,
            seat_preference_val,
            meal_preference_val,
            notify_email_val,
            notify_sms_val,
            is_primary_val,
            is_active_val,
        )
        msg = "Traveller details updated successfully."
    else:
        insert_traveler(
            user_id,
            form_data["traveler_type"],
            form_data["document_type"],
            form_data["document_number"],
            form_data["issuing_country_iso2"],
            issue_date_val,
            form_data["expiry_date"],
            form_data["first_name"],
            form_data["last_name"],
            form_data["date_of_birth"],
            form_data["gender"],
            form_data["nationality_iso2"],
            email_val,
            phone_val,
            phone_iso_code_val,
            phone_std_code_val,
            preferred_currency_val,
            preferred_language_val,
            seat_preference_val,
            meal_preference_val,
            notify_email_val,
            notify_sms_val,
            is_primary_val,
            is_active_val,
        )
        msg = "Traveller added successfully."

    if return_to == "confirm":
        if agent_fsr_id:
            return RedirectResponse(
                url=f"/portal/flight/confirm?agent_fsr_id={agent_fsr_id}&msg={msg}",
                status_code=303,
            )
        return RedirectResponse(url="/portal/flight/search", status_code=303)

    return RedirectResponse(url=f"/travelers?msg={msg}", status_code=303)


@router.post("/travelers/save")
async def travelers_save(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)

    form = await request.form()

    form_data = {
        "document_id": (form.get("document_id") or "").strip(),
        "return_to": (form.get("return_to") or "").strip(),
        "agent_fsr_id": (form.get("agent_fsr_id") or "").strip(),
        "traveler_type": (form.get("traveler_type") or "Adult").strip(),
        "document_type": (form.get("document_type") or "Passport").strip(),
        "document_number": (form.get("document_number") or "").strip(),
        "issuing_country_iso2": (form.get("issuing_country_iso2") or "").strip().upper(),
        "issue_date": (form.get("issue_date") or "").strip(),
        "expiry_date": (form.get("expiry_date") or "").strip(),
        "first_name": (form.get("first_name") or "").strip(),
        "last_name": (form.get("last_name") or "").strip(),
        "date_of_birth": (form.get("date_of_birth") or "").strip(),
        "gender": (form.get("gender") or "").strip(),
        "nationality_iso2": (form.get("nationality_iso2") or "").strip().upper(),
        "email": (form.get("email") or "").strip(),
        "phone": (form.get("phone") or "").strip(),
        "phone_iso_code": (form.get("phone_iso_code") or "").strip(),
        "phone_std_code": (form.get("phone_std_code") or "").strip(),
        "preferred_currency": (form.get("preferred_currency") or "INR").strip(),
        "preferred_language": (form.get("preferred_language") or "en").strip(),
        "seat_preference": (form.get("seat_preference") or "Any").strip(),
        "meal_preference": (form.get("meal_preference") or "Standard").strip(),
        "notify_email": "1" if form.get("notify_email") else "0",
        "notify_sms": "1" if form.get("notify_sms") else "0",
        "is_primary": "1" if form.get("is_primary") else "0",
        "is_active": "1" if form.get("is_active") else "0",
    }

    return _save_traveler(request, form_data, current_user)


@router.post("/profile/save")
async def profile_save_legacy(request: Request):
    return await travelers_save(request)


@router.post("/travelers/set-primary")
async def travelers_set_primary(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)

    form = await request.form()
    document_id = int(form.get("document_id"))
    return_to = (form.get("return_to") or "").strip()
    agent_fsr_id = (form.get("agent_fsr_id") or "").strip()

    set_primary_traveler(int(current_user["user_id"]), document_id)

    if return_to == "confirm":
        if agent_fsr_id:
            return RedirectResponse(
                url=f"/portal/flight/confirm?agent_fsr_id={agent_fsr_id}&msg=Primary traveller updated.",
                status_code=303,
            )
        return RedirectResponse(url="/portal/flight/search", status_code=303)

    return RedirectResponse(url="/travelers?msg=Primary traveller updated.", status_code=303)


@router.post("/profile/set-primary")
async def profile_set_primary_legacy(request: Request):
    return await travelers_set_primary(request)


@router.post("/travelers/toggle-active")
async def travelers_toggle_active(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)

    form = await request.form()
    document_id = int(form.get("document_id"))
    return_to = (form.get("return_to") or "").strip()
    agent_fsr_id = (form.get("agent_fsr_id") or "").strip()

    toggle_traveler_active(int(current_user["user_id"]), document_id)

    if return_to == "confirm":
        if agent_fsr_id:
            return RedirectResponse(
                url=f"/portal/flight/confirm?agent_fsr_id={agent_fsr_id}&msg=Traveller status updated.",
                status_code=303,
            )
        return RedirectResponse(url="/portal/flight/search", status_code=303)

    return RedirectResponse(url="/travelers?msg=Traveller status updated.", status_code=303)


@router.post("/profile/toggle-active")
async def profile_toggle_active_legacy(request: Request):
    return await travelers_toggle_active(request)
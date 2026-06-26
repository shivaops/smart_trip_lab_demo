from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from datetime import date, datetime
import re
import json
import uuid
from urllib.parse import quote

from app.llm.nodes import apply_date_confirmation_node, build_search_route_payload_node
from app.llm.schemas import SearchRoutePayload
from app.llm.graph import build_llm_graph
from app.llm.graph_state import LLMGraphState
from app.routers.flight_search import (
    FLIGHT_SEARCH_ENDPOINT_ID,
    _apply_search_trip_type_rules,
    _build_one_way_grouped_rows,
    _build_round_trip_result_cards,
    _fetch_search_rows,
    _persist_search_results,
    _load_selected_item_json,
    _load_selected_search_request_json,
    _normalize_confirm_model,
    _find_fare_option_by_ids,
    _find_fare_option_by_key,
    _validate_booking_payload,
    _normalize_payload_for_provider,
    _normalize_trip_type_value,
    _get_active_traveler_rows,
    _check_duplicate_booking_conflict,
    _build_confirmed_journey,
    _build_manage_passengers,
    _get_manage_booking_by_ref,
    _extract_provider_error_message,
)
from app.llm.services.llm_state_service import load_state, save_state
from core.audit import log_fail, log_info
from core.auth_context import get_session_uuid_from_request
from core.json_path import json_set
from core.provider_client import call_provider, call_provider_traced
from db.session import get_conn
from repo.cfg_repo import build_result_grid_fields, build_search_form_fields
from repo.endpoint_repo import get_endpoint_connection
from repo.provider_repo import get_active_default_llm_provider, get_llm_provider_by_code
from repo.session_repo import get_active_session_by_uuid
from repo.greeting_repo import find_active_greeting_by_message


templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/portal/llm", tags=["LLM Assist"])



def _llm_build_provider_manage_booking_url(booking_ref: str) -> str:
    ref = str(booking_ref or "").strip()
    if not ref:
        return ""
    base_url = ""
    try:
        conn_cfg = get_endpoint_connection(2)
        base_url = str(conn_cfg.get("base_url") or "").strip().rstrip("/")
    except Exception:
        base_url = ""
    if not base_url:
        base_url = "http://bookmyflight.local:8002"
    return f"{base_url}/manage-booking?booking_ref={quote(ref)}"


class LLMIntentRequest(BaseModel):
    message: str = Field(..., min_length=1)
    today_date: str = Field(default_factory=lambda: date.today().isoformat())
    provider_code: str | None = None


class LLMIntentResponse(BaseModel):
    status: str
    next_action: str | None = None
    next_route: str | None = None
    user_message: str | None = None
    errors: list[str] = Field(default_factory=list)
    llm_intent: dict | None = None
    normalized_intent: dict | None = None
    missing_fields: list[dict] = Field(default_factory=list)
    route_payload: dict | None = None


class LLMDateConfirmRequest(BaseModel):
    message: str = Field(..., min_length=1)
    today_date: str = Field(default_factory=lambda: date.today().isoformat())
    selected_date: str = Field(..., min_length=1)
    provider_code: str | None = None
    normalized_intent: dict | None = None
    route_payload: dict | None = None


class LLMDateConfirmResponse(BaseModel):
    status: str
    next_action: str | None = None
    next_route: str | None = None
    user_message: str | None = None
    errors: list[str] = Field(default_factory=list)
    normalized_intent: dict | None = None
    route_payload: dict | None = None


class LLMRouteToSearchRequest(BaseModel):
    route_payload: SearchRoutePayload
    confirmed: bool = True


class LLMResumeRequest(BaseModel):
    route_payload: SearchRoutePayload
    field_name: str = Field(..., min_length=1)
    value: str | int | float | None = None
    provider_code: str | None = None


class LLMResumeResponse(BaseModel):
    status: str
    next_action: str | None = None
    user_message: str | None = None
    missing_fields: list[dict] = Field(default_factory=list)
    route_payload: dict | None = None


class LLMFareOptionsRequest(BaseModel):
    agent_fsr_id: int
    selected_result: dict | None = None


class LLMTravelersRequest(BaseModel):
    agent_fsr_id: int


class LLMTravelerSelectionRequest(BaseModel):
    agent_fsr_id: int
    selected_document_ids: list[int] = Field(default_factory=list)
    selection: dict | None = None
    allow_mismatch_override: bool = False


class LLMBookingPreviewRequest(BaseModel):
    agent_fsr_id: int
    selected_document_ids: list[int] = Field(default_factory=list)
    selection: dict | None = None


class LLMBookingConfirmRequest(BaseModel):
    agent_fsr_id: int
    selected_document_ids: list[int] = Field(default_factory=list)
    selection: dict | None = None


class LLMBookingStatusRequest(BaseModel):
    booking_ref: str


llm_graph = build_llm_graph()

LLM_PROVIDER_COOKIE_NAME = "tt_llm_provider"




def _safe_load_llm_state(session_id: int | None, endpoint_id: int = FLIGHT_SEARCH_ENDPOINT_ID) -> dict | None:
    try:
        if not session_id:
            return None
        return load_state(session_id, endpoint_id)
    except Exception:
        return None


def _safe_save_llm_state(session_id: int | None, provider: dict | None, state: dict | None, user_message: str | None = None, endpoint_id: int = FLIGHT_SEARCH_ENDPOINT_ID) -> None:
    try:
        if not session_id or not isinstance(state, dict):
            return
        save_state(session_id, endpoint_id, (provider or {}).get("llm_provider_id"), state, user_message)
    except Exception:
        return


def _build_llm_persisted_state(*, status: str | None, next_action: str | None = None, missing_fields: list[dict] | None = None, route_payload: dict | None = None, normalized_intent: dict | None = None, llm_intent: dict | None = None) -> dict:
    missing = list(missing_fields or [])
    first_missing = missing[0] if missing else {}
    awaiting_cfg_id = None
    try:
        awaiting_cfg_id = int(first_missing.get("cfg_id")) if first_missing.get("cfg_id") is not None else None
    except Exception:
        awaiting_cfg_id = None
    conversation_status = str(next_action or status or "").strip().upper() or "UNKNOWN"
    awaiting_reason = "MISSING" if missing else None
    return {
        "conversation_status": conversation_status,
        "awaiting_cfg_id": awaiting_cfg_id,
        "awaiting_reason": awaiting_reason,
        "missing_fields": missing,
        "route_payload": route_payload or {},
        "normalized_intent": normalized_intent or {},
        "llm_intent": llm_intent or {},
    }

def _normalize_text(value: str | None) -> str:
    return str(value or "").strip().lower()


def _provider_connection_message(provider: dict | None, text: str | None = None) -> str | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    lower = raw.lower()
    provider_name = str((provider or {}).get("provider_name") or (provider or {}).get("provider_code") or "the selected LLM provider").strip()
    tokens = [
        "http 503",
        '"code": 503',
        'status": "unavailable"',
        "currently experiencing high demand",
        "connection refused",
        "timed out",
        "timeout",
        "max retries exceeded",
        "failed to establish a new connection",
        "temporarily unavailable",
    ]
    if any(token in lower for token in tokens):
        return f"Unable to connect to {provider_name}. Please try again after some time, or check whether your billing or plan limit is exhausted."
    if any(token in lower for token in ["api key", "unauthorized", "forbidden", "401", "403", "quota", "billing", "rate limit"]):
        return f"Unable to connect to {provider_name}. Please try again after some time, or check whether your billing or plan limit is exhausted."
    return None


def _match_select_option(raw_value: str | None, options: list[tuple[str, str]] | None) -> str | None:
    text = _normalize_text(raw_value)
    if not text:
        return None
    options = options or []

    def _canon(value: str | None) -> str:
        return re.sub(r"[^a-z0-9]+", " ", _normalize_text(value)).strip()

    canon = _canon(text)
    compact = canon.replace(" ", "")
    if not canon:
        return None

    exact_value: dict[str, str] = {}
    exact_label: dict[str, str] = {}
    token_prefix_hits: list[str] = []

    synonyms = {
        "eco": "Economy",
        "economy": "Economy",
        "prem eco": "Premium Economy",
        "premium economy": "Premium Economy",
        "premiumeconomy": "Premium Economy",
        "biz": "Business",
        "biz class": "Business",
        "business": "Business",
        "business class": "Business",
        "first": "First",
        "first class": "First",
    }
    if canon in synonyms:
        wanted = _normalize_text(synonyms[canon])
        for value, label in options:
            if _normalize_text(value) == wanted or _normalize_text(label) == wanted:
                return str(value)

    for value, label in options:
        value_s = str(value)
        label_s = str(label)
        value_norm = _normalize_text(value_s)
        label_norm = _normalize_text(label_s)
        value_canon = _canon(value_s)
        label_canon = _canon(label_s)

        for key in {value_norm, value_canon, value_canon.replace(" ", "")}:
            if key:
                exact_value.setdefault(key, value_s)
        for key in {label_norm, label_canon, label_canon.replace(" ", "")}:
            if key:
                exact_label.setdefault(key, value_s)

        label_tokens = [tok for tok in label_canon.split() if tok]
        value_tokens = [tok for tok in value_canon.split() if tok]
        if len(canon) >= 3:
            if any(tok.startswith(canon) for tok in label_tokens + value_tokens):
                token_prefix_hits.append(value_s)

    for keymap in (exact_value, exact_label):
        if canon in keymap:
            return keymap[canon]
        if compact in keymap:
            return keymap[compact]

    unique_prefix_hits = []
    seen = set()
    for hit in token_prefix_hits:
        if hit not in seen:
            seen.add(hit)
            unique_prefix_hits.append(hit)
    if len(unique_prefix_hits) == 1:
        return unique_prefix_hits[0]
    return None


def _normalize_option_tuples(options) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for opt in options or []:
        if isinstance(opt, (list, tuple)) and len(opt) >= 2:
            out.append((str(opt[0]), str(opt[1])))
        elif isinstance(opt, dict):
            value = str(opt.get("value") or opt.get("code") or "").strip()
            label = str(opt.get("label") or opt.get("name") or value).strip()
            if value or label:
                out.append((value or label, label or value))
        elif opt not in (None, ""):
            out.append((str(opt), str(opt)))
    return out


def _normalize_preferred_airline_input(raw_value: str | None) -> str | None:
    raw = str(raw_value or "").strip()
    if not raw:
        return None
    value = raw.replace("_", " ")
    value = re.sub(r"^[\s:;,-]+|[\s:;,-]+$", "", value).strip()
    lower = value.lower()
    prefixes = [
        "preferred airline",
        "preferred_airline",
        "search preference",
        "search_preference",
        "airline preference",
        "airline",
    ]
    for prefix in prefixes:
        if lower.startswith(prefix):
            value = value[len(prefix):].strip(" :-_=.")
            break
    value = re.sub(r"\bcode\b", " ", value, flags=re.I)
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def _resolve_preferred_airline_code_from_master(raw_value: str | None) -> str | None:
    """Resolve a user-friendly airline name/code to the provider airline code.

    Example:
    - User/LLM value: Air India
    - DB/provider value: AI

    This is intentionally used only for preferred_airline so normal select matching
    remains unchanged for cabin/currency. It also preserves the existing rule that
    price preferences such as CHEAPEST must not become preferred_airline.
    """
    supplied = _normalize_preferred_airline_input(raw_value)
    if not supplied or _is_price_search_preference(supplied):
        return None

    def _canon(value: str | None) -> str:
        return re.sub(r"[^a-z0-9]+", " ", str(value or "").strip().lower()).strip()

    canon = _canon(supplied)
    compact = canon.replace(" ", "")
    if not canon:
        return None

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT airline_code, airline_name
                    FROM airline
                    WHERE airline_code IS NOT NULL
                      AND airline_code <> ''
                """)
                rows = list(cur.fetchall() or [])
    except Exception:
        return None

    exact_hits: list[str] = []
    prefix_hits: list[str] = []

    for row in rows:
        code = str(row.get("airline_code") or "").strip()
        name = str(row.get("airline_name") or "").strip()
        if not code:
            continue

        code_canon = _canon(code)
        name_canon = _canon(name)
        keys = {code_canon, code_canon.replace(" ", ""), name_canon, name_canon.replace(" ", "")}
        if canon in keys or compact in keys:
            exact_hits.append(code)
            continue

        # Safe convenience for partial user input like "Air Ind".
        # Only accept if it results in one unique airline.
        if len(canon) >= 4 and name_canon.startswith(canon):
            prefix_hits.append(code)

    unique_exact = []
    seen = set()
    for code in exact_hits:
        if code not in seen:
            seen.add(code)
            unique_exact.append(code)
    if len(unique_exact) == 1:
        return unique_exact[0]

    unique_prefix = []
    seen = set()
    for code in prefix_hits:
        if code not in seen:
            seen.add(code)
            unique_prefix.append(code)
    if len(unique_prefix) == 1:
        return unique_prefix[0]

    return None


def _extract_preferred_airline_from_user_message(message: str | None) -> str | None:
    """Recover preferred airline from the original user text when the LLM misses it.

    Keep this as raw display/user input (for example, "Air India").
    The existing LOV/config validation later maps it to the real airline code (for example, AI).
    Price words such as cheapest/lowest/budget must remain search_preference only, not preferred_airline.
    """
    raw = str(message or "").strip()
    if not raw:
        return None

    stop_words = (
        r"on|from|to|adult|adults|child|children|infant|infants|currency|"
        r"cabin|class|depart|departure|return|date|trip|one\s+way|round\s+trip"
    )
    patterns = [
        rf"(?i)\bpreferred\s+airline\s*[:=-]?\s*(?P<airline>[A-Za-z][A-Za-z .&_-]{{1,50}}?)(?=\s*(?:[.,;]|$)|\s+\b(?:{stop_words})\b)",
        rf"(?i)\bairline\s+preference\s*[:=-]?\s*(?P<airline>[A-Za-z][A-Za-z .&_-]{{1,50}}?)(?=\s*(?:[.,;]|$)|\s+\b(?:{stop_words})\b)",
        rf"(?i)\bonly\s+(?P<airline>[A-Za-z]{{2,3}}|[A-Za-z][A-Za-z .&_-]{{2,50}}?)\s+flights?\b",
        rf"(?i)\bfly\s+by\s+(?P<airline>[A-Za-z][A-Za-z .&_-]{{1,50}}?)(?=\s*(?:[.,;]|$)|\s+\b(?:{stop_words})\b)",
    ]
    for pat in patterns:
        m = re.search(pat, raw)
        if not m:
            continue
        airline = _normalize_preferred_airline_input(m.group("airline"))
        if airline and not _is_price_search_preference(airline):
            return airline
    return None


def _apply_preferred_airline_fallback(normalized_intent: dict | None, original_message: str | None) -> dict | None:
    """Fill preferred_airline from original text only when LLM output missed it.

    This preserves the recent separation:
    - preferred_airline = Air India / Gulf Air / etc.
    - search_preference = CHEAPEST / lowest fare / budget
    """
    if not isinstance(normalized_intent, dict) or not normalized_intent:
        return normalized_intent
    current = _normalize_preferred_airline_input(normalized_intent.get("preferred_airline"))
    if current and not _is_price_search_preference(current):
        normalized_intent["preferred_airline"] = current
        return normalized_intent

    recovered = _extract_preferred_airline_from_user_message(original_message)
    if recovered:
        normalized_intent["preferred_airline"] = recovered
    elif current and _is_price_search_preference(current):
        normalized_intent["preferred_airline"] = None
    return normalized_intent




def _is_price_search_preference(raw_value: str | None) -> bool:
    """Return True for search preferences like cheapest/lowest fare, not airline names."""
    value = re.sub(r"[^a-z0-9]+", " ", str(raw_value or "").lower()).strip()
    if not value:
        return False
    price_phrases = {
        "cheap", "cheapest", "lowest", "lowest fare", "lowest price",
        "low fare", "low price", "budget", "budget fare", "best price",
        "minimum fare", "minimum price", "min fare", "min price",
        "affordable", "economical", "least fare", "least price",
    }
    return value in price_phrases or any(re.search(rf"\b{re.escape(p)}\b", value) for p in price_phrases)

def _rewrite_airline_phrases_for_llm(message: str | None) -> str:
    text = str(message or "")
    if not text.strip():
        return text

    def _repl(match: re.Match) -> str:
        airline = str(match.group('airline') or '').strip(" .,:;_-\t")
        airline = re.sub(r"\s+", " ", airline).strip()
        if not airline:
            return match.group(0)
        return f"search preference {airline}"

    patterns = [
        r"(?i)\bpreferred\s+airline\s*[:=-]?\s*(?P<airline>[A-Za-z][A-Za-z .&_-]{1,40})",
        r"(?i)\bairline\s+preference\s*[:=-]?\s*(?P<airline>[A-Za-z][A-Za-z .&_-]{1,40})",
        r"(?i)\bfilter\s+only\s+(?P<airline>[A-Za-z][A-Za-z .&_-]{1,40})",
        r"(?i)\bonly\s+(?P<airline>[A-Za-z]{2,3}|[A-Za-z][A-Za-z .&_-]{2,40})\s+flights?",
        r"(?i)\bairline\s*[:=-]?\s*(?P<airline>[A-Za-z][A-Za-z .&_-]{1,40})",
        r"(?i)\bfly\s+by\s+(?P<airline>[A-Za-z][A-Za-z .&_-]{1,40})",
        r"(?i)\bsearch\s+for\s+(?P<airline>[A-Za-z]{2,3}|[A-Za-z][A-Za-z .&_-]{2,40})(?!\s+flight|\s+flights|\s+cheap|\s+cheapest|\s+fast|\s+fastest)",
    ]

    out = text
    for pat in patterns:
        out = re.sub(pat, _repl, out)
    return out


def _parse_flexible_date_from_text(text: str | None) -> str | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    m = re.search(r'(?i)\b(on|depart|departure)\s+(\d{1,2}[-/][A-Za-z]{3}[-/]\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})\b', raw)
    candidate = m.group(2) if m else raw
    candidate = candidate.strip()
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', candidate)
    if m:
        return candidate
    m = re.match(r'^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$', candidate)
    if m:
        dd, mm, yyyy = m.groups()
        return f"{yyyy}-{int(mm):02d}-{int(dd):02d}"
    m = re.match(r'^(\d{1,2})[-/]([A-Za-z]{3})[-/](\d{4})$', candidate)
    if m:
        dd, mon, yyyy = m.groups()
        months = {"jan":"01","feb":"02","mar":"03","apr":"04","may":"05","jun":"06","jul":"07","aug":"08","sep":"09","oct":"10","nov":"11","dec":"12"}
        mm = months.get(mon.lower()[:3])
        if mm:
            return f"{yyyy}-{mm}-{int(dd):02d}"
    return None


def _extract_route_pair_from_message(message: str | None) -> tuple[str | None, str | None]:
    raw = str(message or "")
    if not raw.strip():
        return None, None
    m = re.search(r'(?i)\bfrom\s+([A-Za-z][A-Za-z .-]{1,40}?)\s+to\s+([A-Za-z][A-Za-z .-]{1,40}?)(?=\s+on\b|[.,]|$)', raw)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m = re.search(r'(?i)\bfrom\s+([A-Za-z][A-Za-z .-]{1,40}?)(?=\s+on\b|[.,]|$)', raw)
    if m:
        return m.group(1).strip(), None
    return None, None


def _extract_int_after_keywords(message: str | None, keywords: list[str], default: int) -> int:
    raw = str(message or "")
    for key in keywords:
        m = re.search(rf'(?i)\b{key}\s*[:=-]?\s*(\d+)\b', raw)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return default
    return default


def _extract_keyword_value(message: str | None, keyword_patterns: list[str]) -> str | None:
    raw = str(message or "")
    for pat in keyword_patterns:
        m = re.search(pat, raw, flags=re.I)
        if m:
            return m.group(1).strip()
    return None


def _salvage_search_intent_from_message(message: str | None) -> dict | None:
    raw = str(message or "").strip()
    if not raw:
        return None
    rewritten = _rewrite_airline_phrases_for_llm(raw)
    from_city, to_city = _extract_route_pair_from_message(rewritten)
    depart_date = _parse_flexible_date_from_text(rewritten)

    route_payload = {
        "trip_type": "ONE_WAY",
        "from_city": from_city,
        "to_city": to_city,
        "depart_date": depart_date,
        "return_date": None,
        "adults": _extract_int_after_keywords(rewritten, ["adult", "adults"], 1),
        "children": _extract_int_after_keywords(rewritten, ["child", "children"], 0),
        "infants": _extract_int_after_keywords(rewritten, ["infant", "infants"], 0),
        "cabin_class": _extract_keyword_value(rewritten, [r'\bcabin\s+([A-Za-z ]{3,30})\b']),
        "currency": _extract_keyword_value(rewritten, [r'\bcurrency\s+([A-Za-z]{3})\b']),
        "meal_preference": None,
        "preferred_airline": _extract_keyword_value(rewritten, [r'\bsearch\s+preference\s+([A-Za-z0-9 .&_-]{2,40})\b']),
        "search_preference": _extract_keyword_value(rewritten, [r'\bsearch\s+preference\s+([A-Za-z0-9 .&_-]{2,40})\b']),
    }

    if _is_price_search_preference(route_payload.get("preferred_airline")):
        route_payload["preferred_airline"] = None

    if not route_payload["from_city"] and not route_payload["to_city"] and not route_payload["depart_date"]:
        return None

    normalized_intent = {
        "intent": "search_flights",
        "trip_type": None,
        "from_city": route_payload["from_city"],
        "to_city": route_payload["to_city"],
        "depart_date_raw": depart_date,
        "depart_date": depart_date,
        "return_date_raw": None,
        "return_date": None,
        "adults": route_payload["adults"],
        "children": route_payload["children"],
        "infants": route_payload["infants"],
        "cabin_class": route_payload["cabin_class"],
        "currency": route_payload["currency"],
        "meal_preference": None,
        "search_preference": route_payload["search_preference"],
        "preferred_airline": route_payload["preferred_airline"],
        "missing_fields": [],
    }
    return {
        "llm_intent": dict(normalized_intent),
        "normalized_intent": normalized_intent,
        "route_payload": route_payload,
    }


def _build_response_from_salvage(message: str | None) -> LLMIntentResponse | None:
    salvaged = _salvage_search_intent_from_message(message)
    if not salvaged:
        return None
    normalized_intent = salvaged.get("normalized_intent") or {}
    route_payload = salvaged.get("route_payload") or {}
    missing_fields, rebuilt_route_payload = _build_missing_field_descriptors_for_intent(normalized_intent)
    next_action = "ASK_MISSING_FIELDS" if missing_fields else "ROUTE_TO_SEARCH"
    next_route = None if missing_fields else "/portal/llm/route-to-search"
    user_message = (
        "I understood part of your request. Please review and complete the remaining details before I continue."
        if missing_fields else
        "I understood your request and I am ready to continue to flight search."
    )
    return LLMIntentResponse(
        status="NEEDS_CONFIRMATION" if missing_fields else "READY_TO_ROUTE",
        next_action=next_action,
        next_route=next_route,
        user_message=user_message,
        errors=[],
        llm_intent=salvaged.get("llm_intent"),
        normalized_intent=normalized_intent,
        missing_fields=missing_fields,
        route_payload=rebuilt_route_payload or route_payload,
    )


def _load_cfg_options_for_llm(field: dict) -> list[tuple[str, str]]:
    options = _normalize_option_tuples(field.get("options"))
    if options:
        return options

    allowed_csv = str(field.get("allowed_values_csv") or "").strip()
    if allowed_csv:
        parsed: list[tuple[str, str]] = []
        for raw in allowed_csv.split(","):
            value = str(raw or "").strip()
            if value:
                parsed.append((value, value))
        if parsed:
            return parsed

    lov_source_type = str(field.get("lov_source_type") or "").strip().upper()
    lov_source_sql = str(field.get("lov_source_sql") or "").strip()
    if lov_source_type == "SQL" and lov_source_sql:
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(lov_source_sql)
                    rows = list(cur.fetchall() or [])
            parsed: list[tuple[str, str]] = []
            for row in rows:
                if isinstance(row, dict):
                    value = str(row.get("value") or row.get("VALUE") or "").strip()
                    label = str(row.get("label") or row.get("LABEL") or value).strip()
                elif isinstance(row, (list, tuple)):
                    value = str(row[0] if len(row) > 0 else "").strip()
                    label = str(row[1] if len(row) > 1 else value).strip()
                else:
                    value = str(row or "").strip()
                    label = value
                if value:
                    parsed.append((value, label or value))
            if parsed:
                return parsed
        except Exception:
            return []

    return []


def _resolve_airport_code(raw_value: str | None) -> str | None:
    text = str(raw_value or "").strip()
    if not text:
        return None
    sql = """
        SELECT airport_code, city_name, airport_name, display_rank
        FROM tt_agentic.airport
        WHERE is_active = 1
          AND (
                UPPER(airport_code) = UPPER(%s)
             OR UPPER(city_name) = UPPER(%s)
             OR UPPER(airport_name) = UPPER(%s)
             OR UPPER(CONCAT(airport_code, ' - ', city_name, ' - ', airport_name)) = UPPER(%s)
             OR UPPER(city_name) LIKE UPPER(%s)
             OR UPPER(airport_name) LIKE UPPER(%s)
          )
        ORDER BY
            CASE
                WHEN UPPER(airport_code) = UPPER(%s) THEN 1
                WHEN UPPER(city_name) = UPPER(%s) THEN 2
                WHEN UPPER(airport_name) = UPPER(%s) THEN 3
                WHEN UPPER(CONCAT(airport_code, ' - ', city_name, ' - ', airport_name)) = UPPER(%s) THEN 4
                WHEN UPPER(city_name) LIKE UPPER(%s) THEN 5
                WHEN UPPER(airport_name) LIKE UPPER(%s) THEN 6
                ELSE 99
            END,
            display_rank ASC,
            airport_code ASC
        LIMIT 5
    """
    like_value = f"{text}%"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (text, text, text, text, like_value, like_value, text, text, text, text, like_value, like_value))
            rows = list(cur.fetchall() or [])
    if not rows:
        raise ValueError(f"Could not resolve airport/city '{text}' to an active airport code.")
    first_code = str(rows[0].get("airport_code") or "").strip()
    if not first_code:
        raise ValueError(f"Airport resolution failed for '{text}'.")
    same_top_exact = [r for r in rows if _normalize_text(r.get("city_name")) == _normalize_text(text)]
    unique_codes = {str(r.get("airport_code") or "").strip() for r in same_top_exact if str(r.get("airport_code") or "").strip()}
    if len(unique_codes) > 1:
        raise ValueError(f"Airport/city '{text}' matches multiple airports ({', '.join(sorted(unique_codes))}). Please clarify the airport code.")
    return first_code


def _cast_cfg_value(value, data_type: str | None):
    if value in (None, ""):
        return value
    dt = str(data_type or "STRING").upper()
    if dt in ("INT", "INTEGER", "NUMBER"):
        try:
            return int(value)
        except Exception:
            return float(value)
    return value


def _route_key_for_request_path(req_path: str) -> str | None:
    mapping = {
        "search.trip_type": "trip_type",
        "search.from_airport": "from_city",
        "search.to_airport": "to_city",
        "search.depart_date": "depart_date",
        "search.return_date": "return_date",
        "search.adults": "adults",
        "search.children": "children",
        "search.infants": "infants",
        "search.cabin_class": "cabin_class",
        "search.currency": "currency",
        "search.preferred_airline": "preferred_airline",
    }
    return mapping.get(req_path)


def _default_from_cfg(field: dict, req_path: str, trip_type: str):
    default_value = field.get("default_value")
    if req_path == "search.return_date" and trip_type != "ROUND_TRIP":
        return ""
    if default_value in (None, ""):
        return None
    options = _normalize_option_tuples(field.get("options"))
    if req_path in ("search.cabin_class", "search.currency"):
        return _match_select_option(str(default_value), options) or default_value
    return default_value


def _missing_field_descriptor(field: dict, req_path: str) -> dict:
    options = _load_cfg_options_for_llm(field)
    raw_control_type = str(
        field.get("ui_control_type")
        or field.get("ui_control")
        or field.get("control_type")
        or ""
    ).strip().upper()
    data_type = str(field.get("data_type") or "STRING").strip().upper()

    if options:
        ui_control_type = "SELECT"
        ui_mode = "DROPDOWN"
    elif raw_control_type == "DATE" or data_type == "DATE":
        ui_control_type = "DATE"
        ui_mode = "TEXT"
    else:
        ui_control_type = raw_control_type or "TEXT"
        ui_mode = "TEXT"

    label = field.get("label") or field.get("ui_label") or field.get("name") or req_path
    prompt = f"Please provide {label}."
    if ui_mode == "DROPDOWN":
        prompt = f"Please select {label}."
    return {
        "cfg_id": field.get("cfg_id"),
        "label": label,
        "name": field.get("name") or f"cfg_{field.get('cfg_id')}" or req_path,
        "request_json_path": req_path,
        "route_key": _route_key_for_request_path(req_path),
        "data_type": field.get("data_type") or "STRING",
        "ui_control_type": ui_control_type,
        "ui_mode": ui_mode,
        "options": [{"value": value, "label": label_text} for value, label_text in options],
        "default_value": field.get("default_value"),
        "prompt": prompt,
        "placeholder": str(field.get("placeholder") or field.get("ui_placeholder") or "").strip(),
        "hint": str(field.get("help_text") or field.get("ui_help_text") or "").strip(),
    }

def _build_partial_route_payload_from_normalized_intent(normalized_intent: dict | None) -> dict | None:
    ni = normalized_intent or {}
    if not isinstance(ni, dict) or not ni:
        return None
    trip_type = str(ni.get("trip_type") or "ONE_WAY").strip().upper() or "ONE_WAY"
    return {
        "trip_type": trip_type,
        "from_city": ni.get("from_city"),
        "to_city": ni.get("to_city"),
        "depart_date": ni.get("depart_date"),
        "return_date": ni.get("return_date") if trip_type == "ROUND_TRIP" else None,
        "adults": ni.get("adults", 1),
        "children": ni.get("children", 0),
        "infants": ni.get("infants", 0),
        "cabin_class": ni.get("cabin_class"),
        "currency": ni.get("currency"),
        "meal_preference": ni.get("meal_preference"),
        "preferred_airline": (
            ni.get("preferred_airline")
            if ni.get("preferred_airline") not in (None, "") and not _is_price_search_preference(ni.get("preferred_airline"))
            else (ni.get("search_preference") if not _is_price_search_preference(ni.get("search_preference")) else None)
        ),
        "search_preference": ni.get("search_preference"),
    }


def _build_missing_field_descriptors_for_intent(normalized_intent: dict | None) -> tuple[list[dict], dict | None]:
    ni = normalized_intent or {}
    if not isinstance(ni, dict) or str(ni.get("intent") or "") != "search_flights":
        return [], None

    route_payload = _build_partial_route_payload_from_normalized_intent(ni)
    if not route_payload:
        return [], None

    trip_type = str(route_payload.get("trip_type") or "ONE_WAY").strip().upper() or "ONE_WAY"
    route_payload["trip_type"] = trip_type

    try:
        fields = build_search_form_fields(FLIGHT_SEARCH_ENDPOINT_ID)
    except Exception:
        fields = []
    if not fields:
        return [], route_payload

    try:
        _, missing_required, _ = _prepare_cfg_driven_search_payload_from_route(SearchRoutePayload(**route_payload), fields)
    except Exception:
        return [], route_payload

    return list(missing_required or []), route_payload



def _set_route_payload_value(route_payload: dict, field_name: str, value):
    field = str(field_name or '').strip()
    if not field:
        return route_payload
    rp = dict(route_payload or {})
    rp[field] = value
    return rp


def _recompute_missing_fields_from_route_payload(route_payload: dict) -> tuple[list[dict], dict]:
    rp = dict(route_payload or {})
    if not str(rp.get('trip_type') or '').strip():
        rp['trip_type'] = 'ONE_WAY'
    fields = build_search_form_fields(FLIGHT_SEARCH_ENDPOINT_ID)
    _, missing_required, _ = _prepare_cfg_driven_search_payload_from_route(SearchRoutePayload(**rp), fields)
    return missing_required, rp

def _prepare_cfg_driven_search_payload_from_route(route_payload: SearchRoutePayload, fields: list[dict]) -> tuple[dict, list[dict], dict]:
    rp = route_payload.model_dump() if hasattr(route_payload, "model_dump") else dict(route_payload or {})
    payload: dict = {}
    missing_required: list[dict] = []
    applied_defaults: dict = {}
    trip_type = str(rp.get("trip_type") or "ONE_WAY").strip().upper() or "ONE_WAY"

    def mark_missing(field_cfg: dict, req_path_value: str):
        desc = _missing_field_descriptor(field_cfg, req_path_value)
        key = (desc.get("route_key"), desc.get("request_json_path"))
        seen = {(m.get("route_key"), m.get("request_json_path")) for m in missing_required}
        if key not in seen:
            missing_required.append(desc)

    for f in fields:
        cfg_id = int(f["cfg_id"])
        req_path = (f.get("request_json_path") or "").strip()
        if not req_path:
            raise ValueError(f"Missing request_json_path in cfg for cfg_id={cfg_id}")

        raw_value = None
        invalid_airport_value = None
        invalid_select_value = None
        options_norm = _normalize_option_tuples(f.get("options"))
        if req_path == "search.trip_type":
            raw_value = trip_type
        elif req_path == "search.from_airport":
            try:
                raw_value = _resolve_airport_code(rp.get("from_city"))
            except ValueError:
                invalid_airport_value = rp.get("from_city")
                raw_value = None
        elif req_path == "search.to_airport":
            try:
                raw_value = _resolve_airport_code(rp.get("to_city"))
            except ValueError:
                invalid_airport_value = rp.get("to_city")
                raw_value = None
        elif req_path == "search.depart_date":
            raw_value = rp.get("depart_date")
        elif req_path == "search.return_date":
            raw_value = rp.get("return_date") if trip_type == "ROUND_TRIP" else ""
        elif req_path == "search.adults":
            raw_value = rp.get("adults")
        elif req_path == "search.children":
            raw_value = rp.get("children")
        elif req_path == "search.infants":
            raw_value = rp.get("infants")
        elif req_path == "search.cabin_class":
            supplied = rp.get("cabin_class")
            matched = _match_select_option(supplied, options_norm)
            if supplied not in (None, "") and not matched:
                invalid_select_value = supplied
            raw_value = matched
        elif req_path == "search.currency":
            supplied = rp.get("currency")
            matched = _match_select_option(supplied, options_norm)
            if supplied not in (None, "") and not matched:
                invalid_select_value = supplied
            raw_value = matched
        elif req_path == "search.preferred_airline":
            preferred_present = "preferred_airline" in rp
            preferred_raw = rp.get("preferred_airline")
            if preferred_present and str(preferred_raw or "").strip() == "":
                supplied = ""
            else:
                supplied = preferred_raw
                if supplied in (None, "") and not _is_price_search_preference(rp.get("search_preference")):
                    supplied = rp.get("search_preference")
            supplied = _normalize_preferred_airline_input(supplied) if supplied not in (None, "") else supplied
            if _is_price_search_preference(supplied):
                supplied = ""
            matched = _match_select_option(supplied, options_norm)
            if not matched:
                # Preferred airline LOV may contain provider code only (for example AI),
                # while the user naturally says the airline name (for example Air India).
                # Resolve through the airline master and then validate the resolved code
                # against the configured LOV when available.
                resolved_airline_code = _resolve_preferred_airline_code_from_master(supplied)
                if resolved_airline_code:
                    matched = _match_select_option(resolved_airline_code, options_norm) or resolved_airline_code
            if supplied not in (None, "") and not matched:
                invalid_select_value = supplied
            raw_value = matched
        else:
            raw_value = None

        allow_default = invalid_airport_value in (None, "") and invalid_select_value in (None, "")
        if raw_value in (None, "") and allow_default:
            fallback_default = _default_from_cfg(f, req_path, trip_type)
            if fallback_default not in (None, ""):
                raw_value = fallback_default
                applied_defaults[req_path] = fallback_default

        if raw_value in (None, ""):
            if f.get("required") or invalid_select_value not in (None, ""):
                mark_missing(f, req_path)
            if invalid_airport_value not in (None, "") and req_path in ("search.from_airport", "search.to_airport"):
                applied_defaults[f"invalid::{req_path}"] = str(invalid_airport_value)
            if invalid_select_value not in (None, ""):
                applied_defaults[f"invalid::{req_path}"] = str(invalid_select_value)
            if not f.get("send_if_empty"):
                continue

        value = _cast_cfg_value(raw_value, f.get("data_type"))
        json_set(payload, req_path, value)

    # ---------------------------------------------------------------------
    # Smart Trip conditional required-field rule:
    #
    # return_date is NOT globally required because ONE_WAY search does not
    # need it. But for ROUND_TRIP / return flight, return_date is mandatory.
    #
    # Your log already shows:
    # normalized_intent.missing_fields = ["return_date"]
    #
    # But the UI renders only missing_required from this function.
    # So we must force search.return_date into missing_required when:
    #   trip_type = ROUND_TRIP
    #   return_date is empty
    # ---------------------------------------------------------------------
    def _already_missing(req_path_value: str) -> bool:
        return any(
            str(m.get("request_json_path") or "").strip() == req_path_value
            or str(m.get("route_key") or "").strip() == "return_date"
            for m in missing_required
            if isinstance(m, dict)
        )

    if trip_type == "ROUND_TRIP" and not str(rp.get("return_date") or "").strip():
        return_date_cfg = None

        for cfg_field in fields or []:
            if str(cfg_field.get("request_json_path") or "").strip() == "search.return_date":
                return_date_cfg = cfg_field
                break

        if return_date_cfg and not _already_missing("search.return_date"):
            mark_missing(return_date_cfg, "search.return_date")

        elif not _already_missing("search.return_date"):
            missing_required.append(
                {
                    "cfg_id": None,
                    "label": "Return Date",
                    "name": "return_date",
                    "request_json_path": "search.return_date",
                    "route_key": "return_date",
                    "data_type": "DATE",
                    "ui_control_type": "DATE",
                    "ui_mode": "TEXT",
                    "options": [],
                    "default_value": "",
                    "prompt": "Please provide Return Date.",
                    "placeholder": "Select return date",
                    "hint": "Return date is required for round trip.",
                }
            )

    return payload, missing_required, applied_defaults


def _safe_audit_info(session_id: int | None, event_type: str, message: str, details: dict | None = None):
    if not session_id:
        return
    try:
        log_info(int(session_id), "TOOL", event_type, message, details=details)
    except Exception:
        pass


def _safe_audit_fail(session_id: int | None, event_type: str, message: str, err: Exception, details: dict | None = None):
    if not session_id:
        return
    try:
        log_fail(int(session_id), "TOOL", event_type, message, err, details=details)
    except Exception:
        pass


def _resolve_selected_provider(request: Request, provider_code: str | None = None) -> dict | None:
    code = str(provider_code or request.query_params.get("provider_code") or request.cookies.get(LLM_PROVIDER_COOKIE_NAME) or "").strip().upper()
    provider = get_llm_provider_by_code(code) if code else None
    if provider:
        return provider
    return get_active_default_llm_provider()


def _apply_provider_cookie(response, provider: dict | None):
    code = str((provider or {}).get("provider_code") or "").strip().upper()
    if not code:
        return response
    try:
        response.set_cookie(LLM_PROVIDER_COOKIE_NAME, code, httponly=False, samesite="Lax", path="/")
    except Exception:
        pass
    return response


def _get_session_id_from_request(request: Request) -> int | None:
    sess = _get_active_session_or_redirect(request)
    if not sess:
        return None
    try:
        return int(sess["session_id"])
    except Exception:
        return None


def _get_active_session_or_redirect(request: Request):
    session_uuid = get_session_uuid_from_request(request)
    sess = get_active_session_by_uuid(session_uuid) if session_uuid else None
    if not sess:
        return None
    return sess

import re
from typing import Any, Dict



def _contains_any_keyword_phrase(text: str, phrases: set[str]) -> bool:
    """Return True when any blocked non-airline phrase appears as a word/phrase."""
    safe_text = f" {str(text or '').strip().lower()} "
    for phrase in phrases:
        safe_phrase = str(phrase or "").strip().lower()
        if not safe_phrase:
            continue
        if " " in safe_phrase:
            if f" {safe_phrase} " in safe_text:
                return True
        else:
            if re.search(rf"\b{re.escape(safe_phrase)}\b", safe_text):
                return True
    return False


def _is_non_airline_booking_request(text: str) -> bool:
    """Block non-airline domains before LLM/flight intent routing."""
    blocked_phrases = {
        # Medical / appointment domain
        "doctor", "appointment", "clinic", "hospital", "dentist", "physician", "medical",

        # Cinema / entertainment
        "cinema", "movie", "film", "theatre", "theater", "concert", "event",

        # Non-flight transport / local services
        "train", "railway", "rail", "bus", "coach", "cab", "taxi", "auto", "rickshaw",

        # Non-flight travel services
        "hotel", "restaurant", "table booking", "room booking",

        # Sports / other ticketing
        "cricket", "match", "stadium",
    }
    return _contains_any_keyword_phrase(text, blocked_phrases)


def _is_airline_information_only_request(text: str) -> bool:
    """Block airline-related information/support queries that are not booking/search intents.

    Important demo rule:
    A sentence may contain words like show/find/search/flight/from/to, but if the
    real subject is status, baggage rules, visa documents, or meal/menu options,
    it is not a booking request and must not enter LLM extraction/search flow.

    Examples to block:
    - Can you show me the flight status from Mumbai to Bahrain for tomorrow?
    - Can you help me find baggage rules for a flight from Mumbai to Bahrain?
    - I am planning a trip to Bahrain. Can you tell me what visa documents are required?
    - Can you show dinner meal options available on flights from Mumbai to Bahrain?

    Examples to allow:
    - Book a flight from Mumbai to Bahrain with dinner meal.
    - Search cheapest flights from Mumbai to Bahrain.
    """
    t = str(text or "").strip().lower()
    if not t:
        return False

    # ------------------------------------------------------------------
    # Hard information/support topics. These must win over generic words
    # like show/find/search/flight because those words also appear in
    # information-only questions.
    # ------------------------------------------------------------------
    hard_information_only_patterns = [
        # Flight operational/status/support information
        r"\bflight\s+status\b",
        r"\bstatus\s+of\s+(my\s+)?flight\b",
        r"\btrack\s+(my\s+)?flight\b",
        r"\bpnr\s+status\b",
        r"\bflight\s+number\b",
        r"\bflight\s*#\b",

        # Baggage/rules/policy information
        r"\bbaggage\b.*\b(rule|rules|allowance|policy|policies|limit|limits|weight)\b",
        r"\b(rule|rules|allowance|policy|policies|limit|limits|weight)\b.*\bbaggage\b",
        r"\bhand\s+baggage\b",
        r"\bcheck(?:ed)?\s+baggage\b",

        # Visa/document/passport information
        r"\bvisa\b",
        r"\b(documents?|passport)\b.*\b(required|requirement|requirements|needed|need)\b",
        r"\bwhat\s+documents?\b",

        # Meal/menu/service information only.
        # Do not block normal booking meal preferences like:
        # "Book a flight ... with dinner meal" because that does not match
        # option/menu/available wording below.
        r"\b(meal|meals|dinner|lunch|food)\b.*\b(option|options|menu|available|availability)\b",
        r"\b(option|options|menu|available|availability)\b.*\b(meal|meals|dinner|lunch|food)\b",

        # General helpdesk/info wording connected with rules/policies.
        r"\b(help|tell|explain)\b.*\b(rule|rules|policy|policies|required|requirement|requirements)\b",
    ]

    if any(re.search(pattern, t) for pattern in hard_information_only_patterns):
        return True

    # Generic information-only wording where no booking/fare action is present.
    generic_info_patterns = [
        r"\b(can you|could you|please)?\s*(tell|explain|help)\b.*\b(flight|airline|airport|trip|travel)\b",
        r"\bwhat\s+(is|are)\b.*\b(rule|rules|policy|policies|requirement|requirements)\b",
    ]
    if any(re.search(pattern, t) for pattern in generic_info_patterns):
        true_booking_or_fare_intent = any(re.search(pattern, t) for pattern in [
            r"\bbook\b.*\b(flight|flights|airline|airlines|fare|fares)\b",
            r"\breserve\b.*\b(flight|flights|airline|airlines)\b",
            r"\b(search|find|show|display|list|check|get|give\s+me)\b.*\b(available\s+)?(flight\s+options|flights|fares|fare)\b",
            r"\b(cheapest|cheap|lowest|low\s+cost|budget|best\s+price|minimum\s+price)\b.*\b(flight|flights|fare|fares)\b",
        ])
        return not true_booking_or_fare_intent

    return False

def _classify_llm_chat_scope(message: str) -> Dict[str, Any]:
    """Classify a chat message before sending it into the booking flow."""
    raw_text = (message or "").strip()

    non_travel_message = (
    "It seems your request is outside the airline flight booking flow.\n\n"
    "As per Smart Trip policy, this assistant currently supports airline flight search and booking requests only. "
    "Other service requests or information-only queries are not processed to avoid unnecessary LLM and API calls, "
    "as they may result in additional cost without adding value to the flight booking flow.\n\n"
    "Please enter a flight request such as:\n"
    "Book a flight from Mumbai to Bahrain on 20-May-2026 for 1 adult, currency INR, cabin economy."
    )

    if not raw_text:
        return {"bucket": "NON_TRAVEL", "allow_main_flow": False, "user_message": non_travel_message}

    text = raw_text.lower().replace("’", "'").replace("`", "'")

    # Handles accidental copy/paste from chat UI:
    # Example:
    # You
    # I want to book a round trip...
    text = re.sub(r"^\s*you\s+", "", text, flags=re.I)

    text = re.sub(r"[^\w\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    replacements = {
        "hru": "how are you",
        "hw r u": "how are you",
        "how r u": "how are you",
        "hi how r u": "hi how are you",
        "hey how r u": "hey how are you",
        "hey hru": "hey how are you",
        "how are u": "how are you",
        "how ru": "how are you",
        "how u doing": "how are you doing",
        "how you doing": "how are you doing",
        "hi how you doing": "hi how are you doing",
        "how you doin": "how are you doing",
        "whats up": "what is up",
        "what's up": "what is up",
        "wats up": "what is up",
        "wassup": "what is up",
        "sup": "what is up",
        "gm": "good morning",
        "gn": "good night",
        "gud morning": "good morning",
        "gud afternoon": "good afternoon",
        "gud evening": "good evening",
        "gud night": "good night",
    }
    normalized_text = replacements.get(text, text)

    greeting_exact = {
        "hi", "hii", "hiii", "hello", "helo", "helloo", "hey", "heyy", "heyyy",
        "hy", "hay", "hiya", "yo", "howdy", "namaste", "namaskar", "salam", "salaam","salaam waleyum","as salaam waleyum",
        "good morning", "good afternoon", "good evening", "good day", "good night",
    }

    wellbeing_exact = {
        "how are you", "how are you doing", "how are you today", "how are you doing today",
        "how is it going", "how's it going", "how is everything", "how are things",
        "hope you are well", "hope you are doing well", "are you there", "you there",
    }

    casual_exact = {
        "what is up", "what is going on", "what are you doing", "what you doing",
        "what is plan today", "whats plan today", "what's plan today", "what is the plan today",
        "can you help", "can you help me", "help me", "i need help", "need help",
        "ok", "okay", "fine", "great", "nice", "cool", "perfect", "thanks", "thank you", "thx",
    }

    goodbye_exact = {
        "bye", "goodbye", "see you", "see you later", "talk to you later",
    }

    # -------------------------------------------------------------------------
    # 1) HARD NON-AIRLINE DOMAIN GUARD
    # -------------------------------------------------------------------------
    # This must run BEFORE the positive airline guard.
    # Clear non-airline booking domains like cinema, bus, train, cab, hotel,
    # doctor appointment, event, or sports ticketing should not enter LLM flow,
    # even when the text also contains generic words like book/search/find/trip/ticket.
    # -------------------------------------------------------------------------

    if _is_non_airline_booking_request(normalized_text):
        return {"bucket": "NON_AIRLINE_BOOKING", "allow_main_flow": False, "user_message": non_travel_message}

    # -------------------------------------------------------------------------
    # 2) AIRLINE INFORMATION-ONLY GUARD
    # -------------------------------------------------------------------------
    # These are airline-related, but they are not flight booking/search intents.
    # Examples: flight status, baggage rules, visa documents, meal option menu.
    # They must not enter the LLM extraction/search flow.
    # -------------------------------------------------------------------------

    if _is_airline_information_only_request(normalized_text):
        return {"bucket": "AIRLINE_INFO_ONLY", "allow_main_flow": False, "user_message": non_travel_message}

    # -------------------------------------------------------------------------
    # 3) STRONG POSITIVE AIRLINE GUARD
    # -------------------------------------------------------------------------
    # Reason:
    # In airline booking language, words like "show", "display", "list",
    # "find", "search", and "check" are valid when used with fares/flights.
    #
    # Examples:
    # - Show economy fares in INR
    # - Please show economy class fares in INR
    # - Display available flights
    # - Find economy fares
    # - Check return flight fares
    # -------------------------------------------------------------------------

    intent_patterns = [
        # Direct booking/search phrases, including words between action and flight.
        r"\bbook\b.*\b(flight|flights|return\s+flight|round\s+trip|return\s+trip|one\s+way|one\s+way\s+flight|trip|ticket|tickets|journey|travel|fare|fares)\b",
        r"\b(plan|find|search|need|reserve|show|display|list|check|get|give\s+me)\b.*\b(flight|flights|return\s+flight|round\s+trip|return\s+trip|one\s+way|one\s+way\s+flight|trip|ticket|tickets|journey|travel|fare|fares)\b",

        # Natural fare display phrases.
        r"\b(show|display|list|find|search|check|get|give\s+me)\b.*\b(economy|business|first|premium\s+economy)\b.*\b(fare|fares|class|ticket|tickets)\b",
        r"\b(show|display|list|find|search|check|get|give\s+me)\b.*\b(fare|fares)\b.*\b(inr|bhd|usd|aed|eur|gbp|sar|qar|omr|kwd)\b",
        r"\bplease\s+show\b.*\b(economy|business|first|premium\s+economy)\b.*\b(fare|fares|class)\b",

        # Common airline booking phrases.
        r"\b(return|round)\s+(flight|trip|ticket)\b",
        r"\bround[-\s]?trip\b",
        r"\bone[-\s]?way\b",
        r"\breturn\s+date\b",
        r"\bdepart(ure)?\s+date\b",
        r"\bcabin\s+(class\s+)?(economy|business|first|premium\s+economy)\b",
        r"\b(economy|business|first|premium\s+economy)\s+(class\s+)?(fare|fares|ticket|tickets)?\b",
        r"\bpreferred\s+airline\b",

        # Route and passenger clues.
        r"\bflight\s+(from|to|on|for)\b",
        r"\bfrom\s+[a-z ]+\s+to\s+[a-z ]+\b",
        r"\b(adult|adults|child|children|infant|infants|passenger|passengers|traveller|travellers|traveler|travelers)\b",
    ]

    # Clear booking/trip intent should always win, even if greeting words are also present.
    if any(re.search(pattern, normalized_text) for pattern in intent_patterns):
        return {"bucket": "TRAVEL", "allow_main_flow": True, "user_message": None}

    # -------------------------------------------------------------------------
    # 2) GREETING / CASUAL HANDLING
    # -------------------------------------------------------------------------
    # Keep greetings local and do not send them to LLM.
    # This is intentionally after positive travel guard so mixed text like:
    # "Hi, book a flight from Mumbai to Bahrain..."
    # still goes to travel flow.
    #
    # V14 enhancement:
    # Greeting reply is now read from greeting_mst instead of hard-coded text.
    # Matching rule: normalize raw user input by keeping alphabets only,
    # lowercasing it, then exact-match greeting_mst.greeting_key.
    # -------------------------------------------------------------------------

    greeting_row = find_active_greeting_by_message(raw_text)
    if greeting_row:
        return {
            "bucket": "GREETING",
            "allow_main_flow": False,
            "user_message": greeting_row.get("user_message"),
            "greeting_id": greeting_row.get("greeting_id"),
            "greeting_key": greeting_row.get("greeting_key"),
            "greeting_type": greeting_row.get("greeting_type"),
        }

    if normalized_text in goodbye_exact:
        return {
            "bucket": "GREETING",
            "allow_main_flow": False,
            "user_message": "Goodbye! Whenever you are ready, share your travel plan and I will help you book your flight step by step.",
        }

    if normalized_text in greeting_exact:
        return {
            "bucket": "GREETING",
            "allow_main_flow": False,
            "user_message": "Hello! How can I help with your travel plans today?",
        }

    if normalized_text in wellbeing_exact or any(re.fullmatch(pattern, normalized_text) for pattern in [
        r"(hi|hii|hello|helo|hey|heyy|hy|hay|yo|namaste|salam)\s+(how are you|how are you doing|how is it going|salaam waleyum|as salaam waleyum)",
        r"(how are you|how are you doing|how is it going)\s+(today|dear|buddy|friend)?",
    ]):
        return {
            "bucket": "GREETING",
            "allow_main_flow": False,
            "user_message": "I’m doing well, thank you. Please share your travel booking plan in one message, and I will guide you step by step.",
        }

    if normalized_text in casual_exact:
        return {
            "bucket": "CASUAL",
            "allow_main_flow": False,
            "user_message": "I’m here and ready to help with your flight booking. Share your trip details like from city, to city, travel date, passengers, cabin class, and currency.",
        }

    # -------------------------------------------------------------------------
    # 3) NON-AIRLINE DOMAIN GUARD
    # -------------------------------------------------------------------------
    # IMPORTANT:
    # Do NOT keep "show" in non_airline_booking_keywords.
    #
    # "show economy fares in INR" is valid airline language.
    # "show" by itself is not a domain. It is only an action word.
    # -------------------------------------------------------------------------

    non_airline_booking_keywords = {
        "cinema", "movie", "movies", "film", "films", "theatre", "theater",
        "train", "rail", "railway", "metro", "bus", "coach",
        "hotel", "room", "restaurant", "cab", "taxi",
        "doctor", "appointment", "clinic", "hospital", "dentist", "physician", "medical",
        "concert", "event", "cricket", "match", "stadium", "mall",
    }

    airline_scope_keywords = {
        "flight", "flights", "airline", "airlines", "airways", "air", "airport",
        "airports", "plane", "airplane", "aircraft", "aviation",
        "fare", "fares", "cabin", "economy", "business", "first",
        "round", "return", "departure", "depart", "passenger", "passengers",
        "adult", "adults", "child", "children", "infant", "infants",
    }

    tokens = set(normalized_text.split())
    has_non_airline_keyword = any(word in tokens for word in non_airline_booking_keywords)
    has_airline_scope_keyword = any(word in tokens for word in airline_scope_keywords)

    if has_non_airline_keyword and not has_airline_scope_keyword:
        return {
            "bucket": "NON_TRAVEL",
            "allow_main_flow": False,
            "user_message": non_travel_message,
        }

    # Non-airline domain words must still win for clear medical/event/non-flight cases.
    # Example:
    # "book a flight appointment with doctor"
    # contains "flight", but is still a doctor appointment request.
    if _is_non_airline_booking_request(normalized_text):
        return {"bucket": "NON_TRAVEL", "allow_main_flow": False, "user_message": non_travel_message}

    return {"bucket": "NON_TRAVEL", "allow_main_flow": False, "user_message": non_travel_message}


def _ensure_return_date_missing_field_for_ui(
    normalized_intent: Dict[str, Any],
    route_payload: Dict[str, Any],
    missing_fields: list,
) -> list:
    """
    Ensure return_date is shown in the correction UI when trip_type is ROUND_TRIP.

    Why:
    normalized_intent.missing_fields may already contain ["return_date"],
    but the UI renders only the top-level missing_fields list.
    """

    if missing_fields is None:
        missing_fields = []

    # Convert pydantic/model object to dict if needed
    if hasattr(normalized_intent, "dict"):
        normalized_intent = normalized_intent.dict()

    if hasattr(route_payload, "dict"):
        route_payload = route_payload.dict()

    normalized_intent = normalized_intent or {}
    route_payload = route_payload or {}

    trip_type = str(
        route_payload.get("trip_type")
        or normalized_intent.get("trip_type")
        or ""
    ).upper().replace(" ", "_").replace("-", "_")

    return_date = (
        route_payload.get("return_date")
        or normalized_intent.get("return_date")
        or ""
    )

    normalized_missing = normalized_intent.get("missing_fields") or []

    needs_return_date = (
        trip_type in ("ROUND_TRIP", "RETURN_TRIP", "RETURN")
        and not str(return_date).strip()
        and "return_date" in normalized_missing
    )

    if not needs_return_date:
        return missing_fields

    def _already_exists(item: Dict[str, Any]) -> bool:
        return (
            str(item.get("route_key") or "").strip() == "return_date"
            or str(item.get("name") or "").strip() == "return_date"
            or str(item.get("request_json_path") or "").strip() == "search.return_date"
        )

    if any(_already_exists(item) for item in missing_fields if isinstance(item, dict)):
        return missing_fields

    missing_fields.append(
        {
            "hint": "Return date is required for round trip.",
            "name": "return_date",
            "label": "Return Date",
            "cfg_id": None,
            "prompt": "Please enter Return Date.",
            "options": [],
            "ui_mode": "DATE",
            "data_type": "DATE",
            "route_key": "return_date",
            "placeholder": "Select return date",
            "default_value": "",
            "ui_control_type": "DATE",
            "request_json_path": "search.return_date",
        }
    )

    return missing_fields
    
@router.get("/start", response_class=HTMLResponse)
def llm_chat_start(request: Request):
    sess = _get_active_session_or_redirect(request)
    if not sess:
        return RedirectResponse(url="/login", status_code=302)
    provider = _resolve_selected_provider(request)
    _safe_audit_info(
        int(sess["session_id"]),
        "LLM_CHAT_START",
        "LLM chat start page requested",
        details={"provider_code": (provider or {}).get("provider_code"), "provider_name": (provider or {}).get("provider_name")},
    )
    response = RedirectResponse(url="/portal/llm/chat", status_code=302)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return _apply_provider_cookie(response, provider)


@router.get("/chat", response_class=HTMLResponse)
def llm_chat_page(request: Request):
    sess = _get_active_session_or_redirect(request)
    if not sess:
        return RedirectResponse(url="/login", status_code=302)
    provider = _resolve_selected_provider(request)
    _safe_audit_info(
        int(sess["session_id"]),
        "LLM_CHAT_OPEN",
        "LLM chat page opened",
        details={"provider_code": (provider or {}).get("provider_code"), "provider_name": (provider or {}).get("provider_name")},
    )
    response = templates.TemplateResponse(
        "llm_chat.html",
        {
            "request": request,
            "session_id": int(sess["session_id"]),
            "llm_provider_code": (provider or {}).get("provider_code") or "",
            "llm_provider_name": (provider or {}).get("provider_name") or "Default Provider",
            "today_date": date.today().isoformat(),
            "llm_chat_patch_version": "resume-v2",
        },
    )
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return _apply_provider_cookie(response, provider)


@router.post("/intent", response_model=LLMIntentResponse)
def llm_intent_assist(request: Request, payload: LLMIntentRequest) -> LLMIntentResponse:
    session_id = _get_session_id_from_request(request)
    provider = _resolve_selected_provider(request, payload.provider_code)
    _safe_audit_info(
        session_id,
        "LLM_INTENT_START",
        "LLM intent analysis started",
        details={
            "user_input": payload.message,
            "today_date": payload.today_date,
            "provider_code": (provider or {}).get("provider_code"),
            "provider_name": (provider or {}).get("provider_name"),
        },
    )
    try:
        scope_result = _classify_llm_chat_scope(payload.message)
        if not scope_result.get("allow_main_flow"):
            response = LLMIntentResponse(
                status="SUCCESS",
                next_action="SHOW_MESSAGE",
                next_route=None,
                user_message=scope_result.get("user_message"),
                errors=[],
                llm_intent=None,
                normalized_intent=None,
                missing_fields=[],
                route_payload=None,
            )
            _safe_audit_info(
                session_id,
                "LLM_INTENT_SCOPE_BLOCKED",
                "LLM intent request handled by pre-check scope classifier",
                details={
                    "user_input": payload.message,
                    "bucket": scope_result.get("bucket"),
                    "provider_code": (provider or {}).get("provider_code"),
                    "provider_name": (provider or {}).get("provider_name"),
                },
            )
            return response

        rewritten_message = _rewrite_airline_phrases_for_llm(payload.message)
        initial_state = LLMGraphState(
            user_input=rewritten_message,
            today_date=payload.today_date,
            provider_code=(provider or {}).get("provider_code"),
        )
        final_state = llm_graph.invoke(initial_state)
        if isinstance(final_state, dict):
            llm_intent_obj = final_state.get("llm_intent")
            normalized_intent_obj = final_state.get("normalized_intent")
            normalized_intent_dict = normalized_intent_obj.model_dump() if hasattr(normalized_intent_obj, "model_dump") else normalized_intent_obj
            normalized_intent_dict = _apply_preferred_airline_fallback(normalized_intent_dict, payload.message)
            missing_fields, route_payload = _build_missing_field_descriptors_for_intent(normalized_intent_dict)
            next_action = final_state.get("next_action")
            next_route = final_state.get("next_route")
            user_message = final_state.get("user_message")
            if missing_fields:
                next_action = "ASK_MISSING_FIELDS"
                next_route = None
                labels = ", ".join([str(m.get("route_key") or m.get("name") or m.get("label") or "").strip() for m in missing_fields if m])
                user_message = f"I need a few more details before I can continue: {labels}" if labels else "I need a few more details before I can continue."
            response = LLMIntentResponse(
                status=final_state.get("status", "FAILED"),
                next_action=next_action,
                next_route=next_route,
                user_message=user_message,
                errors=final_state.get("errors", []),
                llm_intent=llm_intent_obj.model_dump() if hasattr(llm_intent_obj, "model_dump") else llm_intent_obj,
                normalized_intent=normalized_intent_dict,
                missing_fields=missing_fields,
                route_payload=route_payload,
            )
        else:
            normalized_intent_dict = final_state.normalized_intent.model_dump() if final_state.normalized_intent else None
            normalized_intent_dict = _apply_preferred_airline_fallback(normalized_intent_dict, payload.message)
            missing_fields, route_payload = _build_missing_field_descriptors_for_intent(normalized_intent_dict)
            next_action = final_state.next_action
            next_route = final_state.next_route
            user_message = final_state.user_message
            if missing_fields:
                next_action = "ASK_MISSING_FIELDS"
                next_route = None
                labels = ", ".join([str(m.get("route_key") or m.get("name") or m.get("label") or "").strip() for m in missing_fields if m])
                user_message = f"I need a few more details before I can continue: {labels}" if labels else "I need a few more details before I can continue."
            response = LLMIntentResponse(
                status=final_state.status,
                next_action=next_action,
                next_route=next_route,
                user_message=user_message,
                errors=final_state.errors,
                llm_intent=final_state.llm_intent.model_dump() if final_state.llm_intent else None,
                normalized_intent=normalized_intent_dict,
                missing_fields=missing_fields,
                route_payload=route_payload,
            )
        provider_msg = _provider_connection_message(provider, "\n".join(response.errors or []))
        if response.status == "FAILED":
            salvaged_response = _build_response_from_salvage(payload.message)
            if salvaged_response:
                response = salvaged_response
            else:
                response.user_message = provider_msg or response.user_message or "I could not decide the next step for your request."

        _safe_save_llm_state(
            session_id,
            provider,
            _build_llm_persisted_state(
                status=response.status,
                next_action=response.next_action,
                missing_fields=response.missing_fields,
                route_payload=response.route_payload,
                normalized_intent=response.normalized_intent,
                llm_intent=response.llm_intent,
            ),
            payload.message,
        )

        _safe_audit_info(
            session_id,
            "LLM_INTENT_DONE",
            "LLM intent analysis completed",
            details={
                "user_input": payload.message,
                "today_date": payload.today_date,
                "provider_code": (provider or {}).get("provider_code"),
                "provider_name": (provider or {}).get("provider_name"),
                "status": response.status,
                "next_action": response.next_action,
                "next_route": response.next_route,
                "errors": response.errors,
                "llm_intent": response.llm_intent,
                "normalized_intent": response.normalized_intent,
                "missing_fields": response.missing_fields,
                "route_payload": response.route_payload,
            },
        )
        return response
    except Exception as exc:
        salvaged_response = _build_response_from_salvage(payload.message)
        if salvaged_response:
            _safe_audit_info(
                session_id,
                "LLM_INTENT_FALLBACK_DONE",
                "LLM intent fallback salvage completed",
                details={
                    "user_input": payload.message,
                    "today_date": payload.today_date,
                    "provider_code": (provider or {}).get("provider_code"),
                    "provider_name": (provider or {}).get("provider_name"),
                    "status": salvaged_response.status,
                    "next_action": salvaged_response.next_action,
                    "next_route": salvaged_response.next_route,
                    "normalized_intent": salvaged_response.normalized_intent,
                    "route_payload": salvaged_response.route_payload,
                    "missing_fields": salvaged_response.missing_fields,
                    "fallback_reason": str(exc),
                },
            )
            _safe_save_llm_state(
                session_id,
                provider,
                _build_llm_persisted_state(
                    status=salvaged_response.status,
                    next_action=salvaged_response.next_action,
                    missing_fields=salvaged_response.missing_fields,
                    route_payload=salvaged_response.route_payload,
                    normalized_intent=salvaged_response.normalized_intent,
                    llm_intent=salvaged_response.llm_intent,
                ),
                payload.message,
            )
            return salvaged_response
        _safe_audit_fail(
            session_id,
            "LLM_INTENT_FAIL",
            "LLM intent analysis failed",
            exc,
            details={
                "user_input": payload.message,
                "today_date": payload.today_date,
                "provider_code": (provider or {}).get("provider_code"),
                "provider_name": (provider or {}).get("provider_name"),
            },
        )
        provider_msg = _provider_connection_message(provider, str(exc))
        raise HTTPException(status_code=500, detail=provider_msg or f"LLM intent assist failed: {str(exc)}")


@router.post("/confirm-date", response_model=LLMDateConfirmResponse)
def llm_confirm_date(request: Request, payload: LLMDateConfirmRequest) -> LLMDateConfirmResponse:
    session_id = _get_session_id_from_request(request)
    provider = _resolve_selected_provider(request, payload.provider_code)
    route_payload_dict = payload.route_payload or {}
    normalized_intent_dict = payload.normalized_intent or {}
    _safe_audit_info(
        session_id,
        "LLM_DATE_CONFIRM_START",
        "LLM date confirmation started",
        details={
            "user_input": payload.message,
            "today_date": payload.today_date,
            "selected_date": payload.selected_date,
            "provider_code": (provider or {}).get("provider_code"),
            "provider_name": (provider or {}).get("provider_name"),
            "has_route_payload": bool(route_payload_dict),
            "has_normalized_intent": bool(normalized_intent_dict),
        },
    )
    try:
        if not route_payload_dict and not normalized_intent_dict:
            raise ValueError("No saved normalized intent or route payload was provided for date confirmation.")

        merged_route_payload = dict(route_payload_dict or {})
        merged_normalized_intent = dict(normalized_intent_dict or {})
        merged_route_payload["depart_date"] = payload.selected_date
        merged_normalized_intent["depart_date"] = payload.selected_date
        if merged_normalized_intent.get("return_date") and not merged_normalized_intent.get("trip_type"):
            merged_normalized_intent["trip_type"] = "ROUND_TRIP"
        if merged_route_payload.get("return_date") and not merged_route_payload.get("trip_type"):
            merged_route_payload["trip_type"] = "ROUND_TRIP"
        merged_normalized_intent["trip_type"] = merged_normalized_intent.get("trip_type") or merged_route_payload.get("trip_type") or "ONE_WAY"
        merged_route_payload["trip_type"] = merged_route_payload.get("trip_type") or merged_normalized_intent.get("trip_type") or "ONE_WAY"
        merged_route_payload["from_city"] = merged_route_payload.get("from_city") or merged_normalized_intent.get("from_city")
        merged_route_payload["to_city"] = merged_route_payload.get("to_city") or merged_normalized_intent.get("to_city")
        merged_route_payload["return_date"] = merged_route_payload.get("return_date") or merged_normalized_intent.get("return_date")
        merged_route_payload["adults"] = merged_route_payload.get("adults", merged_normalized_intent.get("adults", 1))
        merged_route_payload["children"] = merged_route_payload.get("children", merged_normalized_intent.get("children", 0))
        merged_route_payload["infants"] = merged_route_payload.get("infants", merged_normalized_intent.get("infants", 0))
        merged_route_payload["cabin_class"] = merged_route_payload.get("cabin_class") or merged_normalized_intent.get("cabin_class")
        merged_route_payload["currency"] = merged_route_payload.get("currency") or merged_normalized_intent.get("currency")
        merged_route_payload["meal_preference"] = merged_route_payload.get("meal_preference") or merged_normalized_intent.get("meal_preference")
        merged_route_payload["preferred_airline"] = (
            merged_route_payload.get("preferred_airline")
            or (merged_normalized_intent.get("preferred_airline") if not _is_price_search_preference(merged_normalized_intent.get("preferred_airline")) else None)
        )
        merged_route_payload["search_preference"] = merged_route_payload.get("search_preference") or merged_normalized_intent.get("search_preference")

        response = LLMDateConfirmResponse(
            status="SUCCESS",
            next_action="ROUTE_TO_SEARCH",
            next_route="/portal/llm/route-to-search",
            user_message=f"I understood your request. I will use departure date {payload.selected_date} and continue to flight search.",
            errors=[],
            normalized_intent=merged_normalized_intent,
            route_payload=merged_route_payload,
        )
        _safe_save_llm_state(
            session_id,
            provider,
            _build_llm_persisted_state(
                status=response.status,
                next_action=response.next_action,
                missing_fields=[],
                route_payload=response.route_payload,
                normalized_intent=response.normalized_intent,
            ),
            payload.message,
        )
        _safe_audit_info(
            session_id,
            "LLM_DATE_CONFIRM_DONE",
            "LLM date confirmation completed",
            details={
                "user_input": payload.message,
                "today_date": payload.today_date,
                "selected_date": payload.selected_date,
                "provider_code": (provider or {}).get("provider_code"),
                "provider_name": (provider or {}).get("provider_name"),
                "status": response.status,
                "next_action": response.next_action,
                "next_route": response.next_route,
                "errors": response.errors,
                "normalized_intent": response.normalized_intent,
                "route_payload": response.route_payload,
            },
        )
        return response
    except Exception as exc:
        _safe_audit_fail(
            session_id,
            "LLM_DATE_CONFIRM_FAIL",
            "LLM date confirmation failed",
            exc,
            details={
                "user_input": payload.message,
                "today_date": payload.today_date,
                "selected_date": payload.selected_date,
                "provider_code": (provider or {}).get("provider_code"),
                "provider_name": (provider or {}).get("provider_name"),
                "has_route_payload": bool(route_payload_dict),
                "has_normalized_intent": bool(normalized_intent_dict),
            },
        )
        raise HTTPException(status_code=500, detail=f"LLM date confirmation failed: {str(exc)}")


@router.post("/resume", response_model=LLMResumeResponse)
def llm_resume_missing_field(request: Request, payload: LLMResumeRequest) -> LLMResumeResponse:
    session_id = _get_session_id_from_request(request)
    try:
        route_payload_dict = payload.route_payload.model_dump() if hasattr(payload.route_payload, "model_dump") else dict(payload.route_payload or {})
        if not route_payload_dict:
            saved_state = _safe_load_llm_state(session_id)
            if isinstance(saved_state, dict):
                route_payload_dict = dict(saved_state.get("route_payload") or {})
        route_payload_dict = _set_route_payload_value(route_payload_dict, payload.field_name, payload.value)
        missing_fields, route_payload_dict = _recompute_missing_fields_from_route_payload(route_payload_dict)
        next_action = 'ASK_MISSING_FIELDS' if missing_fields else 'ROUTE_TO_SEARCH'
        response = LLMResumeResponse(
            status='SUCCESS',
            next_action=next_action,
            user_message='Missing field updated.' if next_action == 'ROUTE_TO_SEARCH' else 'Please provide the next missing detail.',
            missing_fields=missing_fields,
            route_payload=route_payload_dict,
        )
        saved_state = _safe_load_llm_state(session_id) or {}
        _safe_save_llm_state(
            session_id,
            provider=None,
            state=_build_llm_persisted_state(
                status=response.status,
                next_action=response.next_action,
                missing_fields=response.missing_fields,
                route_payload=response.route_payload,
                normalized_intent=saved_state.get("normalized_intent") or {},
                llm_intent=saved_state.get("llm_intent") or {},
            ),
            user_message=str(payload.value) if payload.value is not None else None,
        )
        _safe_audit_info(
            session_id,
            'LLM_RESUME_DONE',
            'LLM missing-field continuation processed',
            details={
                'field_name': payload.field_name,
                'input_value': payload.value,
                'next_action': next_action,
                'route_payload': route_payload_dict,
                'missing_fields': missing_fields,
            },
        )
        return response
    except Exception as exc:
        _safe_audit_fail(session_id, 'LLM_RESUME_FAIL', 'LLM missing-field continuation failed', exc, details={'field_name': payload.field_name, 'input_value': payload.value})
        raise HTTPException(status_code=400, detail=f'LLM resume failed: {str(exc)}')





def _get_app_config_value(config_name: str, default: str = "") -> str:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT config_value FROM app_config WHERE config_name=%s LIMIT 1", (config_name,))
                row = cur.fetchone()
        if not row:
            return default
        value = row.get("config_value") if isinstance(row, dict) else row[0]
        return str(value).strip() if value not in (None, "") else default
    except Exception:
        return default


def _format_display_datetime(value: object, fmt: str | None = None) -> str:
    s = str(value or "").strip()
    if not s:
        return ""
    fmt = fmt or _get_app_config_value("DATETIME_DISPLAY_FORMAT", "%a %d %b %Y %H:%M")
    candidates = [s]
    if 'T' in s:
        candidates.append(s.replace('T', ' '))
    for cand in candidates:
        try:
            dt = datetime.fromisoformat(cand)
            return dt.strftime(fmt)
        except Exception:
            pass
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, pattern)
            return dt.strftime(fmt)
        except Exception:
            pass
    return s

def _safe_float(value: object) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _duration_minutes_from_any(value: object) -> int:
    if value in (None, ""):
        return 999999
    s = str(value).strip()
    if not s:
        return 999999
    if s.isdigit():
        return int(s)
    m = re.match(r"^(\d{1,2}):(\d{2})$", s)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.search(r"(\d+)\s*h", s, re.I)
    h = int(m.group(1)) if m else 0
    m2 = re.search(r"(\d+)\s*m", s, re.I)
    mm = int(m2.group(1)) if m2 else 0
    if h or mm:
        return h * 60 + mm
    return 999999


def _summarize_round_trip_cards(cards: list[dict], searched_cabin_class: str = "") -> list[dict]:
    out: list[dict] = []
    searched_cabin = str(searched_cabin_class or "").strip()
    dt_fmt = _get_app_config_value("DATETIME_DISPLAY_FORMAT", "%a %d %b %Y %H:%M")
    for idx, card in enumerate(cards or [], 1):
        outbound = card.get("outbound") if isinstance(card.get("outbound"), dict) else {}
        ret = card.get("return") if isinstance(card.get("return"), dict) else {}
        out_air = outbound.get("airline") if isinstance(outbound.get("airline"), dict) else {}
        ret_air = ret.get("airline") if isinstance(ret.get("airline"), dict) else {}
        out_route = outbound.get("route") if isinstance(outbound.get("route"), dict) else {}
        ret_route = ret.get("route") if isinstance(ret.get("route"), dict) else {}
        out_from = out_route.get("from") if isinstance(out_route.get("from"), dict) else {}
        out_to = out_route.get("to") if isinstance(out_route.get("to"), dict) else {}
        ret_from = ret_route.get("from") if isinstance(ret_route.get("from"), dict) else {}
        ret_to = ret_route.get("to") if isinstance(ret_route.get("to"), dict) else {}
        out_sched = outbound.get("schedule") if isinstance(outbound.get("schedule"), dict) else {}
        ret_sched = ret.get("schedule") if isinstance(ret.get("schedule"), dict) else {}
        out_stops = outbound.get("stops") if isinstance(outbound.get("stops"), dict) else {}
        ret_stops = ret.get("stops") if isinstance(ret.get("stops"), dict) else {}
        low = card.get("lowest_total_price") if isinstance(card.get("lowest_total_price"), dict) else {}
        airlines = [a for a in [str(out_air.get("name") or out_air.get("code") or "").strip(), str(ret_air.get("name") or ret_air.get("code") or "").strip()] if a]
        price_total = _safe_float(low.get("total"))
        total_stop = int(card.get("__filter_stop_count__") or 0)
        duration_min = _duration_minutes_from_any(outbound.get("duration_min") or outbound.get("duration_formatted")) + _duration_minutes_from_any(ret.get("duration_min") or ret.get("duration_formatted"))
        out_cabin = str(outbound.get("travel_class") or searched_cabin or "").strip()
        ret_cabin = str(ret.get("travel_class") or searched_cabin or out_cabin or "").strip()
        option_cabin = out_cabin or ret_cabin or "Economy"
        if out_cabin and ret_cabin and out_cabin != ret_cabin:
            option_cabin = f"{out_cabin} / {ret_cabin}"
        out.append({
            "kind": "ROUND_TRIP",
            "rank": idx,
            "option_label": f"Option {idx} · {option_cabin}",
            "agent_fsr_id": card.get("agent_fsr_id"),
            "journey_key": card.get("journey_key"),
            "booked": bool(card.get("booked")),
            "booking_ref": card.get("booking_ref") or "",
            "provider_portal_url": card.get("provider_portal_url") or "",
            "price_total": price_total,
            "currency": str(low.get("currency") or "").strip(),
            "airlines": airlines,
            "stop_count": total_stop,
            "duration_min": duration_min,
            "outbound": {
                "airline_name": str(out_air.get("name") or "").strip(),
                "airline_code": str(out_air.get("code") or "").strip(),
                "city_from": str(out_from.get("city") or out_from.get("city_name") or "").strip(),
                "city_to": str(out_to.get("city") or out_to.get("city_name") or "").strip(),
                "cabin_class": out_cabin or option_cabin,
                "flight_number": str(outbound.get("flight_number") or "").strip(),
                "from_airport": str(out_from.get("airport") or "").strip(),
                "to_airport": str(out_to.get("airport") or "").strip(),
                "depart": _format_display_datetime(out_sched.get("scheduled_departure_formatted") or out_sched.get("scheduled_departure"), dt_fmt),
                "arrive": _format_display_datetime(out_sched.get("scheduled_arrival_formatted") or out_sched.get("scheduled_arrival"), dt_fmt),
                "duration": str(outbound.get("duration_formatted") or "").strip(),
                "stops_formatted": str(out_stops.get("stops_formatted") or "NON-STOP").strip(),
                "via_text": " ".join([p for p in [
                    f"Via {out_stops.get('layover1_airport_code')} layover {out_stops.get('layover1_min')} min" if out_stops.get('layover1_airport_code') else "",
                    f"Via {out_stops.get('layover2_airport_code')} layover {out_stops.get('layover2_min')} min" if out_stops.get('layover2_airport_code') else "",
                    f"Via {out_stops.get('layover3_airport_code')} layover {out_stops.get('layover3_min')} min" if out_stops.get('layover3_airport_code') else "",
                ] if p]).strip(),
            },
            "return_leg": {
                "airline_name": str(ret_air.get("name") or "").strip(),
                "airline_code": str(ret_air.get("code") or "").strip(),
                "city_from": str(ret_from.get("city") or ret_from.get("city_name") or "").strip(),
                "city_to": str(ret_to.get("city") or ret_to.get("city_name") or "").strip(),
                "cabin_class": ret_cabin or option_cabin,
                "flight_number": str(ret.get("flight_number") or "").strip(),
                "from_airport": str(ret_from.get("airport") or "").strip(),
                "to_airport": str(ret_to.get("airport") or "").strip(),
                "depart": _format_display_datetime(ret_sched.get("scheduled_departure_formatted") or ret_sched.get("scheduled_departure"), dt_fmt),
                "arrive": _format_display_datetime(ret_sched.get("scheduled_arrival_formatted") or ret_sched.get("scheduled_arrival"), dt_fmt),
                "duration": str(ret.get("duration_formatted") or "").strip(),
                "stops_formatted": str(ret_stops.get("stops_formatted") or "NON-STOP").strip(),
                "via_text": " ".join([p for p in [
                    f"Via {ret_stops.get('layover1_airport_code')} layover {ret_stops.get('layover1_min')} min" if ret_stops.get('layover1_airport_code') else "",
                    f"Via {ret_stops.get('layover2_airport_code')} layover {ret_stops.get('layover2_min')} min" if ret_stops.get('layover2_airport_code') else "",
                    f"Via {ret_stops.get('layover3_airport_code')} layover {ret_stops.get('layover3_min')} min" if ret_stops.get('layover3_airport_code') else "",
                ] if p]).strip(),
            },
            "sort_price": price_total,
            "sort_duration": duration_min,
        })
    out.sort(key=lambda x: (x.get("sort_price", 0), x.get("sort_duration", 999999), x.get("rank", 999999)))
    return out



def _summarize_one_way_rows(rows: list[dict], searched_cabin_class: str = "") -> list[dict]:
    out: list[dict] = []
    searched_cabin = str(searched_cabin_class or "").strip()
    dt_fmt = _get_app_config_value("DATETIME_DISPLAY_FORMAT", "%a %d %b %Y %H:%M")
    for idx, row in enumerate(rows or [], 1):
        values = list((row or {}).values())
        text_values = [str(v).strip() for v in values if isinstance(v, (str, int, float))]
        flight_number = next((v for v in text_values if re.match(r'^[A-Z]{2}\d{5,}$', v)), '')
        airports = [v for v in text_values if re.match(r'^[A-Z]{3}$', v)]
        option_cabin = searched_cabin or str(row.get("__travel_class__") or row.get("travel_class") or "").strip() or "Economy"
        out.append({
            "kind": "ONE_WAY",
            "rank": idx,
            "option_label": f"Option {idx} · {option_cabin}",
            "agent_fsr_id": row.get("__fsr_id__"),
            "booked": bool(row.get("__booked__")),
            "booking_ref": row.get("__booking_ref__") or "",
            "provider_portal_url": row.get("__provider_portal_url__") or "",
            "price_total": _safe_float(row.get("__price_total__")),
            "currency": str(row.get("__currency__") or "").strip(),
            "airlines": [str(row.get("__airline_name__") or "").strip()] if str(row.get("__airline_name__") or "").strip() else [],
            "stop_count": int(row.get("__stop_count__") or 0),
            "duration_min": _duration_minutes_from_any(row.get("__duration_formatted__")),
            "outbound": {
                "airline_name": str(row.get("__airline_name__") or "").strip(),
                "city_from": str(row.get("__city_from__") or row.get("from_city") or "").strip(),
                "city_to": str(row.get("__city_to__") or row.get("to_city") or "").strip(),
                "cabin_class": option_cabin,
                "flight_number": flight_number,
                "from_airport": str(row.get("__from_airport__") or (airports[0] if len(airports) > 0 else '')),
                "to_airport": str(row.get("__to_airport__") or (airports[1] if len(airports) > 1 else '')),
                "depart": _format_display_datetime(row.get("__depart__") or "", dt_fmt),
                "arrive": _format_display_datetime(row.get("__arrive__") or "", dt_fmt),
                "duration": str(row.get("__duration_formatted__") or "").strip(),
                "stops_formatted": str(row.get("__stops_formatted__") or "").strip(),
                "via_text": str(row.get("__via_text__") or "").strip(),
            },
            "sort_price": _safe_float(row.get("__price_total__")),
            "sort_duration": _duration_minutes_from_any(row.get("__duration_formatted__")),
        })
    out.sort(key=lambda x: (x.get("sort_price", 0), x.get("sort_duration", 999999), x.get("rank", 999999)))
    return out



def _llm_search_results_payload(*, request: Request, session_id: int, payload: dict, fields: list[dict], cols: list[dict], search_origin: str = "LLM_BRIDGE") -> dict:
    _apply_search_trip_type_rules(payload)
    conn = get_endpoint_connection(FLIGHT_SEARCH_ENDPOINT_ID)
    provider = _resolve_selected_provider(request)
    resp_json = call_provider_traced(
        session_id=session_id,
        base_url=conn["base_url"],
        path=conn["path"],
        http_method=conn["http_method"],
        payload=payload,
        timeout_ms=conn.get("timeout_ms"),
        request_event_type="PROVIDER_SEARCH_REQUEST",
        response_event_type="PROVIDER_SEARCH_RESPONSE",
        fail_event_type="PROVIDER_SEARCH_FAILED",
        request_message="Provider flight search request sent",
        response_message="Provider flight search response received",
        fail_message="Provider flight search failed",
        provider_details={
            "api_provider_code": conn.get("provider_code"),
            "api_provider_name": conn.get("provider_name"),
            "api_provider_type": conn.get("provider_type"),
            "llm_provider_code": (provider or {}).get("provider_code"),
            "llm_provider_name": (provider or {}).get("provider_name"),
            "endpoint_id": FLIGHT_SEARCH_ENDPOINT_ID,
            "endpoint_type": conn.get("endpoint_type"),
        },
        request_context={"flow_mode": search_origin, "search_origin": search_origin},
        response_context={"flow_mode": search_origin, "search_origin": search_origin},
    )
    trip_type = str((((payload or {}).get("search") or {}).get("trip_type") or "ONE_WAY")).strip().upper() or "ONE_WAY"
    search_batch_id = str(uuid.uuid4())
    persist_payload = dict(payload)
    persist_payload["_meta"] = {"search_batch_id": search_batch_id, "search_origin": search_origin}
    _persist_search_results(session_id=session_id, endpoint_id=FLIGHT_SEARCH_ENDPOINT_ID, request_payload=persist_payload, resp_json=resp_json)
    db_rows = _fetch_search_rows(session_id, FLIGHT_SEARCH_ENDPOINT_ID, batch_id=search_batch_id)
    if trip_type == "ROUND_TRIP":
        cards = _summarize_round_trip_cards(_build_round_trip_result_cards(db_rows), ((payload or {}).get("search") or {}).get("cabin_class") or "")
    else:
        cards = _summarize_one_way_rows(_enrich_one_way_grouped_rows_for_llm(_build_one_way_grouped_rows(db_rows, cols), db_rows), ((payload or {}).get("search") or {}).get("cabin_class") or "")
    airlines = sorted({a for c in cards for a in (c.get("airlines") or []) if a})
    prices = [_safe_float(c.get("price_total")) for c in cards if _safe_float(c.get("price_total")) > 0]
    return {
        "trip_type": trip_type,
        "result_count": len(cards),
        "results": cards,
        "filters": {
            "airlines": airlines,
            "min_price": min(prices) if prices else 0,
            "max_price": max(prices) if prices else 0,
        },
    }


@router.post("/route-to-search")
def llm_route_to_search(request: Request, payload: LLMRouteToSearchRequest):
    sess = _get_active_session_or_redirect(request)
    if not sess:
        return JSONResponse({"detail": "Active application session not found for route-to-search. Please sign in again."}, status_code=401)
    session_id = int(sess["session_id"])
    provider = _resolve_selected_provider(request)
    route_payload_dict = payload.route_payload.model_dump() if hasattr(payload.route_payload, "model_dump") else dict(payload.route_payload or {})
    _safe_audit_info(
        session_id,
        "LLM_ROUTE_TO_SEARCH_START",
        "LLM route-to-search started",
        details={
            "confirmed": payload.confirmed,
            "provider_code": (provider or {}).get("provider_code"),
            "provider_name": (provider or {}).get("provider_name"),
            "route_payload": route_payload_dict,
        },
    )
    if not payload.confirmed:
        err = ValueError("Search auto-trigger is allowed only after explicit confirmation.")
        _safe_audit_fail(
            session_id,
            "LLM_ROUTE_TO_SEARCH_FAIL",
            "LLM route-to-search rejected because confirmation was missing",
            err,
            details={"confirmed": payload.confirmed, "provider_code": (provider or {}).get("provider_code"), "provider_name": (provider or {}).get("provider_name")},
        )
        raise HTTPException(status_code=400, detail="Search auto-trigger is allowed only after explicit confirmation.")
    try:
        fields = build_search_form_fields(FLIGHT_SEARCH_ENDPOINT_ID)
        cols = build_result_grid_fields(FLIGHT_SEARCH_ENDPOINT_ID)
        search_payload, missing_required, applied_defaults = _prepare_cfg_driven_search_payload_from_route(payload.route_payload, fields)

        if missing_required:
            _safe_audit_info(
                session_id,
                "LLM_ROUTE_TO_SEARCH_NEEDS_INPUT",
                "LLM route-to-search needs one or more missing fields",
                details={
                    "confirmed": payload.confirmed,
                    "provider_code": (provider or {}).get("provider_code"),
                    "provider_name": (provider or {}).get("provider_name"),
                    "route_payload": route_payload_dict,
                    "missing_fields": missing_required,
                    "applied_defaults": applied_defaults,
                },
            )
            return JSONResponse(
                {
                    "status": "MISSING_REQUIRED_FIELDS",
                    "next_action": "ASK_MISSING_FIELDS",
                    "user_message": f"I need {'just one more detail' if len(missing_required) == 1 else 'a few more details'} before I can search flights.",
                    "missing_fields": missing_required,
                    "route_payload": route_payload_dict,
                    "applied_defaults": applied_defaults,
                }
            )

        _safe_audit_info(
            session_id,
            "LLM_SEARCH_BRIDGE_START",
            "LLM confirmed request routed to flight search",
            details={"payload": search_payload, "endpoint_id": FLIGHT_SEARCH_ENDPOINT_ID, "search_origin": "LLM_BRIDGE"},
        )
        result_bundle = _llm_search_results_payload(
            request=request,
            session_id=session_id,
            payload=search_payload,
            fields=fields,
            cols=cols,
            search_origin="LLM_BRIDGE",
        )
        _safe_audit_info(
            session_id,
            "LLM_SEARCH_BRIDGE_DONE",
            "LLM bridged flight search completed",
            details={"endpoint_id": FLIGHT_SEARCH_ENDPOINT_ID, "result_count": result_bundle.get("result_count", 0), "search_origin": "LLM_BRIDGE"},
        )
        _safe_save_llm_state(
            session_id,
            provider,
            _build_llm_persisted_state(
                status="SUCCESS",
                next_action="SHOW_RESULTS",
                missing_fields=[],
                route_payload=route_payload_dict,
                normalized_intent=(_safe_load_llm_state(session_id) or {}).get("normalized_intent") or {},
                llm_intent=(_safe_load_llm_state(session_id) or {}).get("llm_intent") or {},
            ),
            None,
        )
        response = JSONResponse({
            "status": "SEARCH_RESULTS",
            "next_action": "SHOW_RESULTS",
            "user_message": f"I found {result_bundle.get('result_count', 0)} flights for your trip. Showing the best available options based on your search.",
            "route_payload": route_payload_dict,
            "search_payload": search_payload,
            "trip_type": result_bundle.get("trip_type"),
            "result_count": result_bundle.get("result_count", 0),
            "results": result_bundle.get("results", []),
            "filters": result_bundle.get("filters", {}),
        })
        return _apply_provider_cookie(response, provider)
    except HTTPException as exc:
        _safe_audit_fail(
            session_id,
            "LLM_ROUTE_TO_SEARCH_FAIL",
            "LLM route-to-search failed with HTTP exception",
            exc,
            details={
                "confirmed": payload.confirmed,
                "provider_code": (provider or {}).get("provider_code"),
                "provider_name": (provider or {}).get("provider_name"),
                "route_payload": route_payload_dict,
            },
        )
        raise
    except Exception as exc:
        _safe_audit_fail(
            session_id,
            "LLM_ROUTE_TO_SEARCH_FAIL",
            "LLM route-to-search failed",
            exc,
            details={
                "confirmed": payload.confirmed,
                "provider_code": (provider or {}).get("provider_code"),
                "provider_name": (provider or {}).get("provider_name"),
                "route_payload": route_payload_dict,
            },
        )
        raise HTTPException(status_code=400, detail=f"LLM route-to-search failed: {str(exc)}")


def _parse_json_dict(value) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            data = json.loads(value) if value else {}
        except Exception:
            data = {}
        return data if isinstance(data, dict) else {}
    return {}


def _enrich_one_way_grouped_rows_for_llm(grouped_rows: list[dict], db_rows: list[dict]) -> list[dict]:
    by_fsr = {}
    for db_row in db_rows or []:
        try:
            fsr_id = int(db_row.get("agent_fsr_id"))
        except Exception:
            continue
        by_fsr[fsr_id] = db_row

    out: list[dict] = []
    for row in grouped_rows or []:
        new_row = dict(row or {})
        try:
            fsr_id = int(new_row.get("__fsr_id__"))
        except Exception:
            fsr_id = None
        item = _parse_json_dict((by_fsr.get(fsr_id) or {}).get("response_json"))
        flight = item.get("flight") if isinstance(item.get("flight"), dict) else {}
        route = flight.get("route") if isinstance(flight.get("route"), dict) else {}
        frm = route.get("from") if isinstance(route.get("from"), dict) else {}
        to = route.get("to") if isinstance(route.get("to"), dict) else {}
        sched = flight.get("schedule") if isinstance(flight.get("schedule"), dict) else {}
        fare = item.get("fare") if isinstance(item.get("fare"), dict) else {}
        price = fare.get("price") if isinstance(fare.get("price"), dict) else {}

        if not new_row.get("__airline_name__"):
            airline = flight.get("airline") if isinstance(flight.get("airline"), dict) else {}
            new_row["__airline_name__"] = str(airline.get("name") or "").strip()
        if not new_row.get("__city_from__"):
            new_row["__city_from__"] = str(frm.get("city") or frm.get("city_name") or "").strip()
        if not new_row.get("__city_to__"):
            new_row["__city_to__"] = str(to.get("city") or to.get("city_name") or "").strip()
        if not new_row.get("__from_airport__"):
            new_row["__from_airport__"] = str(frm.get("airport") or "").strip()
        if not new_row.get("__to_airport__"):
            new_row["__to_airport__"] = str(to.get("airport") or "").strip()
        if not new_row.get("__depart__"):
            new_row["__depart__"] = str(sched.get("scheduled_departure_formatted") or sched.get("scheduled_departure") or "").strip()
        if not new_row.get("__arrive__"):
            new_row["__arrive__"] = str(sched.get("scheduled_arrival_formatted") or sched.get("scheduled_arrival") or "").strip()
        if not new_row.get("__currency__"):
            new_row["__currency__"] = str(price.get("currency") or "").strip()
        if (new_row.get("__price_total__") in (None, "", 0, 0.0)) and price.get("total") not in (None, ""):
            new_row["__price_total__"] = _safe_float(price.get("total"))
        if not new_row.get("__travel_class__"):
            new_row["__travel_class__"] = str(fare.get("travel_class") or flight.get("travel_class") or item.get("travel_class") or "").strip()

        out.append(new_row)
    return out



def _llm_required_pax_counts(search_request_json: dict) -> dict:
    search = search_request_json.get("search") if isinstance(search_request_json.get("search"), dict) else {}

    def _to_int(value: object) -> int:
        try:
            return max(0, int(value or 0))
        except Exception:
            return 0

    return {
        "adults": _to_int(search.get("adults")),
        "children": _to_int(search.get("children")),
        "infants": _to_int(search.get("infants")),
    }


def _llm_format_required_pax(counts: dict) -> str:
    parts: list[str] = []
    for key, label in (("adults", "Adult"), ("children", "Child"), ("infants", "Infant")):
        count = int(counts.get(key) or 0)
        if count > 0:
            parts.append(f"{count} {label}")
    return ", ".join(parts) if parts else "at least one Adult"


def _llm_validate_selected_pax_against_search(*, booking_payload: dict, search_request_json: dict) -> None:
    required = _llm_required_pax_counts(search_request_json)
    if sum(required.values()) <= 0:
        return
    booking = booking_payload.get("booking") if isinstance(booking_payload.get("booking"), dict) else {}
    actual = booking.get("pax_counts") if isinstance(booking.get("pax_counts"), dict) else {}
    actual_counts = {
        "adults": int(actual.get("adults") or 0),
        "children": int(actual.get("children") or 0),
        "infants": int(actual.get("infants") or 0),
    }
    if actual_counts != required:
        raise ValueError(f"Selected travellers do not match the booking requirement. Please select {_llm_format_required_pax(required)}.")


def _llm_resolve_selected_fare_option(*, selected_item_json: dict, confirm_model: dict, selection: dict | None) -> dict:
    selection = selection if isinstance(selection, dict) else {}
    trip_type = _normalize_trip_type_value(confirm_model.get("trip_type"))
    selected_option = {}
    if trip_type == "ROUND_TRIP":
        selected_option = _find_fare_option_by_ids(
            selected_item_json,
            selection.get("outbound_fare_id"),
            selection.get("return_fare_id"),
        )
    else:
        selected_option = _find_fare_option_by_key(selected_item_json, str(selection.get("fare_combo_key") or ""))
    if not selected_option:
        selected_fare = confirm_model.get("selected_fare") if isinstance(confirm_model.get("selected_fare"), dict) else {}
        selected_option = _find_fare_option_by_key(selected_item_json, str(selected_fare.get("fare_combo_key") or ""))
        if not selected_option and trip_type == "ROUND_TRIP":
            selected_option = _find_fare_option_by_ids(
                selected_item_json,
                selected_fare.get("outbound_fare_id"),
                selected_fare.get("return_fare_id"),
            )
    return selected_option or {}


def _llm_apply_selected_fare_to_booking(*, booking: dict, selected_fare_option: dict) -> None:
    sel = selected_fare_option.get("selection") if isinstance(selected_fare_option.get("selection"), dict) else {}
    if sel.get("outbound_flight_id"):
        booking["flight_id"] = int(sel.get("outbound_flight_id"))
    if sel.get("outbound_fare_id"):
        booking["fare_id"] = int(sel.get("outbound_fare_id"))
    if sel.get("return_flight_id"):
        booking["return_flight_id"] = int(sel.get("return_flight_id"))
    if sel.get("return_fare_id"):
        booking["return_fare_id"] = int(sel.get("return_fare_id"))
    if selected_fare_option.get("fare_combo_key"):
        booking["fare_combo_key"] = str(selected_fare_option.get("fare_combo_key"))
    total_price = selected_fare_option.get("total_price") if isinstance(selected_fare_option.get("total_price"), dict) else {}
    if total_price.get("total") not in (None, ""):
        booking["selected_total_amount"] = float(total_price.get("total"))
    if total_price.get("currency") not in (None, ""):
        booking["selected_currency"] = str(total_price.get("currency"))


def _llm_format_money(amount: object, currency: str | None = None) -> str:
    try:
        num = float(amount or 0)
        if abs(num - int(num)) < 0.00001:
            value = f"{int(num):,}"
        else:
            value = f"{num:,.2f}"
    except Exception:
        value = str(amount or "-")
    c = str(currency or "").strip()
    return f"{c} {value}".strip()


def _llm_to_float(value: object) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _llm_build_booking_payload(*, agent_fsr_id: int, user_id: int, selected_document_ids: list[int], selection: dict | None) -> tuple[dict, dict, dict, dict]:
    selected_item_json = _load_selected_item_json(agent_fsr_id)
    if not selected_item_json:
        raise ValueError("Selected journey was not found.")
    search_request_json = _load_selected_search_request_json(agent_fsr_id)
    confirm_model = _normalize_confirm_model(selected_item_json, search_request_json)
    selected_fare_option = _llm_resolve_selected_fare_option(selected_item_json=selected_item_json, confirm_model=confirm_model, selection=selection)
    booking_payload = {"booking": {"agent_fsr_id": agent_fsr_id, "trip_type": _normalize_trip_type_value(confirm_model.get("trip_type"))}}
    if selected_fare_option:
        _llm_apply_selected_fare_to_booking(booking=booking_payload["booking"], selected_fare_option=selected_fare_option)
    _normalize_payload_for_provider(booking_payload, user_id=user_id, selected_document_ids=selected_document_ids)
    validation_error = _validate_booking_payload(booking_payload, selected_item_json=selected_item_json)
    if validation_error:
        raise ValueError(validation_error)
    return booking_payload, selected_item_json, search_request_json, confirm_model


def _llm_booking_preview_response(*, booking_payload: dict, confirm_model: dict, selected_document_ids: list[int], user_id: int, agent_fsr_id: int) -> dict:
    active_map = {int(r.get("document_id") or 0): r for r in (_get_active_traveler_rows(user_id) or [])}
    selected_travelers = []
    for doc_id in selected_document_ids or []:
        row = active_map.get(int(doc_id or 0))
        if row:
            selected_travelers.append({"document_id": int(row.get("document_id") or 0), "label": _llm_build_traveler_label(row), "traveler_type": str(row.get("traveler_type") or "").strip().title()})
    selected_fare = confirm_model.get("selected_fare") if isinstance(confirm_model.get("selected_fare"), dict) else {}
    booking_block = booking_payload.get("booking") if isinstance(booking_payload.get("booking"), dict) else {}
    pax_count = len(booking_block.get("passengers") or []) or len(selected_document_ids or []) or 1
    base_total = _llm_to_float(
        selected_fare.get("total_amount")
        or selected_fare.get("amount")
        or booking_block.get("selected_total_amount")
        or 0
    )
    preview_total = base_total * pax_count
    currency = str(selected_fare.get("currency") or booking_block.get("selected_currency") or booking_block.get("currency") or "").strip().upper()
    return {
        "status": "BOOKING_PREVIEW",
        "next_action": "CONFIRM_BOOKING",
        "user_message": "Please review your journey details before confirming your booking.",
        "agent_fsr_id": agent_fsr_id,
        "confirm_model": confirm_model,
        "selected_fare": selected_fare,
        "selected_travelers": selected_travelers,
        "selected_document_ids": selected_document_ids or [],
        "total_amount": preview_total,
        "total_display": _llm_format_money(preview_total, currency),
    }


def _llm_build_booking_summary_response(*, booking_ref: str, booking_view: dict, session_id: int | None = None) -> dict:
    confirmed = booking_view.get("confirmed_journey") if isinstance(booking_view, dict) else {}
    payment_status = str(booking_view.get("payment_status") or confirmed.get("payment_status") or "PENDING").upper()
    actual_booking_status = str(booking_view.get("booking_status") or confirmed.get("status") or "CONFIRMED").upper()
    display_booking_status = actual_booking_status
    display_user_message = "Your booking has been confirmed successfully."
    if payment_status == "PENDING":
        display_booking_status = "HELD FOR PAYMENT"
        display_user_message = "Your booking is temporarily held pending payment. Please complete payment to confirm your booking."
    trip_type = str(confirmed.get("trip_type") or "").replace("_", " ").strip().upper() or "TRIP"
    passengers = booking_view.get("passengers") if isinstance(booking_view.get("passengers"), list) else []
    segments = []
    for key, label in (("outbound", "Outbound"), ("return", "Return")):
        seg = confirmed.get(key) if isinstance(confirmed, dict) else None
        if isinstance(seg, dict):
            segments.append({
                "label": label,
                "airline": seg.get("airline_name") or "",
                "flight_number": seg.get("flight_number") or "",
                "from": seg.get("from_airport") or seg.get("from_city") or "",
                "to": seg.get("to_airport") or seg.get("to_city") or "",
                "departure": seg.get("departure_display") or seg.get("scheduled_departure_display") or seg.get("departure") or "",
                "arrival": seg.get("arrival_display") or seg.get("scheduled_arrival_display") or seg.get("arrival") or "",
            })
    return {
        "status": "BOOKING_DONE",
        "next_action": "BOOKING_DONE",
        "user_message": display_user_message,
        "booking_ref": booking_ref,
        "booking_status": display_booking_status,
        "payment_status": payment_status,
        "trip_type": trip_type,
        "traveller_count": len(passengers),
        "total_display": _llm_format_money(confirmed.get("total_amount"), confirmed.get("currency")),
        "segments": segments,
        "travelers": [{"label": (p.get("full_name") or "").strip() + (f" ({str(p.get('traveler_type') or '').title()})" if p.get('traveler_type') else "")} for p in passengers],
        "payment_url": f"/portal/flight/payment?booking_ref={booking_ref}&flow_mode=LLM&session_id={int(session_id) if session_id not in (None, '') else ''}",
        "booking_url": f"/portal/flight/booking-summary?booking_ref={booking_ref}",
        "itinerary_url": f"/portal/flight/itinerary?booking_ref={booking_ref}",
        "itinerary_download_url": f"/portal/flight/itinerary/download?booking_ref={booking_ref}",
        "provider_itinerary_url": _llm_build_provider_manage_booking_url(booking_ref),
    }


@router.post("/booking-preview")
def llm_booking_preview(request: Request, payload: LLMBookingPreviewRequest):
    sess = _get_active_session_or_redirect(request)
    if not sess:
        return JSONResponse({"detail": "Active application session not found for booking preview. Please sign in again."}, status_code=401)
    session_id = int(sess["session_id"]); user_id = int(sess["user_id"])
    try:
        booking_payload, selected_item_json, search_request_json, confirm_model = _llm_build_booking_payload(agent_fsr_id=int(payload.agent_fsr_id), user_id=user_id, selected_document_ids=payload.selected_document_ids or [], selection=payload.selection)
        conflict = _check_duplicate_booking_conflict(user_id=user_id, selected_agent_fsr_id=int(payload.agent_fsr_id), search_endpoint_id=FLIGHT_SEARCH_ENDPOINT_ID, booking_endpoint_id=2)
        if conflict:
            return JSONResponse({"status":"BOOKING_CONFLICT","next_action":"BOOKING_CONFLICT","user_message":conflict.get("message") or "You already have a confirmed booking.","manage_booking_url":f"/portal/flight/booking-summary?booking_ref={conflict.get('booking_ref') or ''}"})
        resp = _llm_booking_preview_response(booking_payload=booking_payload, confirm_model=confirm_model, selected_document_ids=payload.selected_document_ids or [], user_id=user_id, agent_fsr_id=int(payload.agent_fsr_id))
        _safe_audit_info(session_id, "LLM_BOOKING_PREVIEW_DONE", "LLM booking preview prepared", details={"agent_fsr_id": payload.agent_fsr_id})
        return JSONResponse(resp)
    except Exception as exc:
        _safe_audit_fail(session_id, "LLM_BOOKING_PREVIEW_FAIL", "LLM booking preview failed", exc, details={"agent_fsr_id": payload.agent_fsr_id})
        raise HTTPException(status_code=400, detail=f"Unable to prepare booking preview: {str(exc)}")


@router.post("/booking-confirm")
def llm_booking_confirm(request: Request, payload: LLMBookingConfirmRequest):
    sess = _get_active_session_or_redirect(request)
    if not sess:
        return JSONResponse({"detail": "Active application session not found for booking. Please sign in again."}, status_code=401)
    session_id = int(sess["session_id"]); user_id = int(sess["user_id"])
    agent_booking_id = None
    try:
        agent_fsr_id = int(payload.agent_fsr_id)
        booking_payload, selected_item_json, search_request_json, confirm_model = _llm_build_booking_payload(agent_fsr_id=agent_fsr_id, user_id=user_id, selected_document_ids=payload.selected_document_ids or [], selection=payload.selection)
        conflict = _check_duplicate_booking_conflict(user_id=user_id, selected_agent_fsr_id=agent_fsr_id, search_endpoint_id=FLIGHT_SEARCH_ENDPOINT_ID, booking_endpoint_id=2)
        if conflict:
            return JSONResponse({"status":"BOOKING_CONFLICT","next_action":"BOOKING_CONFLICT","user_message":conflict.get("message") or "You already have a confirmed booking.","manage_booking_url":f"/portal/flight/booking-summary?booking_ref={conflict.get('booking_ref') or ''}"})
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO agent_flight_booking (agent_fsr_id, endpoint_id, trip_type, booking_status, request_json) VALUES (%s, %s, %s, 'PENDING', %s)", (agent_fsr_id, 2, booking_payload['booking']['trip_type'], json.dumps(booking_payload)))
                agent_booking_id = cur.lastrowid
            conn.commit()
        conn_cfg = get_endpoint_connection(2)
        provider = _resolve_selected_provider(request)
        resp_json = call_provider_traced(session_id=session_id, base_url=conn_cfg['base_url'], path=conn_cfg['path'], http_method=conn_cfg['http_method'], payload=booking_payload, timeout_ms=conn_cfg.get('timeout_ms'), request_event_type='PROVIDER_BOOK_REQUEST', response_event_type='PROVIDER_BOOK_RESPONSE', fail_event_type='PROVIDER_BOOK_FAILED', request_message='Provider flight booking request sent', response_message='Provider flight booking response received', fail_message='Provider flight booking failed', provider_details={'api_provider_code': conn_cfg.get('provider_code'), 'api_provider_name': conn_cfg.get('provider_name'), 'api_provider_type': conn_cfg.get('provider_type'), 'llm_provider_code': (provider or {}).get('provider_code'), 'llm_provider_name': (provider or {}).get('provider_name'), 'endpoint_id': 2, 'endpoint_type': conn_cfg.get('endpoint_type')}, request_context={'flow_mode': 'LLM', 'agent_fsr_id': agent_fsr_id}, response_context={'flow_mode': 'LLM', 'agent_fsr_id': agent_fsr_id})
        booking_ref = (resp_json or {}).get('booking', {}).get('booking_ref')
        status = str((resp_json or {}).get('booking', {}).get('status', 'SUCCESS')).upper()
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE agent_flight_booking SET provider_booking_ref=%s, booking_status=%s, response_json=%s WHERE agent_booking_id=%s", (booking_ref, status, json.dumps(resp_json), agent_booking_id))
            conn.commit()
        booking_view = _get_manage_booking_by_ref(user_id=user_id, booking_ref=str(booking_ref or '').strip().upper())
        _safe_audit_info(session_id, "LLM_BOOKING_DONE", "LLM booking completed", details={"agent_fsr_id": agent_fsr_id, "booking_ref": booking_ref})
        return JSONResponse(_llm_build_booking_summary_response(booking_ref=str(booking_ref or '').strip().upper(), booking_view=booking_view or {}, session_id=session_id))
    except Exception as exc:
        status_code, body_text, provider_user_message = _extract_provider_error_message(
            exc,
            default_message="Unable to complete booking. Please retry.",
        )
        error_obj = {"error": {"status_code": status_code, "body": body_text, "message": provider_user_message, "technical_message": str(exc)}}
        if agent_booking_id:
            try:
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE agent_flight_booking SET booking_status='FAILED', response_json=%s WHERE agent_booking_id=%s",
                            (json.dumps(error_obj), agent_booking_id),
                        )
                    conn.commit()
            except Exception:
                pass
        _safe_audit_fail(
            session_id,
            "LLM_BOOKING_FAIL",
            provider_user_message,
            exc,
            details={
                "agent_fsr_id": payload.agent_fsr_id,
                "http_status": status_code,
                "provider_error": provider_user_message,
                "provider_response_body": body_text,
            },
        )
        return JSONResponse(
            {
                "status": "BOOKING_FAILED",
                "next_action": "BOOKING_FAILED",
                "user_message": provider_user_message,
            },
            status_code=status_code or 400,
        )


@router.post("/booking-status")
def llm_booking_status(request: Request, payload: LLMBookingStatusRequest):
    sess = _get_active_session_or_redirect(request)
    if not sess:
        return JSONResponse({"detail": "Active application session not found for booking status. Please sign in again."}, status_code=401)
    user_id = int(sess["user_id"]); session_id = int(sess["session_id"])
    try:
        ref = str(payload.booking_ref or '').strip().upper()
        booking_view = _get_manage_booking_by_ref(user_id=user_id, booking_ref=ref)
        if not booking_view:
            raise ValueError('Booking was not found.')
        payment_status = str(booking_view.get('payment_status') or '').upper()
        if payment_status in {'PAID', 'SUCCESS'}:
            data = _llm_build_booking_summary_response(booking_ref=ref, booking_view=booking_view, session_id=session_id)
            data['status'] = 'PAYMENT_DONE'; data['next_action'] = 'PAYMENT_DONE'; data['user_message'] = 'Payment completed successfully. Your itinerary is now available.'
            _safe_audit_info(session_id, 'LLM_BOOKING_STATUS_DONE', 'LLM booking status loaded', details={'booking_ref': ref, 'payment_status': payment_status})
            return JSONResponse(data)
        return JSONResponse({'status':'PAYMENT_PENDING','next_action':'PAYMENT_PENDING','user_message':'Your booking is temporarily held pending payment. Please complete payment to confirm your booking.','booking_ref':ref})
    except Exception as exc:
        _safe_audit_fail(session_id, 'LLM_BOOKING_STATUS_FAIL', 'LLM booking status failed', exc, details={'booking_ref': payload.booking_ref})
        raise HTTPException(status_code=400, detail=f'Unable to load booking status: {str(exc)}')


def _llm_build_traveler_label(row: dict) -> str:
    first_name = str(row.get("first_name") or "").strip()
    last_name = str(row.get("last_name") or "").strip()
    full_name = " ".join([x for x in [first_name, last_name] if x]).strip() or f"Traveller {row.get('document_id')}"
    traveler_type = str(row.get("traveler_type") or "Traveller").strip().title()
    return f"{full_name} ({traveler_type})"


@router.post("/fare-options")
def llm_fare_options(request: Request, payload: LLMFareOptionsRequest):
    sess = _get_active_session_or_redirect(request)
    if not sess:
        return JSONResponse({"detail": "Active application session not found for fare-options. Please sign in again."}, status_code=401)
    session_id = int(sess["session_id"])
    try:
        agent_fsr_id = int(payload.agent_fsr_id)
        selected_item_json = _load_selected_item_json(agent_fsr_id)
        if not selected_item_json:
            raise HTTPException(status_code=404, detail="Selected journey was not found.")
        search_request_json = _load_selected_search_request_json(agent_fsr_id)
        confirm_model = _normalize_confirm_model(selected_item_json, search_request_json)
        selected_fare = confirm_model.get("selected_fare") if isinstance(confirm_model.get("selected_fare"), dict) else {}
        selection = selected_fare.get("selection") if isinstance(selected_fare.get("selection"), dict) else {}
        selected_option = _find_fare_option_by_key(selected_item_json, str(selected_fare.get("fare_combo_key") or ""))
        if not selected_option and confirm_model.get("trip_type") == "ROUND_TRIP":
            selected_option = _find_fare_option_by_ids(selected_item_json, selection.get("outbound_fare_id"), selection.get("return_fare_id"))
        response = {
            "status": "FARE_OPTIONS",
            "next_action": "SHOW_FARE_OPTIONS",
            "user_message": "Please choose the fare option that suits your trip.",
            "agent_fsr_id": agent_fsr_id,
            "selected_result": payload.selected_result or {},
            "confirm_model": confirm_model,
            "fare_options": selected_item_json.get("fare_options") if isinstance(selected_item_json.get("fare_options"), list) else [],
            "selected_fare_option": selected_option or {},
        }
        _safe_audit_info(session_id, "LLM_FARE_OPTIONS_DONE", "LLM fare options prepared", details={"agent_fsr_id": agent_fsr_id, "trip_type": confirm_model.get("trip_type")})
        return JSONResponse(response)
    except HTTPException:
        raise
    except Exception as exc:
        _safe_audit_fail(session_id, "LLM_FARE_OPTIONS_FAIL", "LLM fare options failed", exc, details={"agent_fsr_id": payload.agent_fsr_id})
        raise HTTPException(status_code=400, detail=f"Unable to prepare fare options: {str(exc)}")


@router.post("/travelers")
def llm_travelers(request: Request, payload: LLMTravelersRequest):
    sess = _get_active_session_or_redirect(request)
    if not sess:
        return JSONResponse({"detail": "Active application session not found for travellers. Please sign in again."}, status_code=401)
    session_id = int(sess["session_id"])
    user_id = int(sess["user_id"])
    try:
        agent_fsr_id = int(payload.agent_fsr_id)
        rows = _get_active_traveler_rows(user_id)
        travelers = []
        for row in rows or []:
            travelers.append({
                "document_id": int(row.get("document_id") or 0),
                "label": _llm_build_traveler_label(row),
                "traveler_type": str(row.get("traveler_type") or "").strip().title(),
                "is_primary": int(row.get("is_primary") or 0) == 1,
            })
        _safe_audit_info(session_id, "LLM_TRAVELERS_DONE", "LLM travellers prepared", details={"agent_fsr_id": agent_fsr_id, "traveler_count": len(travelers)})
        return JSONResponse({
            "status": "TRAVELERS",
            "next_action": "SHOW_TRAVELERS",
            "user_message": "Select Travellers",
            "agent_fsr_id": agent_fsr_id,
            "travelers": travelers,
            "manage_url": f"/travelers?agent_fsr_id={agent_fsr_id}",
        })
    except Exception as exc:
        _safe_audit_fail(session_id, "LLM_TRAVELERS_FAIL", "LLM travellers failed", exc, details={"agent_fsr_id": payload.agent_fsr_id})
        raise HTTPException(status_code=400, detail=f"Unable to load travellers: {str(exc)}")


@router.post("/traveler-selection")
def llm_traveler_selection(request: Request, payload: LLMTravelerSelectionRequest):
    sess = _get_active_session_or_redirect(request)
    if not sess:
        return JSONResponse({"detail": "Active application session not found for traveller selection. Please sign in again."}, status_code=401)
    session_id = int(sess["session_id"])
    user_id = int(sess["user_id"])
    try:
        agent_fsr_id = int(payload.agent_fsr_id)
        selected_item_json = _load_selected_item_json(agent_fsr_id)
        if not selected_item_json:
            raise ValueError("Selected journey was not found.")
        search_request_json = _load_selected_search_request_json(agent_fsr_id)
        confirm_model = _normalize_confirm_model(selected_item_json, search_request_json)
        selected_fare_option = _llm_resolve_selected_fare_option(selected_item_json=selected_item_json, confirm_model=confirm_model, selection=payload.selection)

        booking_payload = {
            "booking": {
                "agent_fsr_id": agent_fsr_id,
                "trip_type": _normalize_trip_type_value(confirm_model.get("trip_type")),
            }
        }
        if selected_fare_option:
            _llm_apply_selected_fare_to_booking(booking=booking_payload["booking"], selected_fare_option=selected_fare_option)

        _normalize_payload_for_provider(booking_payload, user_id=user_id, selected_document_ids=payload.selected_document_ids)
        if payload.allow_mismatch_override:
            actual_counts = (booking_payload.get("booking") or {}).get("pax_counts") if isinstance((booking_payload.get("booking") or {}).get("pax_counts"), dict) else {}
            has_any_selected = any(int(actual_counts.get(k) or 0) > 0 for k in ("adults", "children", "infants"))
            if not has_any_selected or int(actual_counts.get("adults") or 0) <= 0:
                raise ValueError("At least one ADULT traveller must be selected for booking.")
        else:
            _llm_validate_selected_pax_against_search(booking_payload=booking_payload, search_request_json=search_request_json)
        validation_error = _validate_booking_payload(booking_payload, selected_item_json=selected_item_json)
        if validation_error:
            raise ValueError(validation_error)

        active_map = {int(r.get("document_id") or 0): r for r in (_get_active_traveler_rows(user_id) or [])}
        selected_travelers = []
        for doc_id in payload.selected_document_ids or []:
            row = active_map.get(int(doc_id or 0))
            if row:
                selected_travelers.append({
                    "document_id": int(row.get("document_id") or 0),
                    "label": _llm_build_traveler_label(row),
                    "traveler_type": str(row.get("traveler_type") or "").strip().title(),
                })

        _safe_audit_info(session_id, "LLM_TRAVELER_SELECTION_DONE", "LLM traveller selection validated", details={"agent_fsr_id": agent_fsr_id, "selected_document_ids": payload.selected_document_ids or []})
        return JSONResponse({
            "status": "TRAVELERS_CONFIRMED",
            "next_action": "TRAVELERS_CONFIRMED",
            "user_message": "Traveller details have been saved successfully.",
            "agent_fsr_id": agent_fsr_id,
            "selected_document_ids": payload.selected_document_ids or [],
            "selected_travelers": selected_travelers,
            "booking_payload": booking_payload,
        })
    except Exception as exc:
        _safe_audit_fail(session_id, "LLM_TRAVELER_SELECTION_FAIL", "LLM traveller selection failed", exc, details={"agent_fsr_id": payload.agent_fsr_id, "selected_document_ids": payload.selected_document_ids or []})
        raise HTTPException(status_code=400, detail=f"Unable to validate traveller selection: {str(exc)}")

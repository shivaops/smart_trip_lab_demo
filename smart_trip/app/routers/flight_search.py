# app/routers/flight_search.py
"""Flight Search: DB-driven search form, results page, and booking confirm page.

LOCKED RULES
- UI field names MUST be cfg-based only: name="cfg_{cfg_id}"
- No hardcoded request keys: payload built using cfg.request_json_path
- No hardcoded result columns: grid built using cfg.response_json_path
- No fallback: cfg mistakes must raise (fail fast)   
 
Flow
STEP-1: GET  /portal/flight/search
STEP-2: POST /portal/flight/search -> call provider, persist results into agent_flight_search_result
STEP-3: GET  /portal/flight/confirm?agent_fsr_id=...
STEP-4: POST /portal/flight/confirm -> call provider BOOK, persist agent_flight_booking
"""



from __future__ import annotations
import requests
import uuid
import json
import datetime
import re
from urllib.parse import quote
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
except Exception:  # pragma: no cover
    colors = A4 = ParagraphStyle = getSampleStyleSheet = Paragraph = SimpleDocTemplate = Spacer = Table = TableStyle = None

from core.audit import log_fail, log_info
from core.auth_context import get_current_user, get_session_uuid_from_request
from core.json_path import json_get, json_set
from core.provider_client import call_provider
from db.session import get_conn
from repo.cfg_repo import build_result_grid_fields, build_search_form_fields
from repo.endpoint_repo import get_endpoint_connection
from repo.session_repo import get_active_session_by_uuid
from repo.travelers_repo import get_primary_active_traveler, list_travelers
from repo.audit_repo import fetch_audit_events, list_audit_event_types


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Endpoint ID for ARS_LOCAL FLIGHT_SEARCH
FLIGHT_SEARCH_ENDPOINT_ID = 1


def _parse_iso_date(value: Any):
    s = str(value or '').strip()
    if not s:
        return None
    for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except Exception:
            pass
    try:
        return datetime.date.fromisoformat(s[:10])
    except Exception:
        return None


def _full_years_between(dob: datetime.date, ref: datetime.date) -> int:
    years = ref.year - dob.year
    if (ref.month, ref.day) < (dob.month, dob.day):
        years -= 1
    return years




def _extract_provider_error_message(err: Exception, *, default_message: str = "Provider booking failed. Please retry.") -> tuple[int | None, str | None, str]:
    """Return (http_status, raw_body, clean_user_message) from provider HTTP errors."""
    status_code = None
    body_text = None
    clean_message = default_message

    response = getattr(err, "response", None)
    if response is not None:
        status_code = getattr(response, "status_code", None)
        body_text = (getattr(response, "text", None) or "").strip()
        try:
            body_json = response.json()
        except Exception:
            body_json = None

        if isinstance(body_json, dict):
            detail = body_json.get("detail") or body_json.get("message") or body_json.get("error")
            if isinstance(detail, str) and detail.strip():
                clean_message = detail.strip()
            elif detail is not None:
                clean_message = str(detail).strip()
        elif body_text:
            clean_message = body_text
    elif str(err).strip():
        clean_message = str(err).strip()

    return status_code, body_text, clean_message

def _booking_validation_error(message: str, *, selected_item_json: dict, payload: dict) -> str:
    dep = _parse_iso_date(json_get(selected_item_json, 'flight.schedule.scheduled_departure')) if selected_item_json else None
    booking = payload.get('booking') if isinstance(payload.get('booking'), dict) else {}
    pax = booking.get('pax_counts') if isinstance(booking.get('pax_counts'), dict) else {}
    return message


def _validate_booking_payload(payload: dict, *, selected_item_json: dict) -> str | None:
    booking = payload.get('booking')
    if not isinstance(booking, dict):
        return 'Booking payload is empty. Please fill the booking form again.'

    flight_id = booking.get('flight_id')
    fare_id = booking.get('fare_id')
    agent_fsr_id = booking.get('agent_fsr_id')
    if not flight_id:
        return 'Selected flight is missing. Please select the flight again.'
    if not fare_id:
        return 'Selected fare is missing. Please select the flight again.'
    if not agent_fsr_id:
        return 'Booking context is missing. Please select the flight again.'

    pax_counts = booking.get('pax_counts') if isinstance(booking.get('pax_counts'), dict) else {}
    adults = int(pax_counts.get('adults') or 0)
    children = int(pax_counts.get('children') or 0)
    infants = int(pax_counts.get('infants') or 0)
    requested_total = adults + children + infants

    passengers = booking.get('passengers')
    if not isinstance(passengers, list) or not passengers:
        return 'Passenger details are missing. Please add or activate traveller records before booking.'
    if requested_total and requested_total != len(passengers):
        return f'Passenger count mismatch. Requested {requested_total} passenger(s), but payload contains {len(passengers)} passenger row(s).'

    departure_date = _parse_iso_date(json_get(selected_item_json, 'flight.schedule.scheduled_departure')) if selected_item_json else None
    today = datetime.date.today()

    for idx, p in enumerate(passengers, start=1):
        if not isinstance(p, dict):
            return f'Passenger {idx} details are invalid.'
        first_name = str(p.get('first_name') or '').strip()
        last_name = str(p.get('last_name') or '').strip()
        gender = str(p.get('gender') or '').strip()
        nationality = str(p.get('nationality_iso2') or '').strip().upper()
        traveler_type = str(p.get('traveler_type') or '').strip().title()
        dob = _parse_iso_date(p.get('date_of_birth'))
        if not first_name:
            return f'Passenger {idx}: First Name is required.'
        if not last_name:
            return f'Passenger {idx}: Last Name is required.'
        if not dob:
            return f'Passenger {idx}: Date of Birth is missing or invalid.'
        if dob > today:
            return f'Passenger {idx}: Date of Birth cannot be in the future.'
        if gender not in ('Male', 'Female', 'Other'):
            return f'Passenger {idx}: Gender must be Male, Female, or Other.'
        if len(nationality) != 2 or not nationality.isalpha():
            return f'Passenger {idx}: Nationality must be 2 letters (example: IN).'

        age_ref = departure_date or today
        age = _full_years_between(dob, age_ref)
        if traveler_type == 'Infant' and age >= 2:
            return f'Passenger {idx}: Infant age must be below 2 years on travel date.'
        if traveler_type == 'Child' and (age < 2 or age >= 12):
            return f'Passenger {idx}: Child age must be between 2 and 11 years on travel date.'
        if traveler_type == 'Adult' and age < 12:
            return f'Passenger {idx}: Adult age must be 12 years or above on travel date.'

        if idx == 1:
            email = str(p.get('email') or '').strip()
            phone = str(p.get('phone') or '').strip()
            if not email:
                return 'Lead passenger email is required.'
            if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
                return 'Lead passenger email format is invalid.'
            if not phone:
                return 'Lead passenger phone is required.'
            if not re.fullmatch(r'\+?[0-9]{6,20}', phone):
                return 'Lead passenger phone format is invalid. Use digits only with optional leading + and length between 6 and 20.'

        td = p.get('travel_document') if isinstance(p.get('travel_document'), dict) else {}
        doc_type = str(td.get('document_type') or '').strip()
        doc_number = str(td.get('document_number') or '').strip()
        issuing = str(td.get('issuing_country_iso2') or '').strip().upper()
        expiry = _parse_iso_date(td.get('expiry_date'))
        issue = _parse_iso_date(td.get('issue_date'))
        if not doc_type:
            return f'Passenger {idx}: Document Type is required.'
        if not doc_number:
            return f'Passenger {idx}: Document Number is required.'
        if len(issuing) != 2 or not issuing.isalpha():
            return f'Passenger {idx}: Issuing Country must be 2 letters (example: IN).'
        if not expiry:
            return f'Passenger {idx}: Document Expiry Date is missing or invalid.'
        if issue and issue > today:
            return f'Passenger {idx}: Document Issue Date cannot be in the future.'
        if issue and issue > expiry:
            return f'Passenger {idx}: Document Issue Date cannot be later than Expiry Date.'
        if departure_date and expiry < departure_date:
            return f'Passenger {idx}: Travel document expires before travel date.'
        if expiry <= today:
            return f'Passenger {idx}: Travel document is already expired or expires today.'

    return None


def _extract_from_item(item: dict, path: str):
    p = (path or "").strip()
    if not p:
        raise ValueError("Missing response_json_path in cfg")

    if p.startswith("results[]."):
        p = p[len("results[]."):]

    if p.startswith("meta."):
        raise ValueError(f"meta.* path not supported for per-row extraction: {path}")

    if p.startswith("results["):
        raise ValueError(f"results[index] path not supported for per-row extraction: {path}")

    return json_get(item, p)


def _mask_for_trace(req_path: str, value: Any) -> Any:
    p = (req_path or "").lower()
    if value in (None, ""):
        return value

    if any(k in p for k in ("flight_id", "fare_id", "agent_", "session_id", "agent_fsr_id")):
        return value

    if any(k in p for k in ("email", "phone", "mobile", "document", "passport", "doc_number", "number")):
        s = str(value)
        if len(s) <= 4:
            return "****"
        return s[:2] + "*" * (len(s) - 4) + s[-2:]

    return value


def _get_app_config_int(config_key: str, default: int) -> int:
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT config_value FROM app_config WHERE config_key=%s",
                    (config_key,),
                )
                row = cur.fetchone()
        if not row:
            return default
        v = row.get("config_value") if isinstance(row, dict) else row[0]
        return int(str(v).strip())
    except Exception:
        return default


def _get_selected_flight_meta(*, agent_fsr_id: int, user_id: int, endpoint_id: int) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.flight_number, r.scheduled_departure
                FROM agent_flight_search_result r
                JOIN chat_session s
                  ON s.session_id = r.session_id
                WHERE r.agent_fsr_id = %s
                  AND s.user_id = %s
                  AND r.endpoint_id = %s
                """,
                (agent_fsr_id, user_id, endpoint_id),
            )
            row = cur.fetchone()
    if not row:
        return {}
    return {
        "flight_number": row.get("flight_number") if isinstance(row, dict) else row[0],
        "scheduled_departure": row.get("scheduled_departure") if isinstance(row, dict) else row[1],
    }


def _check_duplicate_booking_conflict(
    *,
    user_id: int,
    selected_agent_fsr_id: int,
    search_endpoint_id: int,
    booking_endpoint_id: int,
) -> Optional[dict]:
    window_hours = _get_app_config_int("DUP_BOOKING_WINDOW", 12)

    meta = _get_selected_flight_meta(
        agent_fsr_id=selected_agent_fsr_id,
        user_id=user_id,
        endpoint_id=search_endpoint_id,
    )
    if not meta or not meta.get("scheduled_departure"):
        return None

    flight_number = str(meta.get("flight_number") or "").strip()
    dep_dt = meta["scheduled_departure"]

    if flight_number:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT b.provider_booking_ref, r.flight_number, r.scheduled_departure
                    FROM agent_flight_booking b
                    JOIN agent_flight_search_result r
                      ON r.agent_fsr_id = b.agent_fsr_id
                    JOIN chat_session s
                      ON s.session_id = r.session_id
                    WHERE s.user_id = %s
                      AND r.endpoint_id = %s
                      AND b.endpoint_id = %s
                      AND b.booking_status = 'CONFIRMED'
                      AND r.flight_number = %s
                      AND DATE(r.scheduled_departure) = DATE(%s)
                    ORDER BY b.agent_booking_id DESC
                    LIMIT 1
                    """,
                    (user_id, search_endpoint_id, booking_endpoint_id, flight_number, dep_dt,),
                )
                row = cur.fetchone()

        if row:
            ref = row.get("provider_booking_ref") if isinstance(row, dict) else row[0]
            date_str = str(dep_dt)[:10]
            return {
                "title": "Booking not allowed",
                "booking_ref": ref,
                "message": (
                    f"You already have a confirmed booking for flight {flight_number} on {date_str}. "
                    f"Please open Manage Booking to review your existing reservation (Ref: {ref})."
                ),
            }

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT b.provider_booking_ref, r.flight_number, r.scheduled_departure
                FROM agent_flight_booking b
                JOIN agent_flight_search_result r
                  ON r.agent_fsr_id = b.agent_fsr_id
                JOIN chat_session s
                  ON s.session_id = r.session_id
                WHERE s.user_id = %s
                  AND r.endpoint_id = %s
                  AND b.endpoint_id = %s
                  AND b.booking_status = 'CONFIRMED'
                  AND ABS(TIMESTAMPDIFF(HOUR, r.scheduled_departure, %s)) <= %s
                ORDER BY r.scheduled_departure
                LIMIT 1
                """,
                (user_id, search_endpoint_id, booking_endpoint_id, dep_dt, window_hours),
            )
            row = cur.fetchone()

    if row:
        ref = row.get("provider_booking_ref") if isinstance(row, dict) else row[0]
        ex_fno = row.get("flight_number") if isinstance(row, dict) else row[1]
        ex_dt = row.get("scheduled_departure") if isinstance(row, dict) else row[2]
        return {
            "title": "Booking not allowed",
            "booking_ref": ref,
            "message": (
                f"You already have a confirmed booking scheduled around this time "
                f"({ex_fno} departing {ex_dt}). "
                f"To avoid duplicate travel, another booking within ±{window_hours} hours is not permitted. "
                f"Please open Manage Booking to review your existing reservation (Ref: {ref})."
            ),
        }

    return None


def _persist_search_results(*, session_id: int, endpoint_id: int, request_payload: dict, resp_json: dict) -> int:
    search = request_payload.get("search") if isinstance(request_payload.get("search"), dict) else {}
    trip_type = _normalize_trip_type_value(search.get("trip_type"))
    results = resp_json.get("results") or []
    journeys = resp_json.get("journeys") or []
    req_s = json.dumps(request_payload, ensure_ascii=False)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE b
                FROM agent_flight_booking b
                JOIN agent_flight_search_result r
                  ON r.agent_fsr_id = b.agent_fsr_id
                JOIN chat_session s
                  ON s.session_id = r.session_id
                WHERE s.user_id = %s
                  AND r.endpoint_id = %s
                  AND b.booking_status = 'FAILED'
                """,
                (session_id, endpoint_id),
            )

            cur.execute(
                """
                DELETE r
                FROM agent_flight_search_result r
                WHERE r.session_id = %s
                  AND r.endpoint_id = %s
                  AND NOT EXISTS (
                      SELECT 1
                      FROM agent_flight_booking b2
                      WHERE b2.agent_fsr_id = r.agent_fsr_id
                  )
                """,
                (session_id, endpoint_id),
            )

            upsert_sql = """
                INSERT INTO agent_flight_search_result
                    (session_id, endpoint_id, selected_flag,
                     flight_id, flight_number, scheduled_departure, fare_id,
                     request_json, response_json, created_at)
                VALUES
                    (%s, %s, 0,
                     %s, %s, %s, %s,
                     %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    request_json  = VALUES(request_json),
                    response_json = VALUES(response_json),
                    created_at    = NOW()
            """

            processed = 0
            if trip_type == "ROUND_TRIP":
                for journey in journeys:
                    outbound = journey.get("outbound") if isinstance(journey.get("outbound"), dict) else {}
                    schedule = outbound.get("schedule") if isinstance(outbound.get("schedule"), dict) else {}
                    fare_options = journey.get("fare_options") if isinstance(journey.get("fare_options"), list) else []
                    default_key = journey.get("default_selected_fare_combo_key")
                    default_option = None
                    if default_key:
                        for fo in fare_options:
                            if isinstance(fo, dict) and str(fo.get("fare_combo_key") or "") == str(default_key):
                                default_option = fo
                                break
                    if default_option is None and fare_options:
                        default_option = fare_options[0] if isinstance(fare_options[0], dict) else None

                    sel = default_option.get("selection") if isinstance((default_option or {}).get("selection"), dict) else {}
                    flight_id = sel.get("outbound_flight_id") or outbound.get("flight_id")
                    fare_id = sel.get("outbound_fare_id") or json_get(default_option or {}, "outbound_fare.fare_id")
                    flight_number = outbound.get("flight_number")
                    scheduled_departure = schedule.get("scheduled_departure")

                    persist_item = {
                        "trip_type": "ROUND_TRIP",
                        "journey_key": journey.get("journey_key"),
                        "outbound": journey.get("outbound") or {},
                        "return": journey.get("return") or {},
                        "fare_options": fare_options,
                        "lowest_total_price": journey.get("lowest_total_price") or {},
                        "default_selected_fare_combo_key": journey.get("default_selected_fare_combo_key"),
                        "flight": journey.get("outbound") or {},
                        "fare": (default_option or {}).get("outbound_fare") or {},
                    }
                    item_s = json.dumps(persist_item, ensure_ascii=False)

                    cur.execute(
                        upsert_sql,
                        (
                            session_id,
                            endpoint_id,
                            flight_id,
                            flight_number,
                            scheduled_departure,
                            fare_id,
                            req_s,
                            item_s,
                        ),
                    )
                    processed += 1
            else:
                for item in results:
                    rk = item.get("row_key") or {}
                    flight_id = rk.get("flight_id")
                    flight_number = rk.get("flight_number")
                    scheduled_departure = rk.get("scheduled_departure")
                    fare_id = rk.get("fare_id")

                    item_s = json.dumps(item, ensure_ascii=False)

                    cur.execute(
                        upsert_sql,
                        (
                            session_id,
                            endpoint_id,
                            flight_id,
                            flight_number,
                            scheduled_departure,
                            fare_id,
                            req_s,
                            item_s,
                        ),
                    )
                    processed += 1

        conn.commit()

    return processed


def _fetch_search_rows(session_id: int, endpoint_id: int, batch_id: str | None = None):
    sql = """
    SELECT
    r.agent_fsr_id,
    r.selected_flag,
    r.request_json,
    r.response_json,
    (
      SELECT b.booking_status
      FROM agent_flight_booking b
      JOIN agent_flight_search_result rb
        ON rb.agent_fsr_id = b.agent_fsr_id
      JOIN chat_session sb
        ON sb.session_id = rb.session_id
      WHERE sb.user_id = s.user_id
        AND rb.endpoint_id = r.endpoint_id
        AND b.booking_status = 'CONFIRMED'
        AND (
              (r.flight_id IS NOT NULL AND rb.flight_id = r.flight_id AND rb.scheduled_departure = r.scheduled_departure)
           OR ((r.flight_id IS NULL OR rb.flight_id IS NULL) AND rb.flight_number = r.flight_number AND rb.scheduled_departure = r.scheduled_departure)
        )
      ORDER BY b.agent_booking_id DESC
      LIMIT 1
    ) AS latest_booking_status,
    (
      SELECT b.provider_booking_ref
      FROM agent_flight_booking b
      JOIN agent_flight_search_result rb
        ON rb.agent_fsr_id = b.agent_fsr_id
      JOIN chat_session sb
        ON sb.session_id = rb.session_id
      WHERE sb.user_id = s.user_id
        AND rb.endpoint_id = r.endpoint_id
        AND b.booking_status = 'CONFIRMED'
        AND (
              (r.flight_id IS NOT NULL AND rb.flight_id = r.flight_id AND rb.scheduled_departure = r.scheduled_departure)
           OR ((r.flight_id IS NULL OR rb.flight_id IS NULL) AND rb.flight_number = r.flight_number AND rb.scheduled_departure = r.scheduled_departure)
        )
      ORDER BY b.agent_booking_id DESC
      LIMIT 1
    ) AS latest_booking_ref
    FROM agent_flight_search_result r
    JOIN chat_session s
      ON s.session_id = r.session_id
    WHERE r.session_id = %s
      AND r.endpoint_id = %s
      AND (
            %s IS NULL
         OR JSON_UNQUOTE(JSON_EXTRACT(r.request_json, '$._meta.search_batch_id')) = %s
      )
    ORDER BY r.agent_fsr_id ASC
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (session_id, endpoint_id, batch_id, batch_id))
            return list(cur.fetchall() or [])


def _build_round_trip_result_cards(db_rows: list[dict]) -> list[dict]:
    cards: list[dict] = []
    for r in db_rows:
        item = r.get("response_json")
        if isinstance(item, str):
            try:
                item = json.loads(item) if item else {}
            except Exception:
                item = {}
        elif item is None:
            item = {}

        if not isinstance(item, dict):
            continue

        journey_key = str(item.get("journey_key") or "")
        outbound = item.get("outbound") if isinstance(item.get("outbound"), dict) else {}
        return_leg = item.get("return") if isinstance(item.get("return"), dict) else {}
        fare_options = item.get("fare_options") if isinstance(item.get("fare_options"), list) else []

        out_air = outbound.get("airline") if isinstance(outbound.get("airline"), dict) else {}
        ret_air = return_leg.get("airline") if isinstance(return_leg.get("airline"), dict) else {}
        out_stops = outbound.get("stops") if isinstance(outbound.get("stops"), dict) else {}
        ret_stops = return_leg.get("stops") if isinstance(return_leg.get("stops"), dict) else {}
        low_price = item.get("lowest_total_price") or {}

        cards.append({
            "agent_fsr_id": int(r["agent_fsr_id"]),
            "journey_key": journey_key,
            "outbound": outbound,
            "return": return_leg,
            "fare_options": fare_options,
            "lowest_total_price": low_price,
            "default_selected_fare_combo_key": item.get("default_selected_fare_combo_key"),
            "booked": (str(r.get("latest_booking_status") or "").upper() == "CONFIRMED"),
            "booking_ref": (r.get("latest_booking_ref") or ""),
            "provider_portal_url": _build_provider_portal_url(r.get("latest_booking_ref") or ""),
            "__filter_out_stop_count__": int(out_stops.get("no_of_stop") or 0),
            "__filter_ret_stop_count__": int(ret_stops.get("no_of_stop") or 0),
            "__filter_stop_count__": int(out_stops.get("no_of_stop") or 0) + int(ret_stops.get("no_of_stop") or 0),
            "__filter_airlines__": [
                str(out_air.get("name") or "").strip(),
                str(ret_air.get("name") or "").strip(),
            ],
            "__filter_price__": _flt(low_price.get("total")),
        })

    cards.sort(key=lambda c: (
        float(((c.get("lowest_total_price") or {}).get("total") or 0.0)),
        str((((c.get("outbound") or {}).get("schedule") or {}).get("scheduled_departure") or "")),
        str((((c.get("return") or {}).get("schedule") or {}).get("scheduled_departure") or "")),
        str(c.get("journey_key") or ""),
    ))
    return cards


def _one_way_group_key(item: dict) -> str:
    flight = item.get("flight") if isinstance(item.get("flight"), dict) else {}
    route = flight.get("route") if isinstance(flight.get("route"), dict) else {}
    frm = route.get("from") if isinstance(route.get("from"), dict) else {}
    to = route.get("to") if isinstance(route.get("to"), dict) else {}
    sched = flight.get("schedule") if isinstance(flight.get("schedule"), dict) else {}
    flight_id = flight.get("flight_id")
    if flight_id not in (None, ""):
        return f"FID:{flight_id}"
    return "|".join([
        str(flight.get("flight_number") or ""),
        str(frm.get("airport") or ""),
        str(to.get("airport") or ""),
        str(sched.get("scheduled_departure") or sched.get("scheduled_departure_formatted") or ""),
    ])


def _build_one_way_grouped_rows(db_rows: list[dict], cols: list[dict]) -> list[dict]:
    groups: dict[str, dict] = {}
    for r in db_rows:
        item = r.get("response_json")
        if isinstance(item, str):
            try:
                item = json.loads(item) if item else {}
            except Exception:
                item = {}
        elif item is None:
            item = {}
        if not isinstance(item, dict):
            continue
        gkey = _one_way_group_key(item)
        flight = item.get("flight") if isinstance(item.get("flight"), dict) else {}
        stops = flight.get("stops") if isinstance(flight.get("stops"), dict) else {}
        status = str(flight.get("status") or "Scheduled")
        via_parts = []
        for idx in (1, 2, 3):
            airport = str(stops.get(f"layover{idx}_airport_code") or "").strip()
            mins = str(stops.get(f"layover{idx}_min") or "").strip()
            if airport:
                via_parts.append(f"Via {airport}" + (f" layover {mins} min" if mins else ""))
        airline = flight.get("airline") if isinstance(flight.get("airline"), dict) else {}
        price = item.get("fare", {}).get("price", {}) if isinstance(item.get("fare"), dict) else {}
        total_val = _flt(price.get("total"))
        row = {
            "__fsr_id__": int(r["agent_fsr_id"]),
            "__booked__": (str(r.get("latest_booking_status") or "").upper() == "CONFIRMED"),
            "__booking_ref__": (r.get("latest_booking_ref") or ""),
            "__provider_portal_url__": _build_provider_portal_url(r.get("latest_booking_ref") or ""),
            "__duration_formatted__": str(flight.get("duration_formatted") or ""),
            "__stops_formatted__": str(stops.get("stops_formatted") or "NON-STOP"),
            "__stop_count__": int(stops.get("no_of_stop") or 0),
            "__airline_name__": str(airline.get("name") or "").strip(),
            "__status__": status,
            "__via_text__": " • ".join(via_parts),
            "__price_total__": total_val,
        }
        for c in cols:
            pth = (c.get("response_json_path") or "").strip()
            if not pth:
                raise ValueError(f"Missing response_json_path in cfg for cfg_id={c.get('cfg_id')}")
            row[str(c["cfg_id"])] = _extract_from_item(item, pth)
        grp = groups.get(gkey)
        if grp is None:
            groups[gkey] = {
                "key": gkey,
                "rows": [row],
                "default_row": row,
                "default_total": total_val,
                "booked": row["__booked__"],
                "booking_ref": row["__booking_ref__"],
                "provider_portal_url": row["__provider_portal_url__"],
                "departure": item.get("flight", {}).get("schedule", {}).get("scheduled_departure") if isinstance(item.get("flight"), dict) else "",
            }
        else:
            grp["rows"].append(row)
            if row["__booked__"] and not grp["booked"]:
                grp["booked"] = True
                grp["booking_ref"] = row["__booking_ref__"]
                grp["provider_portal_url"] = row["__provider_portal_url__"]
            if total_val < grp["default_total"]:
                grp["default_total"] = total_val
                grp["default_row"] = row
    out = []
    for grp in groups.values():
        row = dict(grp["default_row"])
        row["__booked__"] = grp["booked"]
        row["__booking_ref__"] = grp["booking_ref"]
        row["__provider_portal_url__"] = grp["provider_portal_url"]
        out.append(row)
    out.sort(key=lambda rr: (str(rr.get("__booked__") or ""),))
    return out


def _load_selected_item_json(agent_fsr_id: int) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT agent_fsr_id, session_id, endpoint_id, request_json, response_json,
                       flight_id, scheduled_departure
                FROM agent_flight_search_result
                WHERE agent_fsr_id = %s
                """,
                (agent_fsr_id,),
            )
            r = cur.fetchone()

    if not r:
        return {}

    try:
        item = json.loads(r.get("response_json") or "{}")
    except Exception:
        item = {}

    if not isinstance(item, dict):
        return {}

    trip_type = _normalize_trip_type_value(item.get("trip_type"))
    if trip_type == "ROUND_TRIP":
        return item

    session_id = r.get("session_id")
    endpoint_id = r.get("endpoint_id")
    flight_id = r.get("flight_id")
    scheduled_departure = r.get("scheduled_departure")

    sibling_items = []
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT agent_fsr_id, response_json
                FROM agent_flight_search_result
                WHERE session_id = %s
                  AND endpoint_id = %s
                  AND flight_id = %s
                  AND scheduled_departure = %s
                ORDER BY agent_fsr_id ASC
                """,
                (session_id, endpoint_id, flight_id, scheduled_departure),
            )
            sibling_rows = list(cur.fetchall() or [])

    for s in sibling_rows:
        try:
            si = json.loads(s.get("response_json") or "{}")
        except Exception:
            si = {}
        if isinstance(si, dict):
            sibling_items.append(si)

    if not sibling_items:
        sibling_items = [item]

    fare_options = []
    default_key = ""
    lowest_total = None

    selected_flight_id = str((item.get("flight") or {}).get("flight_id") or "")
    selected_fare_id = str((item.get("fare") or {}).get("fare_id") or "")

    for si in sibling_items:
        fo = _build_single_fare_option(si)
        fare_options.append(fo)

        sel = fo.get("selection") if isinstance(fo.get("selection"), dict) else {}
        if (
            str(sel.get("outbound_flight_id") or "") == selected_flight_id
            and str(sel.get("outbound_fare_id") or "") == selected_fare_id
        ):
            default_key = str(fo.get("fare_combo_key") or "")

        total_dict = fo.get("total_price") if isinstance(fo.get("total_price"), dict) else {}
        total_val = _flt(total_dict.get("total"))
        if lowest_total is None or total_val < _flt((lowest_total or {}).get("total")):
            lowest_total = total_dict

    if not default_key and fare_options:
        default_key = str(fare_options[0].get("fare_combo_key") or "")

    grouped = dict(item)
    grouped["trip_type"] = "ONE_WAY"
    grouped["outbound"] = item.get("flight") if isinstance(item.get("flight"), dict) else {}
    grouped["return"] = {}
    grouped["fare_options"] = fare_options
    grouped["outbound_fares"] = [
        fo.get("outbound_fare") for fo in fare_options if isinstance(fo, dict)
    ]
    grouped["default_selected_fare_combo_key"] = default_key
    grouped["lowest_total_price"] = lowest_total or {}

    return grouped

def _load_selected_search_request_json(agent_fsr_id: int) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT request_json
                FROM agent_flight_search_result
                WHERE agent_fsr_id = %s
                """,
                (agent_fsr_id,),
            )
            r = cur.fetchone()
    if not r:
        return {}
    try:
        return json.loads(r.get("request_json") or "{}")
    except Exception:
        return {}


def _normalize_trip_type_value(value: Any) -> str:
    v = str(value or "ONE_WAY").strip().upper()
    return v if v in {"ONE_WAY", "ROUND_TRIP", "MULTI_CITY"} else "ONE_WAY"


def _validate_depart_date_not_past(search: dict) -> datetime.date:
    """Validate main departure date for GUI and LLM flight search.

    This function is intentionally placed in the shared search-rule layer so the
    same past-date protection applies to both guided GUI search and LLM chat
    search before the request is sent to the provider simulator.
    """
    depart_date = str(search.get("depart_date") or "").strip()
    dep = _parse_iso_date(depart_date)
    if not dep:
        raise ValueError("Depart Date is missing or invalid.")

    today = datetime.date.today()
    if dep < today:
        raise ValueError("Depart Date cannot be earlier than today.")

    return dep


def _validate_multi_city_segment_dates(search: dict) -> None:
    """Validate optional multi-city segment dates when payload contains segments.

    The current demo can still use the common depart_date field for search, but
    this guard also supports a future/LLM payload shape where multi-city dates
    arrive as search.segments[].depart_date or similar keys.
    """
    segments = search.get("segments")
    if not isinstance(segments, list):
        return

    today = datetime.date.today()
    previous_dep = None

    for idx, seg in enumerate(segments, start=1):
        if not isinstance(seg, dict):
            continue

        raw_date = (
            seg.get("depart_date")
            or seg.get("departure_date")
            or seg.get("travel_date")
            or seg.get("date")
        )
        dep = _parse_iso_date(raw_date)
        if not dep:
            raise ValueError(f"Segment {idx} Depart Date is missing or invalid.")

        if dep < today:
            raise ValueError(f"Segment {idx} Depart Date cannot be earlier than today.")

        if previous_dep and dep < previous_dep:
            raise ValueError(f"Segment {idx} Depart Date cannot be earlier than previous segment date.")

        previous_dep = dep


def _apply_search_trip_type_rules(payload: dict) -> None:
    search = payload.get("search")
    if not isinstance(search, dict):
        return

    trip_type = _normalize_trip_type_value(search.get("trip_type"))
    search["trip_type"] = trip_type

    dep = _validate_depart_date_not_past(search)

    if trip_type == "ONE_WAY":
        search.pop("return_date", None)
        return

    if trip_type == "ROUND_TRIP":
        return_date = str(search.get("return_date") or "").strip()
        if not return_date:
            raise ValueError("Return Date is required for Round Trip search.")

        ret = _parse_iso_date(return_date)
        if not ret:
            raise ValueError("Return Date is missing or invalid.")

        if ret < datetime.date.today():
            raise ValueError("Return Date cannot be earlier than today.")

        if ret < dep:
            raise ValueError("Return Date cannot be earlier than Depart Date.")

        return

    if trip_type == "MULTI_CITY":
        _validate_multi_city_segment_dates(search)
        search.pop("return_date", None)
        return

    search.pop("return_date", None)


def _apply_booking_trip_type_from_search(payload: dict, *, agent_fsr_id: int) -> None:
    booking = payload.get("booking")
    if not isinstance(booking, dict):
        return

    search_req = _load_selected_search_request_json(agent_fsr_id)
    search = search_req.get("search") if isinstance(search_req.get("search"), dict) else {}
    trip_type = _normalize_trip_type_value(search.get("trip_type"))
    booking["trip_type"] = trip_type

    return_date = str(search.get("return_date") or "").strip()
    if trip_type == "ROUND_TRIP" and return_date:
        booking["return_date"] = return_date
    else:
        booking.pop("return_date", None)


def _enforce_single_selection(*, session_id: int, agent_fsr_id: int, endpoint_id: int = FLIGHT_SEARCH_ENDPOINT_ID) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE agent_flight_search_result
                SET selected_flag = 0
                WHERE session_id = %s
                  AND endpoint_id = %s
                  AND selected_flag = 1
                  AND agent_fsr_id <> %s
                """,
                (session_id, endpoint_id, agent_fsr_id),
            )

            cur.execute(
                """
                UPDATE agent_flight_search_result
                SET selected_flag = 1
                WHERE agent_fsr_id = %s
                  AND session_id = %s
                  AND endpoint_id = %s
                """,
                (agent_fsr_id, session_id, endpoint_id),
            )

        conn.commit()


def _friendly_flag(value: Any, yes_text: str = "Yes", no_text: str = "No") -> str:
    v = str(value or "").strip().upper()
    if v in {"Y", "YES", "TRUE", "1"}:
        return yes_text
    if v in {"N", "NO", "FALSE", "0"}:
        return no_text
    return str(value or "")


def _build_single_fare_option(item: dict) -> dict:
    fare = item.get("fare") if isinstance(item.get("fare"), dict) else {}
    flight = item.get("flight") if isinstance(item.get("flight"), dict) else {}
    price = fare.get("price") if isinstance(fare.get("price"), dict) else {}
    flight_id = flight.get("flight_id")
    fare_id = fare.get("fare_id")
    combo_key = f"{flight_id}:{fare_id}" if flight_id and fare_id else "ONEWAY_DEFAULT"
    return {
        "fare_combo_key": combo_key,
        "fare_family": fare.get("fare_basis") or "Standard",
        "travel_class": fare.get("travel_class") or "Economy",
        "currency": price.get("currency") or "",
        "total_price": {
            "base_fare": _flt(price.get("base_fare")),
            "taxes": _flt(price.get("taxes")),
            "fees": _flt(price.get("fees")),
            "total": _flt(price.get("total")),
            "currency": price.get("currency") or "",
        },
        "summary_flags": {
            "baggage_allowance": fare.get("baggage_allowance") or "-",
            "refundable_formatted": _friendly_flag((fare.get("flags") or {}).get("refundable_formatted"), "Refundable", "Non-refundable"),
            "changeable_formatted": _friendly_flag((fare.get("flags") or {}).get("changeable_formatted"), "Changeable", "Not changeable"),
        },
        "selection": {
            "outbound_flight_id": flight_id,
            "outbound_fare_id": fare_id,
            "return_flight_id": None,
            "return_fare_id": None,
        },
        "outbound_fare": fare,
        "return_fare": {},
    }


def _flt(v):
    try:
        if v is None or v == "":
            return 0.0
        return float(v)
    except Exception:
        return 0.0


def _fare_label(fare: dict) -> str:
    if not isinstance(fare, dict):
        return "Standard"
    return str(fare.get("fare_family_name") or fare.get("fare_family") or fare.get("fare_basis") or "Standard")


def _make_side_fare_card(fare: dict, *, side: str, is_default: bool = False) -> dict:
    price = fare.get("price") if isinstance(fare.get("price"), dict) else {}
    flags = fare.get("flags") if isinstance(fare.get("flags"), dict) else {}
    return {
        "side": side,
        "fare_id": fare.get("fare_id"),
        "fare_family": _fare_label(fare),
        "travel_class": str(fare.get("travel_class") or "Economy"),
        "currency": str(price.get("currency") or ""),
        "base_fare": _flt(price.get("base_fare")),
        "taxes": _flt(price.get("taxes")),
        "fees": _flt(price.get("fees")),
        "total": _flt(price.get("total")),
        "baggage": str(fare.get("baggage_allowance") or "-"),
        "refundable": _friendly_flag(flags.get("refundable_formatted"), "Refundable", "Non-refundable"),
        "changeable": _friendly_flag(flags.get("changeable_formatted"), "Changeable", "Not changeable"),
        "is_default": is_default,
    }


def _build_side_fare_cards(raw_fares: list, *, default_fare_id: Any, side: str) -> list[dict]:
    cards = []
    for fare in raw_fares or []:
        if not isinstance(fare, dict):
            continue
        cards.append(_make_side_fare_card(fare, side=side, is_default=str(fare.get("fare_id") or "") == str(default_fare_id or "")))
    return cards


def _derive_side_fares_from_combos(fare_options: list[dict], *, side: str) -> list[dict]:
    seen = {}
    key_name = "outbound_fare" if side == "outbound" else "return_fare"
    for fo in fare_options or []:
        if not isinstance(fo, dict):
            continue
        fare = fo.get(key_name) if isinstance(fo.get(key_name), dict) else {}
        fare_id = fare.get("fare_id")
        if fare_id and fare_id not in seen:
            seen[fare_id] = fare
    return list(seen.values())


def _find_roundtrip_fare_selection(item: dict, outbound_fare_id: Any, return_fare_id: Any) -> dict:
    fare_options = item.get("fare_options") if isinstance(item.get("fare_options"), list) else []
    for fo in fare_options:
        if not isinstance(fo, dict):
            continue
        sel = fo.get("selection") if isinstance(fo.get("selection"), dict) else {}
        if str(sel.get("outbound_fare_id") or "") == str(outbound_fare_id or "") and str(sel.get("return_fare_id") or "") == str(return_fare_id or ""):
            return fo
    return {}


def _normalize_confirm_model(selected_item_json: dict, search_request_json: dict) -> dict:
    item = selected_item_json if isinstance(selected_item_json, dict) else {}
    search = search_request_json.get("search") if isinstance(search_request_json.get("search"), dict) else {}
    trip_type = _normalize_trip_type_value(item.get("trip_type") or search.get("trip_type"))

    outbound = item.get("outbound") if isinstance(item.get("outbound"), dict) else {}
    return_leg = item.get("return") if isinstance(item.get("return"), dict) else {}
    if not outbound:
        outbound = item.get("flight") if isinstance(item.get("flight"), dict) else {}

    fare_options = item.get("fare_options") if isinstance(item.get("fare_options"), list) else []

    if not fare_options:
        single = _build_single_fare_option(item)
        fare = single.get("outbound_fare") if isinstance(single.get("outbound_fare"), dict) else {}
        outbound_cards = [_make_side_fare_card(fare, side="outbound", is_default=True)]
        selected_total = single.get("total_price") if isinstance(single.get("total_price"), dict) else {}
        return {
            "trip_type": trip_type,
            "search_summary": {
                "from_airport": str(search.get("from_airport") or json_get(outbound, "route.from.airport") or ""),
                "to_airport": str(search.get("to_airport") or json_get(outbound, "route.to.airport") or ""),
                "depart_date": str(search.get("depart_date") or ""),
                "return_date": str(search.get("return_date") or ""),
                "cabin_class": str(search.get("cabin_class") or fare.get("travel_class") or "Economy"),
                "currency": str(search.get("currency") or selected_total.get("currency") or ""),
            },
            "journey": {"outbound": outbound, "return": return_leg},
            "outbound_fare_cards": outbound_cards,
            "return_fare_cards": [],
            "selected_fare": {
                "currency": str(selected_total.get("currency") or search.get("currency") or ""),
                "base_fare": _flt(selected_total.get("base_fare")),
                "taxes": _flt(selected_total.get("taxes")),
                "fees": _flt(selected_total.get("fees")),
                "total": _flt(selected_total.get("total")),
                "outbound_fare_id": fare.get("fare_id"),
                "return_fare_id": None,
                "outbound_fare_family": _fare_label(fare),
                "return_fare_family": "",
                "display_family": _fare_label(fare),
                "selection": single.get("selection") if isinstance(single.get("selection"), dict) else {},
                "fare_combo_key": str(single.get("fare_combo_key") or ""),
            },
        }

    default_key = str(item.get("default_selected_fare_combo_key") or "").strip()
    default_option = {}
    for fo in fare_options:
        if isinstance(fo, dict) and str(fo.get("fare_combo_key") or "") == default_key:
            default_option = fo
            break
    if not default_option and fare_options:
        default_option = fare_options[0] if isinstance(fare_options[0], dict) else {}

    default_sel = default_option.get("selection") if isinstance(default_option.get("selection"), dict) else {}
    default_outbound_fare_id = default_sel.get("outbound_fare_id")
    default_return_fare_id = default_sel.get("return_fare_id")

    outbound_raw = item.get("outbound_fares") if isinstance(item.get("outbound_fares"), list) else _derive_side_fares_from_combos(fare_options, side="outbound")
    return_raw = item.get("return_fares") if isinstance(item.get("return_fares"), list) else _derive_side_fares_from_combos(fare_options, side="return")

    outbound_cards = _build_side_fare_cards(outbound_raw, default_fare_id=default_outbound_fare_id, side="outbound")
    return_cards = _build_side_fare_cards(return_raw, default_fare_id=default_return_fare_id, side="return")

    selected_option = _find_roundtrip_fare_selection(item, default_outbound_fare_id, default_return_fare_id) or default_option
    if trip_type == "ONE_WAY":
        selected_option = default_option

    selected_total = selected_option.get("total_price") if isinstance(selected_option.get("total_price"), dict) else {}
    outbound_fare = selected_option.get("outbound_fare") if isinstance(selected_option.get("outbound_fare"), dict) else {}
    return_fare = selected_option.get("return_fare") if isinstance(selected_option.get("return_fare"), dict) else {}

    return {
        "trip_type": trip_type,
        "search_summary": {
            "from_airport": str(search.get("from_airport") or json_get(outbound, "route.from.airport") or ""),
            "to_airport": str(search.get("to_airport") or json_get(outbound, "route.to.airport") or ""),
            "depart_date": str(search.get("depart_date") or ""),
            "return_date": str(search.get("return_date") or ""),
            "cabin_class": str(search.get("cabin_class") or outbound_cards[0]["travel_class"] if outbound_cards else "Economy"),
            "currency": str(search.get("currency") or selected_total.get("currency") or ""),
        },
        "journey": {
            "outbound": outbound,
            "return": return_leg,
        },
        "outbound_fare_cards": outbound_cards,
        "return_fare_cards": [] if trip_type == "ONE_WAY" else return_cards,
        "selected_fare": {
            "currency": str(selected_total.get("currency") or search.get("currency") or ""),
            "base_fare": _flt(selected_total.get("base_fare")),
            "taxes": _flt(selected_total.get("taxes")),
            "fees": _flt(selected_total.get("fees")),
            "total": _flt(selected_total.get("total")),
            "outbound_fare_id": default_outbound_fare_id,
            "return_fare_id": None if trip_type == "ONE_WAY" else default_return_fare_id,
            "outbound_fare_family": _fare_label(outbound_fare),
            "return_fare_family": "" if trip_type == "ONE_WAY" else _fare_label(return_fare),
            "display_family": _fare_label(outbound_fare) if trip_type == "ONE_WAY" else f"{_fare_label(outbound_fare)} + {_fare_label(return_fare)}",
            "selection": selected_option.get("selection") if isinstance(selected_option.get("selection"), dict) else {},
            "fare_combo_key": str(selected_option.get("fare_combo_key") or ""),
        },
    }


def _find_fare_option_by_key(selected_item_json: dict, fare_combo_key: str) -> dict:
    fare_options = selected_item_json.get("fare_options") if isinstance(selected_item_json.get("fare_options"), list) else []
    for fo in fare_options:
        if isinstance(fo, dict) and str(fo.get("fare_combo_key") or "") == str(fare_combo_key or ""):
            return fo
    return fare_options[0] if fare_options and isinstance(fare_options[0], dict) else {}


def _find_fare_option_by_ids(selected_item_json: dict, outbound_fare_id: Any, return_fare_id: Any) -> dict:
    fare_options = selected_item_json.get("fare_options") if isinstance(selected_item_json.get("fare_options"), list) else []
    for fo in fare_options:
        if not isinstance(fo, dict):
            continue
        sel = fo.get("selection") if isinstance(fo.get("selection"), dict) else {}
        if str(sel.get("outbound_fare_id") or "") == str(outbound_fare_id or "") and str(sel.get("return_fare_id") or "") == str(return_fare_id or ""):
            return fo
    return {}


def _get_latest_booking(agent_fsr_id: int) -> Optional[dict]:
    sql = """
SELECT agent_booking_id, provider_booking_ref, booking_status, request_json, response_json, created_at
FROM agent_flight_booking
WHERE agent_fsr_id = %s
ORDER BY agent_booking_id DESC
LIMIT 1
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (agent_fsr_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def _get_confirmed_booking(agent_fsr_id: int) -> Optional[dict]:
    sql = """
SELECT agent_booking_id, provider_booking_ref, booking_status, request_json, response_json, created_at
FROM agent_flight_booking
WHERE agent_fsr_id = %s
  AND booking_status = 'CONFIRMED'
ORDER BY agent_booking_id DESC
LIMIT 1
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (agent_fsr_id,))
            row = cur.fetchone()
    return dict(row) if row else None


def _load_selected_row_for_display(agent_fsr_id: int, result_cols: list[dict]) -> dict:
    src = _load_selected_item_json(agent_fsr_id)
    out = {"agent_fsr_id": agent_fsr_id}

    for c in result_cols:
        cfg_id = str(c.get("cfg_id") or "")
        path = c.get("response_json_path")
        if not cfg_id or not path:
            continue
        try:
            v = _extract_from_item(src, path)
        except Exception:
            v = ""
        out[cfg_id] = "" if v is None else str(v)
    return out


def _display_text(value: Any) -> str:
    return "" if value is None else str(value)


def _safe_json_load(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            out = json.loads(value)
            return out if isinstance(out, dict) else {}
        except Exception:
            return {}
    return {}


def _build_manage_passengers(request_json: dict) -> list[dict]:
    booking = request_json.get("booking") if isinstance(request_json.get("booking"), dict) else {}
    passengers = booking.get("passengers") if isinstance(booking.get("passengers"), list) else []
    out = []
    for idx, p in enumerate(passengers, start=1):
        if not isinstance(p, dict):
            continue
        pref = p.get("preferences") if isinstance(p.get("preferences"), dict) else {}
        doc = p.get("travel_document") if isinstance(p.get("travel_document"), dict) else {}
        out.append({
            "seq": idx,
            "traveler_type": _display_text(p.get("traveler_type")),
            "full_name": (f"{str(p.get('first_name') or '').strip()} {str(p.get('last_name') or '').strip()}").strip(),
            "gender": _display_text(p.get("gender")),
            "date_of_birth": _display_text(p.get("date_of_birth")),
            "nationality_iso2": _display_text(p.get("nationality_iso2")),
            "email": _display_text(p.get("email")),
            "phone": _display_text(p.get("phone")),
            "document_type": _display_text(doc.get("document_type")),
            "document_number": _display_text(doc.get("document_number")),
            "document_expiry": _display_text(doc.get("expiry_date")),
            "seat_preference": _display_text(pref.get("seat_preference")),
            "meal_preference": _display_text(pref.get("meal_preference")),
            "language_preference": _display_text(pref.get("language_preference")),
        })
    return out

def _get_manage_booking_by_ref(*, user_id: int, booking_ref: str) -> Optional[dict]:
    sql = """
    SELECT
        b.agent_booking_id,
        b.agent_fsr_id,
        b.provider_booking_ref,
        b.booking_status,
        b.payment_status,
        b.request_json,
        b.response_json,
        b.created_at,
        r.flight_number,
        r.scheduled_departure
    FROM agent_flight_booking b
    JOIN agent_flight_search_result r
      ON r.agent_fsr_id = b.agent_fsr_id
    JOIN chat_session s
      ON s.session_id = r.session_id
    WHERE s.user_id = %s
      AND b.provider_booking_ref = %s
      AND b.booking_status = 'CONFIRMED'
    ORDER BY b.agent_booking_id DESC
    LIMIT 1
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, booking_ref))
            row = cur.fetchone()
    if not row:
        return None
    row = dict(row)
    request_json = _safe_json_load(row.get("request_json"))
    response_json = _safe_json_load(row.get("response_json"))
    
    selected_item_json = _load_selected_item_json(int(row.get("agent_fsr_id") or 0))

    booking_req = request_json.get("booking") if isinstance(request_json.get("booking"), dict) else {}
    selected_outbound_fare_id = booking_req.get("fare_id")
    selected_return_fare_id = booking_req.get("return_fare_id")
    selected_fare_combo_key = booking_req.get("fare_combo_key")

    selected_summary_item = selected_item_json
    if selected_return_fare_id:
        chosen = _find_fare_option_by_ids(selected_item_json, selected_outbound_fare_id, selected_return_fare_id)
        if chosen:
            selected_summary_item = chosen
    elif selected_fare_combo_key:
        chosen = _find_fare_option_by_key(selected_item_json, selected_fare_combo_key)
        if chosen:
            selected_summary_item = chosen

    confirmed_journey = _build_confirmed_journey(response_json, selected_summary_item)
    if isinstance(confirmed_journey, dict):
        confirmed_journey["payment_status"] = _display_text(row.get("payment_status")) or confirmed_journey.get("payment_status")
    
    passengers = _build_manage_passengers(request_json)
    return {
        "agent_booking_id": row.get("agent_booking_id"),
        "agent_fsr_id": row.get("agent_fsr_id"),
        "provider_booking_ref": row.get("provider_booking_ref"),
        "booking_status": row.get("booking_status"),
        "payment_status": _display_text(row.get("payment_status")),
        "created_at": _display_text(row.get("created_at")),
        "flight_number": _display_text(row.get("flight_number")),
        "scheduled_departure": _display_text(row.get("scheduled_departure")),
        "confirmed_journey": confirmed_journey,
        "passengers": passengers,
        "request_json": request_json,
        "response_json": response_json,
        "provider_portal_url": _build_provider_portal_url(row.get("provider_booking_ref")),
    }


def _fetch_provider_itinerary(*, booking_ref: str) -> Optional[dict]:
    requested_ref = str(booking_ref or "").strip().upper()
    if not requested_ref:
        return None

    conn_cfg = get_endpoint_connection(2)
    base_url = str(conn_cfg.get("base_url") or "").rstrip("/")
    url = f"{base_url}/v1/bookings/{quote(requested_ref)}/itinerary"
    timeout_sec = (int(conn_cfg.get("timeout_ms") or 15000) / 1000.0)

    resp = requests.get(url, timeout=timeout_sec)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json() if resp.content else {}
    return data.get("itinerary") if isinstance(data, dict) else None


def _safe_filename(value: str, *, fallback: str) -> str:
    s = re.sub(r'[^A-Za-z0-9._-]+', '_', str(value or '').strip())
    return s or fallback



def _pdf_text(value: Any, default: str = "-") -> str:
    s = str(value or "").strip()
    return s if s else default


def _build_itinerary_pdf_bytes(*, booking_ref: str, booking_view: dict, itinerary_view: dict) -> bytes:
    if SimpleDocTemplate is None or getSampleStyleSheet is None:
        raise RuntimeError("PDF engine is not available on this server. Install reportlab in the TT_AGENTIC venv.")

    import io

    def _fmt_dt(value: Any) -> str:
        return _format_datetime_compact(value) or "-"

    def _fmt_date(value: Any) -> str:
        s = str(value or '').strip()
        if not s:
            return '-'
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
            try:
                dt = datetime.datetime.strptime(s, fmt)
                return dt.strftime('%a, %b %d %y')
            except Exception:
                continue
        return s

    def _route_text(seg: dict) -> str:
        left = _pdf_text(seg.get('dep_airport_display') or seg.get('dep_airport_name') or seg.get('dep_airport_code'))
        right = _pdf_text(seg.get('arr_airport_display') or seg.get('arr_airport_name') or seg.get('arr_airport_code'))
        return f"{left} → {right}"

    def _label_for_segment(seg: dict, idx: int) -> str:
        seq = int(seg.get('sequence_no') or idx or 0)
        if seq == 1:
            return 'Outbound'
        if seq == 2:
            return 'Return'
        return f'Segment {seq}'

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"Flight Itinerary {booking_ref}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TTTitle",
        parent=styles["Title"],
        fontSize=17,
        leading=21,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#111827"),
        spaceAfter=8,
        fontName='Helvetica-Bold',
    )
    section_style = ParagraphStyle(
        "TTSection",
        parent=styles["Heading2"],
        fontSize=11,
        leading=13,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=8,
        spaceAfter=6,
        fontName='Helvetica-Bold',
    )
    normal_style = ParagraphStyle(
        "TTNormal",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#111827"),
        fontName='Helvetica',
    )
    small_style = ParagraphStyle(
        "TTSmall",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
        fontName='Helvetica',
    )

    story = []
    story.append(Paragraph("Flight Itinerary", title_style))
    story.append(Spacer(1, 2 * mm))

    confirmed = booking_view.get("confirmed_journey") if isinstance(booking_view, dict) else {}
    bs = itinerary_view.get('booking_summary') if isinstance(itinerary_view, dict) else {}
    currency = _pdf_text(bs.get('booking_currency') or confirmed.get('currency'), default='').strip()
    total_amount = _pdf_text(bs.get('booking_total_amount') or confirmed.get('total_amount'))
    total_amount_text = f"{total_amount} {currency}".strip() or '-'
    contact_email = _pdf_text(bs.get('booking_contact_email'))
    if contact_email == '-' and isinstance(booking_view.get('passengers'), list) and booking_view['passengers']:
        contact_email = _pdf_text(booking_view['passengers'][0].get('email'))
    contact_phone = _pdf_text(bs.get('booking_contact_phone'))
    if contact_phone == '-' and isinstance(booking_view.get('passengers'), list) and booking_view['passengers']:
        contact_phone = _pdf_text(booking_view['passengers'][0].get('phone'))

    header_rows = [
        ["Booking Reference", _pdf_text(bs.get('booking_reference') or confirmed.get('booking_ref') or booking_ref), "Trip & Travellers", f"{_pdf_text(bs.get('trip_type') or confirmed.get('trip_type'))} · {_pdf_text(bs.get('total_pax_count') or confirmed.get('passenger_count'))} traveller(s)"],
        ["Airline Reference", _pdf_text(booking_view.get('provider_booking_ref') or bs.get('booking_reference')), "Total Amount", total_amount_text],
        ["Booked On", _fmt_date(bs.get('booking_date') or booking_view.get('created_at')), "Contact", f"{contact_email} · {contact_phone}"],
    ]
    header_tbl = Table(header_rows, colWidths=[32 * mm, 56 * mm, 32 * mm, 58 * mm])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("Journey Details", section_style))
    segments = itinerary_view.get("segments") if isinstance(itinerary_view, dict) else []
    for idx, seg in enumerate(segments or [], start=1):
        seg_title = f"{_label_for_segment(seg, idx)} · {_pdf_text(seg.get('airline_name'))} {_pdf_text(seg.get('flight_number'))}"
        story.append(Paragraph(seg_title, normal_style))
        seg_rows = [
            ["Route", _route_text(seg)],
            ["Departure", f"{_route_text({'dep_airport_display': seg.get('dep_airport_display'), 'dep_airport_name': seg.get('dep_airport_name'), 'dep_airport_code': seg.get('dep_airport_code'), 'arr_airport_display': '', 'arr_airport_name': '', 'arr_airport_code': ''}).split(' → ')[0]}\n{_fmt_dt(seg.get('scheduled_departure'))}"],
            ["Arrival", f"{_route_text({'dep_airport_display': seg.get('arr_airport_display'), 'dep_airport_name': seg.get('arr_airport_name'), 'dep_airport_code': seg.get('arr_airport_code'), 'arr_airport_display': '', 'arr_airport_name': '', 'arr_airport_code': ''}).split(' → ')[0]}\n{_fmt_dt(seg.get('scheduled_arrival'))}"],
            ["Travel Class", _pdf_text(seg.get('cabin_class')) + (f" · {_pdf_text(seg.get('fare_family_name'))}" if _pdf_text(seg.get('fare_family_name')) != '-' else '')],
            ["Baggage", f"Cabin: {_pdf_text(seg.get('cabin_baggage'))}    Check-in: {_pdf_text(seg.get('checkin_baggage'))}"],
            ["Status", f"Payment {_pdf_text(bs.get('payment_status') or bs.get('booking_payment_status') or booking_view.get('payment_status'))} · Booking {_pdf_text(bs.get('booking_status') or booking_view.get('booking_status'))}"],
        ]
        seg_tbl = Table(seg_rows, colWidths=[28 * mm, 150 * mm])
        seg_tbl.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9e1ef")),
            ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e2e8f0")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
        ]))
        story.append(seg_tbl)
        story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Passenger Details", section_style))
    passengers = itinerary_view.get("passengers") if isinstance(itinerary_view, dict) else []
    for pax in passengers or []:
        story.append(Paragraph(_pdf_text(pax.get("passenger_name")), normal_style))
        doc_parts = [_pdf_text(pax.get('document_type'), default='').strip(), _pdf_text(pax.get('document_number'), default='').strip()]
        doc_text = ' '.join([x for x in doc_parts if x]) or '-'
        pax_rows = [
            ["Passenger Type", _pdf_text(pax.get("passenger_type")), "Nationality", _pdf_text(pax.get("nationality_iso2"))],
            ["Document", doc_text, "Document Expiry", _fmt_date(pax.get("document_expiry"))],
        ]
        pax_tbl = Table(pax_rows, colWidths=[30 * mm, 60 * mm, 30 * mm, 54 * mm])
        pax_tbl.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9e1ef")),
            ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e2e8f0")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.4),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(pax_tbl)

        pax_segments = pax.get("segments") if isinstance(pax.get("segments"), list) else []
        if pax_segments:
            ps_rows = [["Journey", "Ticket", "Seat", "Status", "Meal", "SSR"]]
            for seg in pax_segments:
                label = 'Outbound' if str(seg.get('sequence_no') or '') == '1' else ('Return' if str(seg.get('sequence_no') or '') == '2' else f"Segment {seg.get('sequence_no') or '-'}")
                ps_rows.append([
                    label,
                    _pdf_text(seg.get("ticket_number")),
                    _pdf_text(seg.get("seat_assignment")),
                    _pdf_text(seg.get("segment_passenger_status")),
                    _pdf_text(seg.get("meal_code")),
                    _pdf_text(seg.get("ssr_code")),
                ])
            ps_tbl = Table(ps_rows, colWidths=[22 * mm, 48 * mm, 18 * mm, 34 * mm, 24 * mm, 24 * mm])
            ps_tbl.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9e1ef")),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e2e8f0")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eff6ff")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.0),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(Spacer(1, 2 * mm))
            story.append(ps_tbl)
        story.append(Spacer(1, 4 * mm))

    doc.build(story)
    return buf.getvalue()

def _list_recent_manage_bookings(*, user_id: int, limit: int = 10) -> list[dict]:
    sql = """
    SELECT
        b.agent_booking_id,
        b.agent_fsr_id,
        b.provider_booking_ref,
        b.booking_status,
        b.response_json,
        b.created_at,
        r.flight_number,
        r.scheduled_departure
    FROM agent_flight_booking b
    JOIN agent_flight_search_result r
      ON r.agent_fsr_id = b.agent_fsr_id
    JOIN chat_session s
      ON s.session_id = r.session_id
    WHERE s.user_id = %s
      AND b.booking_status = 'CONFIRMED'
    ORDER BY b.agent_booking_id DESC
    LIMIT %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, limit))
            rows = list(cur.fetchall() or [])
    out = []
    for row in rows:
        row = dict(row)
        response_json = _safe_json_load(row.get("response_json"))
        selected_item_json = _load_selected_item_json(int(row.get("agent_fsr_id") or 0))
        journey = _build_confirmed_journey(response_json, selected_item_json)
        first_seg = journey.get("segments")[0] if isinstance(journey.get("segments"), list) and journey.get("segments") else {}
        out.append({
            "agent_booking_id": row.get("agent_booking_id"),
            "agent_fsr_id": row.get("agent_fsr_id"),
            "booking_ref": _display_text(row.get("provider_booking_ref")),
            "booking_status": _display_text(row.get("booking_status")),
            "trip_type": _display_text(journey.get("trip_type")),
            "passenger_count": _display_text(journey.get("passenger_count")),
            "segment_count": _display_text(journey.get("segment_count")),
            "currency": _display_text(journey.get("currency")),
            "total_amount": _display_text(journey.get("total_amount")),
            "created_at": _display_text(row.get("created_at")),
            "flight_number": _display_text(first_seg.get("flight_number") or row.get("flight_number")),
            "route": f"{_display_text(first_seg.get('from_airport'))} → {_display_text(first_seg.get('to_airport'))}" if first_seg else "",
            "scheduled_departure": _display_text(first_seg.get("scheduled_departure") or row.get("scheduled_departure")),
            "provider_portal_url": _build_provider_portal_url(row.get("provider_booking_ref")),
        })
    return out


def _get_booking_ref_by_agent_fsr_id(*, user_id: int, agent_fsr_id: int) -> str:
    sql = """
    SELECT b.provider_booking_ref
    FROM agent_flight_booking b
    JOIN agent_flight_search_result r
      ON r.agent_fsr_id = b.agent_fsr_id
    JOIN chat_session s
      ON s.session_id = r.session_id
    WHERE s.user_id = %s
      AND b.agent_fsr_id = %s
      AND b.booking_status = 'CONFIRMED'
    ORDER BY b.agent_booking_id DESC
    LIMIT 1
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, agent_fsr_id))
            row = cur.fetchone()
    if not row:
        return ""
    return _display_text(row.get("provider_booking_ref") if isinstance(row, dict) else row[0])


def _build_provider_portal_url(booking_ref: str) -> str:
    ref = str(booking_ref or "").strip()
    if not ref:
        return ""
    try:
        conn_cfg = get_endpoint_connection(2)
        base_url = str(conn_cfg.get("base_url") or "").strip().rstrip("/")
        if not base_url:
            return ""
        return f"{base_url}/manage-booking?booking_ref={quote(ref)}"
    except Exception:
        return ""


def _render_all_bookings_popup_html(*, rows: list[dict], user_name: str = "") -> str:
    safe_user = str(user_name or "").strip() or "User"
    body_rows = []
    for row in rows:
        booking_ref = _display_text(row.get("booking_ref"))
        flight_detail = " · ".join([p for p in [str(row.get("flight_number") or "").strip(), str(row.get("route") or "").strip()] if p]) or "-"
        travel_date = _format_datetime_compact(row.get("scheduled_departure"))
        provider_url = str(row.get("provider_portal_url") or "").strip()
        portal_html = f'<a href="{provider_url}" target="_blank" rel="noopener">Open Airline Portal</a>' if provider_url else '-'
        body_rows.append(f"<tr><td>{booking_ref}</td><td>{flight_detail}</td><td>{travel_date}</td><td>{portal_html}</td></tr>")
    if not body_rows:
        body_rows.append('<tr><td colspan="4" style="text-align:center;color:#64748b;">No confirmed bookings found.</td></tr>')
    rows_html = "".join(body_rows)
    return f"""<!doctype html>
<html><head><meta charset='utf-8'><title>My Bookings</title><meta name='viewport' content='width=device-width, initial-scale=1' />
<style>
body{{font-family:Arial,sans-serif;background:#f3f6fb;margin:0;color:#0f172a}}
.wrap{{max-width:864px;margin:0 auto;padding:16px}}
.hero{{display:flex;justify-content:space-between;align-items:flex-end;gap:14px;flex-wrap:wrap;background:#0a4bb3;color:#fff;border-radius:18px;padding:18px 20px;box-shadow:0 10px 24px rgba(10,75,179,.18)}}
.eyebrow{{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;opacity:.85}}
.h1{{font-size:28px;font-weight:900;line-height:1.1;margin:4px 0 0}}
.sub{{font-size:13px;opacity:.92;margin-top:6px}}
.meta{{padding:8px 12px;border-radius:999px;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.16);font-size:12px;font-weight:700}}
.card{{margin-top:14px;background:#fff;border:1px solid rgba(15,23,42,.08);border-radius:18px;box-shadow:0 8px 22px rgba(15,23,42,.05);overflow:hidden}}
.table-wrap{{overflow:auto}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:12px 14px;border-bottom:1px solid #e5e7eb;font-size:14px;vertical-align:top;text-align:left}}
th{{background:#f8fafc;color:#334155;font-size:12px;text-transform:uppercase;letter-spacing:.04em}}
tr:last-child td{{border-bottom:none}}
a{{color:#0a4bb3;font-weight:700;text-decoration:none}}
a:hover{{text-decoration:underline}}
</style></head>
<body><div class='wrap'>
<div class='hero'>
  <div>
    <div class='eyebrow'>Smart Trip</div>
    <div class='h1'>My All Booking</div>
    <div class='sub'>Confirmed bookings for {safe_user}. Use the airline portal link to open the provider-side booking page.</div>
  </div>
  <div class='meta'>{len(rows)} booking(s)</div>
</div>
<div class='card'>
  <div class='table-wrap'>
    <table>
      <thead><tr><th>Booking Ref #</th><th>Flight Detail</th><th>Date</th><th>View on Airline Portal</th></tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>
  </div>
</div></body></html>"""


@router.get("/portal/flight/my-bookings-popup", response_class=HTMLResponse)
def my_all_bookings_popup(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return HTMLResponse("<h3>Unauthorized</h3>", status_code=401)
    user_id = int((current_user or {}).get("user_id") or 0)
    if not user_id:
        return HTMLResponse("<h3>Unauthorized</h3>", status_code=401)
    rows = _list_recent_manage_bookings(user_id=user_id, limit=50)
    user_name = (((current_user or {}).get("first_name") or "").strip() + (" " + ((current_user or {}).get("last_name") or "").strip() if ((current_user or {}).get("last_name") or "").strip() else "")).strip() or (current_user or {}).get("username") or ""
    return HTMLResponse(_render_all_bookings_popup_html(rows=rows, user_name=user_name))


def _json_get_first(src: dict, *paths: str, default: Any = "") -> Any:
    if not isinstance(src, dict):
        return default
    for path in paths:
        if not path:
            continue
        try:
            value = json_get(src, path)
            if value not in (None, ""):
                return value
        except Exception:
            continue
    return default


def _format_datetime_compact(value: Any) -> str:
    s = str(value or '').strip()
    if not s:
        return ''
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
        try:
            dt = datetime.datetime.strptime(s, fmt)
            return dt.strftime('%a, %b %d %y %H:%M') if 'H' in fmt else dt.strftime('%a, %b %d %y')
        except Exception:
            continue
    return s


def _lookup_airport_name(airport_code: Any) -> str:
    code = str(airport_code or '').strip().upper()
    if not code:
        return ''
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT airport_name FROM airport WHERE airport_code = %s LIMIT 1", (code,))
                row = cur.fetchone()
        if isinstance(row, dict) and row.get('airport_name'):
            return str(row.get('airport_name')).strip()
    except Exception:
        pass
    return ''


def _lookup_airline_name(airline_code: Any) -> str:
    code = str(airline_code or '').strip().upper()
    if not code:
        return ''
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT airline_name FROM airline WHERE airline_code = %s LIMIT 1", (code,))
                row = cur.fetchone()
        if isinstance(row, dict) and row.get('airline_name'):
            return str(row.get('airline_name')).strip()
    except Exception:
        pass
    return ''


def _segment_airline_name(seg: dict, selected_item_json: dict | None = None) -> str:
    flight_number = str(seg.get('flight_number') or '').strip()
    leg_type = str(seg.get('leg_type') or '').strip().upper()
    item = selected_item_json if isinstance(selected_item_json, dict) else {}

    def _name_from_leg(leg: dict) -> str:
        airline = leg.get('airline') if isinstance(leg.get('airline'), dict) else {}
        name = str(airline.get('name') or '').strip()
        if name:
            return name
        code = str(airline.get('code') or '').strip()
        return _lookup_airline_name(code)

    leg = {}
    if leg_type == 'OUTBOUND':
        leg = item.get('outbound') if isinstance(item.get('outbound'), dict) else item.get('flight') if isinstance(item.get('flight'), dict) else {}
    elif leg_type == 'INBOUND':
        leg = item.get('return') if isinstance(item.get('return'), dict) else {}
    if isinstance(leg, dict) and str(leg.get('flight_number') or '').strip() == flight_number:
        found = _name_from_leg(leg)
        if found:
            return found

    if flight_number:
        return _lookup_airline_name(flight_number[:2])
    return ''


def _segment_cabin_class(seg: dict, selected_item_json: dict | None = None) -> str:
    direct = str(seg.get('cabin_class') or seg.get('cabin') or '').strip()
    if direct:
        return direct

    fare_id = str(seg.get('fare_id') or '').strip()
    leg_type = str(seg.get('leg_type') or '').strip().upper()
    item = selected_item_json if isinstance(selected_item_json, dict) else {}

    # fallback by selected leg fare directly (important for round-trip summary)
    if leg_type == 'OUTBOUND':
        f = item.get('outbound_fare') if isinstance(item.get('outbound_fare'), dict) else {}
        direct_leg = str(f.get('travel_class') or '').strip()
        if direct_leg:
            return direct_leg
    elif leg_type == 'INBOUND':
        f = item.get('return_fare') if isinstance(item.get('return_fare'), dict) else {}
        direct_leg = str(f.get('travel_class') or '').strip()
        if direct_leg:
            return direct_leg

    fare = item.get('fare') if isinstance(item.get('fare'), dict) else {}
    if fare_id and str(fare.get('fare_id') or '').strip() == fare_id:
        return str(fare.get('travel_class') or '').strip()

    for key in ('outbound_fare', 'return_fare'):
        f = item.get(key) if isinstance(item.get(key), dict) else {}
        if fare_id and str(f.get('fare_id') or '').strip() == fare_id:
            return str(f.get('travel_class') or '').strip()

    fare_options = item.get('fare_options') if isinstance(item.get('fare_options'), list) else []
    for fo in fare_options:
        if not isinstance(fo, dict):
            continue
        target = fo.get('outbound_fare') if leg_type == 'OUTBOUND' else fo.get('return_fare')
        target = target if isinstance(target, dict) else {}
        if fare_id and str(target.get('fare_id') or '').strip() == fare_id:
            return str(target.get('travel_class') or '').strip()

    return ''
    
def _airport_display_text(code: Any) -> str:
    airport_code = str(code or '').strip().upper()
    if not airport_code:
        return ''
    airport_name = _lookup_airport_name(airport_code)
    return f"{airport_code}  {airport_name}" if airport_name else airport_code


def _build_round_trip_preview(selected_item_json: dict, search_request_json: dict) -> dict:
    search = search_request_json.get("search") if isinstance(search_request_json.get("search"), dict) else {}
    trip_type = _normalize_trip_type_value(search.get("trip_type"))

    airline_name = _display_text(_json_get_first(
        selected_item_json,
        "flight.airline.name",
        "airline.airline_name",
        "airline.name",
        default=""
    ))
    from_airport = _display_text(_json_get_first(
        selected_item_json,
        "flight.route.from.airport",
        "flight.route.from_airport",
        default=""
    ))
    to_airport = _display_text(_json_get_first(
        selected_item_json,
        "flight.route.to.airport",
        "flight.route.to_airport",
        default=""
    ))
    total_amount = _display_text(_json_get_first(
        selected_item_json,
        "fare.price.total",
        "fare.display.total_amount",
        default=""
    ))
    currency = _display_text(search.get("currency") or _json_get_first(
        selected_item_json,
        "fare.price.currency",
        "fare.currency",
        default=""
    ))
    cabin_class = _display_text(search.get("travel_class") or _json_get_first(
        selected_item_json,
        "fare.travel_class",
        default=""
    ))

    outbound = {
        "leg_title": "Outbound",
        "leg_type": "OUTBOUND",
        "flight_number": _display_text(_json_get_first(selected_item_json, "flight.flight_number", default="")),
        "airline": airline_name,
        "from_airport": from_airport,
        "to_airport": to_airport,
        "scheduled_departure": _display_text(_json_get_first(selected_item_json, "flight.schedule.scheduled_departure", default="")),
        "scheduled_arrival": _display_text(_json_get_first(selected_item_json, "flight.schedule.scheduled_arrival", default="")),
        "total_amount": total_amount,
        "currency": currency,
        "cabin_class": cabin_class,
    }

    return_preview = None
    if trip_type == "ROUND_TRIP":
        return_preview = {
            "leg_title": "Return",
            "leg_type": "INBOUND",
            "flight_number": "Auto-selected at booking time",
            "airline": airline_name or "Preferred same airline if available",
            "from_airport": to_airport,
            "to_airport": from_airport,
            "scheduled_departure": _display_text(search.get("return_date")),
            "scheduled_arrival": "Chosen by provider from matching return options",
            "total_amount": "Included in final provider booking amount",
            "currency": currency,
            "cabin_class": cabin_class,
        }

    return {
        "trip_type": trip_type,
        "depart_date": _display_text(search.get("depart_date")),
        "return_date": _display_text(search.get("return_date")),
        "currency": currency,
        "cabin_class": cabin_class,
        "outbound": outbound,
        "return_preview": return_preview,
    }


def _build_confirmed_journey(response_json: dict, selected_item_json: Optional[dict] = None) -> dict:
    booking = response_json.get("booking") if isinstance(response_json.get("booking"), dict) else {}
    segments = booking.get("segments") if isinstance(booking.get("segments"), list) else []
    normalized_segments = []
    for idx, seg in enumerate(segments, start=1):
        if not isinstance(seg, dict):
            continue
        leg_type = str(seg.get("leg_type") or "").strip().upper()
        flight_number = _display_text(seg.get("flight_number"))
        airline_name = _segment_airline_name(seg, selected_item_json)
        normalized_segments.append({
            "leg_title": "Outbound" if leg_type == "OUTBOUND" else ("Return" if leg_type == "INBOUND" else f"Segment {idx}"),
            "leg_type": leg_type or f"SEGMENT_{idx}",
            "sequence_no": _display_text(seg.get("sequence_no")),
            "segment_id": _display_text(seg.get("segment_id")),
            "flight_id": _display_text(seg.get("flight_id")),
            "flight_number": flight_number,
            "airline_name": airline_name,
            "airline_display": (f"{airline_name} {flight_number}".strip() if airline_name else flight_number),
            "from_airport": _display_text(seg.get("from_airport")),
            "to_airport": _display_text(seg.get("to_airport")),
            "from_airport_display": _airport_display_text(seg.get("from_airport")),
            "to_airport_display": _airport_display_text(seg.get("to_airport")),
            "scheduled_departure": _display_text(seg.get("scheduled_departure")),
            "scheduled_departure_display": _format_datetime_compact(seg.get("scheduled_departure")),
            "scheduled_arrival": _display_text(seg.get("scheduled_arrival")),
            "scheduled_arrival_display": _format_datetime_compact(seg.get("scheduled_arrival")),
            "fare_id": _display_text(seg.get("fare_id")),            
            "cabin_class": _segment_cabin_class(seg, selected_item_json) or '-',
        })

    return {
        "trip_type": _display_text(booking.get("trip_type")),
        "booking_ref": _display_text(booking.get("booking_ref")),
        "status": _display_text(booking.get("status")),
        "payment_status": _display_text(booking.get("payment_status") or 'Pending'),
        "total_amount": _display_text(booking.get("total_amount")),
        "currency": _display_text(booking.get("currency")),
        "segment_count": _display_text(booking.get("segment_count")),
        "passenger_count": _display_text(booking.get("passenger_count")),
        "segments": normalized_segments,
    }

def _normalize_payload_for_provider(payload: dict, *, user_id: int, selected_document_ids: list[int]) -> None:
    booking = payload.get("booking")
    if not isinstance(booking, dict):
        return

    def _clean_dict(d: Any) -> dict:
        if not isinstance(d, dict):
            return {}
        out = {}
        for k, v in d.items():
            if v in (None, "", {}):
                continue
            out[k] = v
        return out

    def _traveler_to_passenger(row: dict) -> dict:
        phone = _normalize_traveller_value("phone", row.get("phone"), row)
        p = {
            "first_name": row.get("first_name"),
            "last_name": row.get("last_name"),
            "date_of_birth": row.get("date_of_birth").strftime("%Y-%m-%d") if isinstance(row.get("date_of_birth"), (datetime.date, datetime.datetime)) else row.get("date_of_birth"),
            "gender": row.get("gender"),
            "nationality_iso2": row.get("nationality_iso2"),
            "email": row.get("email"),
            "phone": phone,
            "traveler_type": row.get("traveler_type"),
            "travel_document": {
                "document_type": row.get("document_type"),
                "document_number": row.get("document_number"),
                "issuing_country_iso2": row.get("issuing_country_iso2"),
                "issue_date": row.get("issue_date").strftime("%Y-%m-%d") if isinstance(row.get("issue_date"), (datetime.date, datetime.datetime)) else row.get("issue_date"),
                "expiry_date": row.get("expiry_date").strftime("%Y-%m-%d") if isinstance(row.get("expiry_date"), (datetime.date, datetime.datetime)) else row.get("expiry_date"),
            },
            "preferences": {
                "seat_preference": row.get("seat_preference"),
                "meal_preference": row.get("meal_preference"),
                "language_preference": row.get("preferred_language"),
            },
        }
        p = {k: v for k, v in p.items() if v not in (None, "", {})}
        if "travel_document" in p and isinstance(p["travel_document"], dict):
            p["travel_document"] = {k: v for k, v in p["travel_document"].items() if v not in (None, "")}
        if "preferences" in p and isinstance(p["preferences"], dict):
            p["preferences"] = {k: v for k, v in p["preferences"].items() if v not in (None, "")}
        return p

    selected_ids: list[int] = []
    for raw_doc_id in (selected_document_ids or []):
        try:
            doc_id = int(raw_doc_id)
        except Exception:
            continue
        if doc_id > 0 and doc_id not in selected_ids:
            selected_ids.append(doc_id)

    if not selected_ids:
        raise ValueError("Please click Auto Populate Traveller Data and select traveller row(s) before booking.")

    active_rows = _get_active_traveler_rows(user_id)
    active_map = {}
    for row in active_rows:
        try:
            doc_id = int(row.get("document_id") or 0)
        except Exception:
            continue
        if doc_id > 0:
            active_map[doc_id] = row

    selected_rows: list[dict] = []
    missing_ids: list[int] = []
    for doc_id in selected_ids:
        row = active_map.get(doc_id)
        if row:
            selected_rows.append(row)
        else:
            missing_ids.append(doc_id)

    if not selected_rows:
        raise ValueError("No active traveller rows were selected for booking.")

    if missing_ids:
        raise ValueError("Some selected traveller row(s) are no longer active. Please click Auto Populate Traveller Data again.")

    adults: list[dict] = []
    children: list[dict] = []
    infants: list[dict] = []

    for row in selected_rows:
        t = str(row.get("traveler_type") or "").strip().upper()
        if t == "ADULT":
            adults.append(row)
        elif t == "CHILD":
            children.append(row)
        elif t == "INFANT":
            infants.append(row)

    if not adults:
        raise ValueError("At least one ADULT traveller must be selected for booking.")

    lead_adult = adults[0]

    ordered_rows: list[dict] = [lead_adult]
    for row in selected_rows:
        if row is lead_adult:
            continue
        ordered_rows.append(row)

    booking["pax_counts"] = {
        "adults": len(adults),
        "children": len(children),
        "infants": len(infants),
    }

    booking["passengers"] = [_traveler_to_passenger(r) for r in ordered_rows]

    # Clear old single-traveller cfg-driven blocks so they cannot override the selected list.
    booking.pop("passenger", None)
    booking.pop("travel_document", None)
    booking.pop("preferences", None)
    
def _json_get_booking_compatible(payload: dict, req_path: str) -> Any:
    req_path = (req_path or '').strip()
    if not req_path:
        return None

    alias_paths = [req_path]
    if req_path.startswith('booking.passenger.'):
        alias_paths.append(req_path.replace('booking.passenger.', 'booking.passengers[0].', 1))
    elif req_path.startswith('booking.travel_document.'):
        alias_paths.append(req_path.replace('booking.travel_document.', 'booking.passengers[0].travel_document.', 1))
    elif req_path.startswith('booking.preferences.'):
        alias_paths.append(req_path.replace('booking.preferences.', 'booking.passengers[0].preferences.', 1))

    last_exc = None
    for path in alias_paths:
        try:
            return json_get(payload, path)
        except Exception as exc:
            last_exc = exc
            continue
    if last_exc:
        raise last_exc
    return None


def _normalize_traveller_value(src_key: str, value: Any, traveler_row: Optional[dict]) -> Any:
    if value in (None, ""):
        return value

    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.strftime("%Y-%m-%d")

    key = (src_key or "").strip().lower()

    if key == "phone":
        iso = (traveler_row or {}).get("phone_iso_code")
        std = (traveler_row or {}).get("phone_std_code")
        number = str(value).strip()
        if number.startswith("+"):
            return number
        prefix = ""
        if iso not in (None, ""):
            prefix = f"+{str(iso).strip()}"
        elif std not in (None, ""):
            prefix = f"+{str(std).strip()}"
        return f"{prefix}{number}" if prefix else number

    return value


def _build_booking_autofill(*, booking_fields: list[dict], session_uuid: Optional[str], session_id: int, user_id: int, agent_fsr_id: int) -> Dict[str, str]:
    traveler_row = get_primary_active_traveler(user_id) or {}
    selected_item_json = _load_selected_item_json(agent_fsr_id)
    context_values = {
        "user_id": user_id,
        "agent_fsr_id": agent_fsr_id,
        "session_id": session_id,
        "session_uuid": session_uuid,
    }

    booking_autofill: Dict[str, str] = {}
    for f in (booking_fields or []):
        fname = str(f.get("name") or "").strip()
        if not fname:
            continue

        src_type = str(f.get("value_source_type") or "").upper().strip()
        src_key = str(f.get("value_source_key") or "").strip()
        val: Any = None

        if src_type == "TRAVELLER" and src_key:
            val = traveler_row.get(src_key)
            val = _normalize_traveller_value(src_key, val, traveler_row)
        elif src_type == "CONTEXT" and src_key:
            val = context_values.get(src_key)
        elif src_type == "SELECTED_ROW" and src_key:
            try:
                val = json_get(selected_item_json, src_key)
            except Exception:
                val = None

        if isinstance(val, (datetime.date, datetime.datetime)):
            val = val.strftime("%Y-%m-%d")

        if val not in (None, ""):
            booking_autofill[fname] = str(val)

    return booking_autofill




def _get_active_traveler_rows(user_id: int) -> list[dict]:
    rows = list_travelers(user_id) or []
    active_rows: list[dict] = []
    for row in rows:
        try:
            if int(row.get("is_active") or 0) == 1:
                active_rows.append(row)
        except Exception:
            continue
    active_rows.sort(
        key=lambda r: (
            0 if int(r.get("is_primary") or 0) == 1 else 1,
            str(r.get("traveler_type") or ""),
            str(r.get("first_name") or ""),
            str(r.get("last_name") or ""),
            int(r.get("document_id") or 0),
        )
    )
    return active_rows

@router.get("/portal/flight/search", response_class=HTMLResponse)
def flight_search_form(request: Request):
    session_uuid = get_session_uuid_from_request(request)
    if not session_uuid or not get_active_session_by_uuid(session_uuid):
        return RedirectResponse(url="/login", status_code=302)

    fields = build_search_form_fields(FLIGHT_SEARCH_ENDPOINT_ID)
    return templates.TemplateResponse(
        "flight_search.html",
        {
            "request": request,
            "title": "Flight Search",
            "fields": fields,
            "endpoint_id": FLIGHT_SEARCH_ENDPOINT_ID,
            "step": 1,
        },
    )


def _run_flight_search_payload(
    *,
    request: Request,
    session_id: int,
    payload: dict,
    fields: list[dict] | None = None,
    cols: list[dict] | None = None,
    start_event_type: str = "GUI_SEARCH_START",
    done_event_type: str = "GUI_SEARCH_DONE",
    fail_event_type: str = "GUI_SEARCH_FAILED",
    start_message: str = "Flight search started",
    done_message: str = "Flight search completed",
    fail_message: str = "Flight search failed",
    search_origin: str = "GUI",
):
    fields = fields or build_search_form_fields(FLIGHT_SEARCH_ENDPOINT_ID)
    cols = cols or build_result_grid_fields(FLIGHT_SEARCH_ENDPOINT_ID)

    try:
        _apply_search_trip_type_rules(payload)

        conn = get_endpoint_connection(FLIGHT_SEARCH_ENDPOINT_ID)

        log_info(
            session_id,
            category="TOOL",
            event_type=start_event_type,
            message=start_message,
            details={
                "endpoint_id": FLIGHT_SEARCH_ENDPOINT_ID,
                "payload": payload,
                "search_origin": search_origin,
            },
        )

        resp_json = call_provider(
            base_url=conn["base_url"],
            path=conn["path"],
            http_method=conn["http_method"],
            payload=payload,
            timeout_ms=conn.get("timeout_ms"),
        )

        trip_type = _normalize_trip_type_value(json_get(payload, "search.trip_type"))
        result_count = (resp_json.get("meta") or {}).get("result_count") if trip_type != "ROUND_TRIP" else (resp_json.get("meta") or {}).get("journey_count")

        log_info(
            session_id,
            category="TOOL",
            event_type=done_event_type,
            message=done_message,
            details={
                "endpoint_id": FLIGHT_SEARCH_ENDPOINT_ID,
                "result_count": result_count,
                "search_origin": search_origin,
            },
        )

        search_batch_id = str(uuid.uuid4())
        persist_payload = dict(payload)
        persist_payload['_meta'] = {
            'search_batch_id': search_batch_id,
            'search_origin': search_origin,
        }

        _persist_search_results(
            session_id=session_id,
            endpoint_id=FLIGHT_SEARCH_ENDPOINT_ID,
            request_payload=persist_payload,
            resp_json=resp_json,
        )

        db_rows = _fetch_search_rows(session_id, FLIGHT_SEARCH_ENDPOINT_ID, batch_id=search_batch_id)

        table_rows = []
        round_trip_cards = []
        if trip_type == "ROUND_TRIP":
            round_trip_cards = _build_round_trip_result_cards(db_rows)
        else:
            table_rows = _build_one_way_grouped_rows(db_rows, cols)

        return templates.TemplateResponse(
            "flight_results.html",
            {
                "request": request,
                "title": "Flight Results",
                "endpoint_id": FLIGHT_SEARCH_ENDPOINT_ID,
                "step": 2,
                "result_cols": cols,
                "result_rows": table_rows,
                "round_trip_cards": round_trip_cards,
                "trip_type": trip_type,
                "result_count": len(round_trip_cards) if trip_type == "ROUND_TRIP" else len(table_rows),
                "search_payload": payload,
            },
        )

    except Exception as e:
        log_fail(
            session_id,
            category="ERROR",
            event_type=fail_event_type,
            message=fail_message,
            err=e,
        )
        return templates.TemplateResponse(
            "flight_search.html",
            {
                "request": request,
                "title": "Flight Search",
                "fields": fields,
                "endpoint_id": FLIGHT_SEARCH_ENDPOINT_ID,
                "step": 2,
                "popup_message": f"Search failed: {e}",
            },
        )


@router.post("/portal/flight/search", response_class=HTMLResponse)
async def flight_search_submit(request: Request):
    session_uuid = get_session_uuid_from_request(request)
    sess = get_active_session_by_uuid(session_uuid) if session_uuid else None
    if not sess:
        return RedirectResponse(url="/login", status_code=302)
    session_id = int(sess["session_id"])

    fields = build_search_form_fields(FLIGHT_SEARCH_ENDPOINT_ID)
    cols = build_result_grid_fields(FLIGHT_SEARCH_ENDPOINT_ID)

    try:
        form = await request.form()
        payload: dict = {}
        missing_required = []

        for f in fields:
            cfg_id = int(f["cfg_id"])
            name = f["name"]
            raw = form.get(name)

            if f.get("control") == "CHECKBOX":
                raw = "Y" if raw else "N"

            value = (str(raw).strip() if raw is not None else "")

            if f.get("required") and value == "":
                missing_required.append(f.get("label") or name)
                continue

            if value == "" and not f.get("send_if_empty"):
                continue

            path = (f.get("request_json_path") or "").strip()
            if not path:
                raise ValueError(f"Missing request_json_path in cfg for cfg_id={cfg_id}")

            dt = (f.get("data_type") or "STRING").upper()
            if dt in ("INT", "INTEGER", "NUMBER") and value != "":
                try:
                    value = int(value)
                except Exception:
                    value = float(value)

            json_set(payload, path, value)

        if missing_required:
            raise ValueError("Missing required fields: " + ", ".join(missing_required))

        return _run_flight_search_payload(
            request=request,
            session_id=session_id,
            payload=payload,
            fields=fields,
            cols=cols,
            start_event_type="GUI_SEARCH_START",
            done_event_type="GUI_SEARCH_DONE",
            fail_event_type="GUI_SEARCH_FAILED",
            start_message="Flight search started",
            done_message="Flight search completed",
            fail_message="Flight search failed",
            search_origin="GUI",
        )
    except Exception as e:
        log_fail(
            session_id,
            category="ERROR",
            event_type="GUI_SEARCH_FAILED",
            message="Flight search failed",
            err=e,
        )
        return templates.TemplateResponse(
            "flight_search.html",
            {
                "request": request,
                "title": "Flight Search",
                "fields": fields,
                "endpoint_id": FLIGHT_SEARCH_ENDPOINT_ID,
                "step": 2,
                "popup_message": f"Search failed: {e}",
            },
        )


@router.get("/portal/flight/confirm", response_class=HTMLResponse)
def flight_confirm_page(request: Request, agent_fsr_id: int):
    popup_message = (request.query_params.get("msg") or "").strip()

    session_uuid = get_session_uuid_from_request(request)
    sess = get_active_session_by_uuid(session_uuid) if session_uuid else None
    if not sess:
        return RedirectResponse(url="/login", status_code=302)

    session_id = int(sess['session_id'])

    _enforce_single_selection(session_id=session_id, agent_fsr_id=agent_fsr_id, endpoint_id=FLIGHT_SEARCH_ENDPOINT_ID)
    log_info(
        session_id,
        category='UI',
        event_type='FLIGHT_SELECTED',
        message='Flight selected for confirmation',
        details={'agent_fsr_id': agent_fsr_id}
    )

    from repo.cfg_repo import build_booking_form_fields, build_result_grid_fields, fetch_booking_confirm_cfg

    result_cols = build_result_grid_fields(1)
    selected_row = _load_selected_row_for_display(agent_fsr_id, result_cols)

    if not selected_row or not selected_row.get("agent_fsr_id"):
        raise ValueError("Selected flight not found")

    booking_fields = build_booking_form_fields(2)
    booking_autofill = _build_booking_autofill(
        booking_fields=booking_fields,
        session_uuid=session_uuid,
        session_id=session_id,
        user_id=int(sess["user_id"]),
        agent_fsr_id=agent_fsr_id,
    )
    traveler_row = get_primary_active_traveler(int(sess["user_id"]))
    traveler_rows = _get_active_traveler_rows(int(sess["user_id"]))
    selected_item_json = _load_selected_item_json(agent_fsr_id)
    search_request_json = _load_selected_search_request_json(agent_fsr_id)
    confirm_model = _normalize_confirm_model(selected_item_json, search_request_json)

    existing = _get_confirmed_booking(agent_fsr_id)
    if existing:
        resp_json = existing.get("response_json")
        if isinstance(resp_json, str):
            resp_json = json.loads(resp_json) if resp_json else {}
        elif resp_json is None:
            resp_json = {}

        confirm_fields = fetch_booking_confirm_cfg(2)
        confirm_row = {}
        for c in confirm_fields:
            cfg_id = str(c.get("cfg_id"))
            path = c.get("response_json_path")
            if not cfg_id or not path:
                continue
            try:
                v = json_get(resp_json, path)
            except Exception:
                v = ""
            confirm_row[cfg_id] = "" if v is None else str(v)

        return templates.TemplateResponse(
            "flight_confirm.html",
            {
                "request": request,
                "agent_fsr_id": agent_fsr_id,
                "selected_row": selected_row,
                "result_cols": result_cols,
                "booking_fields": booking_fields,
                "booking_success": True,
                "confirm_fields": confirm_fields,
                "confirm_row": confirm_row,
                "page_msg": f"Already booked. Booking Ref: {existing.get('provider_booking_ref')}",
                "rebook_blocked": True,
                "booking_autofill": booking_autofill,
                "traveler_row": traveler_row,
                "traveler_rows": traveler_rows,
                "popup_message": popup_message,
                "confirm_model": confirm_model,
                "confirmed_journey": _build_confirmed_journey(resp_json),
                "show_manage_link": True,
                "selected_document_ids": [],
            },
        )

    return templates.TemplateResponse(
        "flight_confirm.html",
        {
            "request": request,
            "agent_fsr_id": agent_fsr_id,
            "selected_row": selected_row,
            "result_cols": result_cols,
            "booking_fields": booking_fields,
            "booking_success": False,
            "rebook_blocked": False,
            "booking_autofill": booking_autofill,
            "traveler_row": traveler_row,
                "traveler_rows": traveler_rows,
            "popup_message": popup_message,
            "confirm_model": confirm_model,
            "confirmed_journey": None,
            "show_manage_link": False,
            "selected_document_ids": [],
        },
    )


@router.post("/portal/flight/confirm", response_class=HTMLResponse)
async def flight_confirm_submit(request: Request):
    session_uuid = get_session_uuid_from_request(request)
    sess = get_active_session_by_uuid(session_uuid) if session_uuid else None
    if not sess:
        return RedirectResponse(url="/login", status_code=302)

    session_id = int(sess["session_id"])
    user_id = int(sess["user_id"])

    from repo.cfg_repo import build_booking_form_fields, fetch_booking_confirm_cfg, build_result_grid_fields

    form = await request.form()
    posted_form_data = {str(k): str(v) for k, v in form.items()}
    selected_document_ids = []
    for raw_doc_id in form.getlist("selected_document_ids"):
        try:
            doc_id = int(str(raw_doc_id).strip())
        except Exception:
            continue
        if doc_id > 0 and doc_id not in selected_document_ids:
            selected_document_ids.append(doc_id)

    raw_fsr = form.get("cfg_61") or form.get("agent_fsr_id")
    if not raw_fsr:
        raise ValueError("Missing agent_fsr_id in booking submit")

    try:
        agent_fsr_id = int(str(raw_fsr).strip())
    except Exception:
        raise ValueError("Invalid agent_fsr_id")

    _enforce_single_selection(session_id=session_id, agent_fsr_id=agent_fsr_id, endpoint_id=FLIGHT_SEARCH_ENDPOINT_ID)

    result_cols = build_result_grid_fields(1)
    booking_fields = build_booking_form_fields(2)
    selected_item_json = _load_selected_item_json(agent_fsr_id)
    search_request_json = _load_selected_search_request_json(agent_fsr_id)
    confirm_model = _normalize_confirm_model(selected_item_json, search_request_json)

    already = _get_confirmed_booking(agent_fsr_id)
    if already:
        selected_row = _load_selected_row_for_display(agent_fsr_id, result_cols)

    booking_autofill = _build_booking_autofill(
        booking_fields=booking_fields,
        session_uuid=session_uuid,
        session_id=session_id,
        user_id=int(sess["user_id"]),
        agent_fsr_id=agent_fsr_id,
    )
    traveler_row = get_primary_active_traveler(int(sess["user_id"]))
    traveler_rows = _get_active_traveler_rows(int(sess["user_id"]))

    if already:
        resp_json = already.get("response_json")
        if isinstance(resp_json, str):
            resp_json = json.loads(resp_json) if resp_json else {}
        elif resp_json is None:
            resp_json = {}

        confirm_fields = fetch_booking_confirm_cfg(2)
        confirm_row = {}
        for c in confirm_fields:
            cfg_id = str(c.get("cfg_id"))
            path = c.get("response_json_path")
            if not cfg_id or not path:
                continue
            try:
                v = json_get(resp_json, path)
            except Exception:
                v = ""
            confirm_row[cfg_id] = "" if v is None else str(v)

        return templates.TemplateResponse(
            "flight_confirm.html",
            {
                "request": request,
                "agent_fsr_id": agent_fsr_id,
                "selected_row": selected_row,
                "result_cols": result_cols,
                "booking_fields": booking_fields,
                "booking_success": True,
                "confirm_fields": confirm_fields,
                "confirm_row": confirm_row,
                "page_msg": f"Already booked. Booking Ref: {already.get('provider_booking_ref')}",
                "rebook_blocked": True,
                "booking_autofill": booking_autofill,
                "traveler_row": traveler_row,
                "traveler_rows": traveler_rows,
                "confirm_model": confirm_model,
                "confirmed_journey": _build_confirmed_journey(resp_json),
                "show_manage_link": True,
            },
        )

    selected_row = _load_selected_row_for_display(agent_fsr_id, result_cols)

    booking_autofill = _build_booking_autofill(
        booking_fields=booking_fields,
        session_uuid=session_uuid,
        session_id=session_id,
        user_id=int(sess["user_id"]),
        agent_fsr_id=agent_fsr_id,
    )
    traveler_row = get_primary_active_traveler(int(sess["user_id"]))
    traveler_rows = _get_active_traveler_rows(int(sess["user_id"]))

    payload: dict = {}

    def _is_hidden(f: dict) -> bool:
        ctl = str(f.get("ui_control_type") or f.get("control") or "").upper().strip()
        return ctl == "HIDDEN"

    def _required(f: dict) -> bool:
        if f.get("required") is True:
            return True
        if str(f.get("is_required") or "").upper() == "Y":
            return True
        return False

    def _label(f: dict) -> str:
        return str(
            f.get("ui_label")
            or f.get("label")
            or f.get("parameter_name")
            or f.get("provider_parameter_name")
            or ""
        ).strip()

    for f in booking_fields:
        cfg_id = int(f.get("cfg_id"))
        name = f"cfg_{cfg_id}"
        raw = form.get(name)

        if raw is None:
            continue

        value_str = str(raw).strip()

        if value_str == "":
            src_type = str(f.get("value_source_type") or "").upper().strip()
            if _required(f) and (not _is_hidden(f)) and src_type in (
                "", "USER_INPUT", "FORM", "TRAVELLER"
            ):
                raise ValueError(f"Missing required field: {_label(f) or name}")
            continue

        req_path = (f.get("request_json_path") or "").strip()
        if not req_path:
            raise ValueError(f"Missing request_json_path for cfg_id={cfg_id}")

        dt = str(f.get("data_type") or "STRING").upper().strip()
        value: Any = value_str
        if dt in ("INT", "INTEGER", "NUMBER"):
            try:
                value = int(value_str)
            except Exception:
                try:
                    value = float(value_str)
                except Exception:
                    value = value_str

        json_set(payload, req_path, value)

    context_values = {"agent_fsr_id": agent_fsr_id, "session_id": session_id}

    for f in booking_fields:
        req_path = (f.get("request_json_path") or "").strip()
        if not req_path:
            continue

        try:
            existing = json_get(payload, req_path)
        except Exception:
            existing = None

        if existing not in (None, "", [], {}):
            continue

        src_type = str(f.get("value_source_type") or "").upper().strip()
        src_key = str(f.get("value_source_key") or "").strip()

        if src_type == "TRAVELLER":
            field_name = str(f.get("name") or "").strip()
            v = booking_autofill.get(field_name)
            if v not in (None, ""):
                dt = str(f.get("data_type") or "STRING").upper().strip()
                if dt in ("INT", "INTEGER", "NUMBER"):
                    try:
                        v = int(v)
                    except Exception:
                        try:
                            v = float(v)
                        except Exception:
                            pass
                json_set(payload, req_path, v)

        elif src_type == "CONTEXT":
            if src_key in context_values:
                json_set(payload, req_path, context_values[src_key])

        elif src_type == "SELECTED_ROW":
            if src_key:
                try:
                    v = json_get(selected_item_json, src_key)
                except Exception:
                    v = None
                if v not in (None, ""):
                    json_set(payload, req_path, v)

    payload.setdefault("booking", {})
    _apply_booking_trip_type_from_search(payload, agent_fsr_id=agent_fsr_id)

    selected_fare_option = {}
    trip_type = _normalize_trip_type_value(json_get(payload, "booking.trip_type"))
    if trip_type == "ROUND_TRIP":
        selected_outbound_fare_id = str(form.get("selected_outbound_fare_id") or "").strip()
        selected_return_fare_id = str(form.get("selected_return_fare_id") or "").strip()
        selected_fare_option = _find_fare_option_by_ids(selected_item_json, selected_outbound_fare_id, selected_return_fare_id)
    else:
        selected_fare_combo_key = str(form.get("selected_fare_combo_key") or "").strip()
        selected_fare_option = _find_fare_option_by_key(selected_item_json, selected_fare_combo_key)

    if selected_fare_option:
        sel = selected_fare_option.get("selection") if isinstance(selected_fare_option.get("selection"), dict) else {}
        if sel.get("outbound_flight_id"):
            payload["booking"]["flight_id"] = int(sel.get("outbound_flight_id"))
        if sel.get("outbound_fare_id"):
            payload["booking"]["fare_id"] = int(sel.get("outbound_fare_id"))
        if sel.get("return_flight_id"):
            payload["booking"]["return_flight_id"] = int(sel.get("return_flight_id"))
        if sel.get("return_fare_id"):
            payload["booking"]["return_fare_id"] = int(sel.get("return_fare_id"))
        if selected_fare_option.get("fare_combo_key"):
            payload["booking"]["fare_combo_key"] = str(selected_fare_option.get("fare_combo_key"))
        total_price = selected_fare_option.get("total_price") if isinstance(selected_fare_option.get("total_price"), dict) else {}
        payload["booking"]["selected_total_amount"] = _flt(total_price.get("total"))
        payload["booking"]["selected_currency"] = str(total_price.get("currency") or "")

    try:
        trace_rows = []
        for f in booking_fields:
            cfg_id = int(f.get("cfg_id"))
            req_path = (f.get("request_json_path") or "").strip()
            src_type = str(f.get("value_source_type") or "").upper().strip()
            src_key = str(f.get("value_source_key") or "").strip()
            try:
                resolved = _json_get_booking_compatible(payload, req_path) if req_path else None
            except Exception:
                resolved = None
            trace_rows.append(
                {
                    "cfg_id": cfg_id,
                    "request_json_path": req_path,
                    "value_source_type": src_type,
                    "value_source_key": src_key,
                    "resolved_value": _mask_for_trace(req_path, resolved),
                }
            )

        try:
            book_flight_id = json_get(payload, "booking.flight_id")
        except Exception:
            book_flight_id = None
        try:
            book_fare_id = json_get(payload, "booking.fare_id")
        except Exception:
            book_fare_id = None

        log_info(
            session_id,
            category="UI",
            event_type="BOOK_PAYLOAD_FIELD_SOURCE",
            message="BOOK payload built from cfg (Phase-2 trace).",
            details={
                "agent_fsr_id": agent_fsr_id,
                "highlight": {"booking.flight_id": book_flight_id, "booking.fare_id": book_fare_id},
                "fields": trace_rows,
            },
        )
    except Exception:
        pass

    try:
        _normalize_payload_for_provider(payload, user_id=user_id, selected_document_ids=selected_document_ids)
    except Exception as exc:
        return templates.TemplateResponse(
            "flight_confirm.html",
            {
                "request": request,
                "agent_fsr_id": agent_fsr_id,
                "selected_row": selected_row,
                "result_cols": result_cols,
                "booking_fields": booking_fields,
                "booking_success": False,
                "rebook_blocked": False,
                "booking_autofill": booking_autofill,
                "traveler_row": traveler_row,
                "traveler_rows": traveler_rows,
                "page_error": str(exc),
                "posted_form_data": posted_form_data,
                "confirm_model": confirm_model,
                "confirmed_journey": None,
                "selected_document_ids": selected_document_ids,
            },
            status_code=400,
        )

    for f in booking_fields:
        if not _required(f):
            continue
        req_path = (f.get("request_json_path") or "").strip()
        if not req_path:
            continue
        try:
            v = _json_get_booking_compatible(payload, req_path)
        except Exception:
            v = None
        if v is None or str(v).strip() == "":
            missing_name = _label(f) or ("cfg_%s" % f.get("cfg_id"))
            return templates.TemplateResponse(
                "flight_confirm.html",
                {
                    "request": request,
                    "agent_fsr_id": agent_fsr_id,
                    "selected_row": selected_row,
                    "result_cols": result_cols,
                    "booking_fields": booking_fields,
                    "booking_success": False,
                    "rebook_blocked": False,
                    "booking_autofill": booking_autofill,
                    "traveler_row": traveler_row,
                "traveler_rows": traveler_rows,
                    "page_error": f"Missing required field: {missing_name}",
                    "posted_form_data": posted_form_data,
                    "confirm_model": confirm_model,
                    "confirmed_journey": None,
                    "show_manage_link": False,
                    "selected_document_ids": selected_document_ids,
                },
                status_code=400,
            )

    business_validation_error = _validate_booking_payload(payload, selected_item_json=selected_item_json)
    if business_validation_error:
        return templates.TemplateResponse(
            "flight_confirm.html",
            {
                "request": request,
                "agent_fsr_id": agent_fsr_id,
                "selected_row": selected_row,
                "result_cols": result_cols,
                "booking_fields": booking_fields,
                "booking_success": False,
                "rebook_blocked": False,
                "booking_autofill": booking_autofill,
                "traveler_row": traveler_row,
                "traveler_rows": traveler_rows,
                "page_error": business_validation_error,
                "posted_form_data": posted_form_data,
                "confirm_model": confirm_model,
                "confirmed_journey": None,
                "selected_document_ids": selected_document_ids,
            },
            status_code=400,
        )

    conflict = _check_duplicate_booking_conflict(
        user_id=user_id,
        selected_agent_fsr_id=agent_fsr_id,
        search_endpoint_id=FLIGHT_SEARCH_ENDPOINT_ID,
        booking_endpoint_id=2,
    )
    if conflict:
        return templates.TemplateResponse(
            "flight_confirm.html",
            {
                "request": request,
                "agent_fsr_id": agent_fsr_id,
                "selected_row": selected_row,
                "result_cols": result_cols,
                "booking_fields": booking_fields,
                "booking_success": False,
                "rebook_blocked": True,
                "booking_autofill": booking_autofill,
                "traveler_row": traveler_row,
                "traveler_rows": traveler_rows,
                "page_error": conflict["message"],
                "popup_message": conflict["message"],
                "posted_form_data": posted_form_data,
                "confirm_model": confirm_model,
                "confirmed_journey": None,
                "show_manage_link": False,
                "provider_portal_url": "",
                "selected_document_ids": selected_document_ids,
            },
        )

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_flight_booking
                (agent_fsr_id, endpoint_id, trip_type, booking_status, request_json)
                VALUES (%s, %s, %s, 'PENDING', %s)
                """,
                (
                    agent_fsr_id,
                    2,
                    payload["booking"]["trip_type"],
                    json.dumps(payload),
                ),
            )
            agent_booking_id = cur.lastrowid

    conn_cfg = get_endpoint_connection(2)

    try:
        resp_json = call_provider(
            base_url=conn_cfg["base_url"],
            path=conn_cfg["path"],
            http_method=conn_cfg["http_method"],
            payload=payload,
            timeout_ms=conn_cfg.get("timeout_ms"),
        )
    except Exception as err:
        status_code, body_text, provider_user_message = _extract_provider_error_message(
            err,
            default_message="Provider booking failed. Please retry.",
        )

        error_obj = {"error": {"status_code": status_code, "body": body_text, "message": provider_user_message, "technical_message": str(err)}}

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE agent_flight_booking
                    SET booking_status = 'FAILED',
                        response_json = %s
                    WHERE agent_booking_id = %s
                    """,
                    (json.dumps(error_obj), agent_booking_id),
                )

        log_fail(
            session_id=session_id,
            category="TOOL",
            event_type="GUI_BOOK_FAILED",
            message=provider_user_message,
            err=err,
            details={
                "endpoint_id": 2,
                "agent_fsr_id": agent_fsr_id,
                "http_status": status_code,
                "provider_error": provider_user_message,
                "provider_response_body": body_text,
            },
        )

        return templates.TemplateResponse(
            "flight_confirm.html",
            {
                "request": request,
                "agent_fsr_id": agent_fsr_id,
                "selected_row": selected_row,
                "result_cols": result_cols,
                "booking_fields": booking_fields,
                "booking_success": False,
                "page_error": provider_user_message,
                "popup_message": provider_user_message,
                "booking_autofill": booking_autofill,
                "traveler_row": traveler_row,
                "traveler_rows": traveler_rows,
                "posted_form_data": posted_form_data,
                "confirm_model": confirm_model,
                "confirmed_journey": None,
                "show_manage_link": False,
                "provider_portal_url": "",
                "selected_document_ids": selected_document_ids,
            },
        )

    booking_ref = (resp_json or {}).get("booking", {}).get("booking_ref")
    status = (resp_json or {}).get("booking", {}).get("status", "SUCCESS")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE agent_flight_booking
                SET provider_booking_ref = %s,
                    booking_status = %s,
                    response_json = %s
                WHERE agent_booking_id = %s
                """,
                (booking_ref, str(status).upper(), json.dumps(resp_json), agent_booking_id),
            )

    log_info(
        session_id=session_id,
        category="TOOL",
        event_type="GUI_BOOK_DONE",
        message="Flight booking completed",
        details={"endpoint_id": 2, "agent_fsr_id": agent_fsr_id, "booking_ref": booking_ref},
    )

    return RedirectResponse(
        url=f"/portal/flight/booking-summary?booking_ref={quote(str(booking_ref or ''))}",
        status_code=303,
    )


@router.get("/portal/flight/booking-summary", response_class=HTMLResponse)
def flight_booking_summary_page(request: Request, booking_ref: str = ""):
    session_uuid = get_session_uuid_from_request(request)
    sess = get_active_session_by_uuid(session_uuid) if session_uuid else None
    if not sess:
        return RedirectResponse(url="/login", status_code=302)

    user_id = int(sess["user_id"])
    requested_ref = str(booking_ref or "").strip().upper()
    if not requested_ref:
        return RedirectResponse(url="/portal/flight/search", status_code=302)

    booking_view = _get_manage_booking_by_ref(user_id=user_id, booking_ref=requested_ref)
    if not booking_view:
        return RedirectResponse(url="/portal/flight/search", status_code=302)

    return templates.TemplateResponse(
        "flight_booking_summary.html",
        {
            "request": request,
            "title": "Booking Summary",
            "booking_ref": requested_ref,
            "booking_view": booking_view,
            "provider_itinerary_url": _build_provider_portal_url(requested_ref),
        },
    )

@router.get("/portal/flight/itinerary", response_class=HTMLResponse)
def flight_itinerary_page(request: Request, booking_ref: str = ""):
    session_uuid = get_session_uuid_from_request(request)
    sess = get_active_session_by_uuid(session_uuid) if session_uuid else None
    if not sess:
        return RedirectResponse(url="/login", status_code=302)

    user_id = int(sess["user_id"])
    requested_ref = str(booking_ref or "").strip().upper()
    if not requested_ref:
        return RedirectResponse(url="/portal/flight/search", status_code=302)

    booking_view = _get_manage_booking_by_ref(user_id=user_id, booking_ref=requested_ref)
    if not booking_view:
        return RedirectResponse(url="/portal/flight/search", status_code=302)

    try:
        itinerary_view = _fetch_provider_itinerary(booking_ref=requested_ref)
    except Exception as err:
        return templates.TemplateResponse(
            "flight_booking_summary.html",
            {
                "request": request,
                "title": "Booking Summary",
                "booking_ref": requested_ref,
                "booking_view": booking_view,
                "page_error": f"Unable to load itinerary now. {err}",
            },
        )

    if not itinerary_view:
        return templates.TemplateResponse(
            "flight_booking_summary.html",
            {
                "request": request,
                "title": "Booking Summary",
                "booking_ref": requested_ref,
                "booking_view": booking_view,
                "page_error": "Itinerary is not available for this booking yet.",
            },
        )

    return templates.TemplateResponse(
        "flight_itinerary.html",
        {
            "request": request,
            "title": "Itinerary",
            "booking_ref": requested_ref,
            "booking_view": booking_view,
            "itinerary_view": itinerary_view,
            "download_mode": False,
        },
    )


@router.get("/portal/flight/itinerary/download")
def flight_itinerary_download(request: Request, booking_ref: str = ""):
    session_uuid = get_session_uuid_from_request(request)
    sess = get_active_session_by_uuid(session_uuid) if session_uuid else None
    if not sess:
        return RedirectResponse(url="/login", status_code=302)

    user_id = int(sess["user_id"])
    requested_ref = str(booking_ref or "").strip().upper()
    if not requested_ref:
        return RedirectResponse(url="/portal/flight/search", status_code=302)

    booking_view = _get_manage_booking_by_ref(user_id=user_id, booking_ref=requested_ref)
    if not booking_view:
        return RedirectResponse(url="/portal/flight/search", status_code=302)

    itinerary_view = _fetch_provider_itinerary(booking_ref=requested_ref)
    if not itinerary_view:
        return RedirectResponse(url=f"/portal/flight/booking-summary?booking_ref={quote(requested_ref)}", status_code=302)

    try:
        pdf_bytes = _build_itinerary_pdf_bytes(
            booking_ref=requested_ref,
            booking_view=booking_view,
            itinerary_view=itinerary_view,
        )
    except Exception as err:
        return Response(
            content=str(err),
            media_type="text/plain",
            status_code=500,
        )

    filename = _safe_filename(f"Smart Trip_Itinerary_{requested_ref}.pdf", fallback="Smart Trip_Itinerary.pdf")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/portal/flight/payment", response_class=HTMLResponse)
async def flight_payment_page(request: Request, booking_ref: str = "", flow_mode: str = "GUI"):
    session_uuid = get_session_uuid_from_request(request)
    sess = get_active_session_by_uuid(session_uuid) if session_uuid else None
    if not sess:
        return RedirectResponse(url="/login", status_code=302)

    user_id = int(sess["user_id"])
    requested_ref = str(booking_ref or "").strip().upper()
    if not requested_ref:
        return RedirectResponse(url="/portal/flight/search", status_code=302)

    booking_view = _get_manage_booking_by_ref(user_id=user_id, booking_ref=requested_ref)
    if not booking_view:
        return RedirectResponse(url="/portal/flight/search", status_code=302)

    confirmed_journey = booking_view.get("confirmed_journey") if isinstance(booking_view, dict) else {}
    amount = _display_text((confirmed_journey or {}).get("total_amount"))
    currency = _display_text((confirmed_journey or {}).get("currency"))
    payment_status = _display_text(booking_view.get("payment_status") or (confirmed_journey or {}).get("payment_status") or "PENDING").upper()

    return templates.TemplateResponse(
        "flight_payment.html",
        {
            "request": request,
            "title": "Payment",
            "booking_ref": requested_ref,
            "amount": amount,
            "currency": currency,
            "payment_status": payment_status,
            "flow_mode": str(flow_mode or "GUI").strip().upper() or "GUI",
            "session_id": str(sess["session_id"]),
        },
    )


@router.post("/portal/flight/payment")
async def flight_payment_submit(request: Request):
    session_uuid = get_session_uuid_from_request(request)
    sess = get_active_session_by_uuid(session_uuid) if session_uuid else None
    if not sess:
        return RedirectResponse(url="/login", status_code=302)

    user_id = int(sess["user_id"])
    form = await request.form()
    requested_ref = str(form.get("booking_ref") or "").strip().upper()
    payment_method = str(form.get("payment_method") or "MOCK_CARD").strip().upper()
    flow_mode = str(form.get("flow_mode") or "GUI").strip().upper()

    if not requested_ref:
        return RedirectResponse(url="/portal/flight/search", status_code=302)

    booking_view = _get_manage_booking_by_ref(user_id=user_id, booking_ref=requested_ref)
    if not booking_view:
        return RedirectResponse(url="/portal/flight/search", status_code=302)

    confirmed_journey = booking_view.get("confirmed_journey") if isinstance(booking_view, dict) else {}
    amount = _flt((confirmed_journey or {}).get("total_amount"))
    currency = _display_text((confirmed_journey or {}).get("currency"))
    agent_booking_id = booking_view.get("agent_booking_id")

    provider_payload = {
        "payment": {
            "booking_ref": requested_ref,
            "amount": amount,
            "currency": currency,
            "payment_method": payment_method,
        }
    }

    conn_cfg = get_endpoint_connection(3)

    try:
        provider_resp = call_provider(
            base_url=conn_cfg["base_url"],
            path=conn_cfg["path"],
            http_method=conn_cfg["http_method"],
            payload=provider_payload,
            timeout_ms=conn_cfg.get("timeout_ms"),
        )

        payment = provider_resp.get("payment") if isinstance(provider_resp, dict) and isinstance(provider_resp.get("payment"), dict) else {}
        payment_status = str(payment.get("payment_status") or "FAILED").strip().upper()
        payment_ref = str(payment.get("payment_ref") or "").strip()

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_payment_txn
                    (
                        agent_booking_id,
                        endpoint_id,
                        payment_status,
                        amount,
                        currency,
                        payment_method,
                        payment_ref,
                        request_json,
                        response_json,
                        created_at
                    )
                    VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        agent_booking_id,
                        3,
                        payment_status,
                        amount,
                        currency,
                        payment_method,
                        payment_ref,
                        json.dumps(provider_payload, ensure_ascii=False),
                        json.dumps(provider_resp, ensure_ascii=False),
                    ),
                )

                cur.execute(
                    """
                    UPDATE agent_flight_booking
                    SET payment_status = %s
                    WHERE agent_booking_id = %s
                    """,
                    (payment_status, agent_booking_id),
                )
            conn.commit()

        log_info(
            session_id=int(sess["session_id"]),
            category="TOOL",
            event_type="GUI_PAYMENT_DONE",
            message="Flight payment completed",
            details={"endpoint_id": 3, "booking_ref": requested_ref, "payment_ref": payment_ref, "payment_status": payment_status},
        )

    except Exception as err:
        err_text = str(err)

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_payment_txn
                    (
                        agent_booking_id,
                        endpoint_id,
                        payment_status,
                        amount,
                        currency,
                        payment_method,
                        payment_ref,
                        request_json,
                        response_json,
                        created_at
                    )
                    VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        agent_booking_id,
                        3,
                        "FAILED",
                        amount,
                        currency,
                        payment_method,
                        "",
                        json.dumps(provider_payload, ensure_ascii=False),
                        json.dumps({"error": err_text}, ensure_ascii=False),
                    ),
                )

                cur.execute(
                    """
                    UPDATE agent_flight_booking
                    SET payment_status = 'FAILED'
                    WHERE agent_booking_id = %s
                    """,
                    (agent_booking_id,),
                )
            conn.commit()

        log_fail(
            session_id=int(sess["session_id"]),
            category="TOOL",
            event_type="GUI_PAYMENT_FAILED",
            message="Flight payment failed",
            err=err,
            details={"endpoint_id": 3, "booking_ref": requested_ref},
        )
        raise

    if flow_mode == "LLM":
        return RedirectResponse(
            url=f"/portal/flight/payment?booking_ref={quote(requested_ref)}&flow_mode=LLM",
            status_code=303,
        )

    return RedirectResponse(
        url=f"/portal/flight/booking-summary?booking_ref={quote(requested_ref)}",
        status_code=303,
    )

@router.get("/portal/audit/trace", response_class=HTMLResponse)
def audit_trace_page(
    request: Request,
    session_id: str | None = None,
    event_type: str | None = None,
    status: str | None = None,
    category: str | None = None,
    limit: int = 200,
):
    session_uuid = get_session_uuid_from_request(request)
    sess = get_active_session_by_uuid(session_uuid) if session_uuid else None
    current_user = get_current_user(request)
    current_session_id = int(sess["session_id"]) if sess and sess.get("session_id") is not None else None
    selected_session_id = None
    session_param_present = "session_id" in request.query_params
    raw_session_id = str(session_id or "").strip()
    session_input_value = raw_session_id
    if session_param_present:
        if raw_session_id:
            try:
                selected_session_id = int(raw_session_id)
            except Exception:
                selected_session_id = current_session_id
                session_input_value = str(current_session_id or "")
        else:
            selected_session_id = None
            session_input_value = ""
    else:
        selected_session_id = current_session_id
        session_input_value = str(current_session_id or "")

    selected_event_type = str(event_type or "").strip() or None
    selected_status = str(status or "").strip().upper() or None
    selected_category = str(category or "").strip().upper() or None
    selected_limit = max(1, min(int(limit or 200), 1000))

    events = fetch_audit_events(
        session_id=selected_session_id,
        event_type=selected_event_type,
        status=selected_status,
        category=selected_category,
        limit=selected_limit,
    )
    event_type_options = list_audit_event_types(selected_session_id)
    success_count = sum(1 for row in events if str(row.get("status") or "").upper() == "SUCCESS")
    fail_count = sum(1 for row in events if str(row.get("status") or "").upper() == "FAIL")

    return templates.TemplateResponse(
        "trace.html",
        {
            "request": request,
            "title": "Audit Trace Log",
            "current_session_id": current_session_id,
            "selected_session_id": selected_session_id,
            "session_input_value": session_input_value,
            "selected_event_type": selected_event_type,
            "selected_status": selected_status,
            "selected_category": selected_category,
            "selected_limit": selected_limit,
            "events": events,
            "event_type_options": event_type_options,
            "status_options": ["SUCCESS", "FAIL"],
            "category_options": ["SESSION", "UI", "VALIDATION", "PROVIDER", "DB", "TOOL", "ERROR"],
            "limit_options": [50, 100, 200, 500, 1000],
            "success_count": success_count,
            "fail_count": fail_count,
            "interaction_mode": (sess or {}).get("interaction_mode") if sess else None,
            "session_status": (sess or {}).get("status") if sess else None,
            "current_user_name": ((current_user or {}).get("first_name") or "").strip() + (" " + ((current_user or {}).get("last_name") or "").strip() if ((current_user or {}).get("last_name") or "").strip() else "") or (current_user or {}).get("username"),
        },
    )

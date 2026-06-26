from __future__ import annotations

import io
from datetime import datetime
from html import escape

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response

from app.db import get_conn
from app.services.flight_search import search_flights
from app.services.flight_booking import book_flight
from app.services.flight_payment import pay_flight

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
except Exception:
    colors = None
    TA_CENTER = None
    A4 = None
    ParagraphStyle = None
    getSampleStyleSheet = None
    mm = None
    Paragraph = None
    SimpleDocTemplate = None
    Spacer = None
    Table = None
    TableStyle = None

app = FastAPI(title="BookMyFlight Provider Simulator API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/flights/search")
def flights_search(payload: dict):
    try:
        return search_flights(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Provider error: {e}")


@app.post("/v1/flights/book")
def flights_book(payload: dict):
    try:
        return book_flight(payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Provider error: {e}")


@app.post("/v1/flights/pay")
def flights_pay(payload: dict):
    try:
        return pay_flight(payload)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Provider error: {e}")


@app.get("/v1/bookings/{booking_ref}/itinerary")
def booking_itinerary(booking_ref: str):
    booking_ref = str(booking_ref or "").strip().upper()
    if not booking_ref:
        raise HTTPException(status_code=400, detail="Missing booking_ref")
    booking_view = _load_provider_booking_view(booking_ref)
    if not booking_view:
        raise HTTPException(status_code=404, detail=f"Booking reference not found: {booking_ref}")
    return {"itinerary": booking_view}


def _display(value, default="-") -> str:
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default


def _format_portal_dt(value) -> str:
    if value in (None, ""):
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%a, %b %d %y %H:%M")
    raw = str(value).strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(raw, fmt).strftime("%a, %b %d %y %H:%M" if "H" in fmt else "%a, %b %d %y")
        except Exception:
            pass
    return raw


def _fmt_money(amount, currency) -> str:
    if amount in (None, ""):
        return "-"
    try:
        return f"{float(amount):,.2f} {str(currency or '').strip()}".strip()
    except Exception:
        return f"{amount} {str(currency or '').strip()}".strip()


def _airport_with_code(code, airport_name=None, airport_display=None) -> str:
    code_val = str(code or "").strip()
    name_val = str(airport_name or "").strip()
    display_val = str(airport_display or "").strip()
    if code_val and name_val:
        return f"{code_val} {name_val}"
    if code_val and display_val:
        if display_val.upper().startswith(code_val.upper() + " "):
            return display_val
        return f"{code_val} {display_val}"
    return code_val or name_val or display_val or "-"


def _safe_filename(name: str, fallback: str) -> str:
    cleaned = "".join(ch for ch in (name or "") if ch.isalnum() or ch in ("-", "_", "."))
    return cleaned or fallback


def _load_provider_booking_view(booking_ref: str) -> dict | None:
    sql_booking = """
    SELECT booking_reference, booking_date, booking_status, payment_status, trip_type, currency,
           total_amount, total_pax_count, adult_count, child_count, infant_count,
           contact_email, contact_phone
    FROM booking
    WHERE booking_reference = %s
    LIMIT 1
    """
    sql_summary = """
    SELECT *
    FROM vw_itinerary_details
    WHERE booking_reference = %s
    ORDER BY sequence_no
    """
    sql_passenger = """
    SELECT *
    FROM vw_itinerary_passenger_details
    WHERE booking_reference = %s
    ORDER BY passenger_seq, sequence_no
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_booking, (booking_ref,))
            booking = cur.fetchone()
            if not booking:
                return None
            booking_summary = dict(booking)

            try:
                cur.execute(sql_summary, (booking_ref,))
                summary_rows = list(cur.fetchall() or [])
            except Exception:
                summary_rows = []

            if not summary_rows:
                cur.execute(
                    """
                    SELECT i.segment_id, i.sequence_no, i.flight_id, i.scheduled_departure, i.scheduled_arrival,
                           i.origin_airport_code AS dep_airport_code, apd.airport_name AS dep_airport_name, apd.city_name AS dep_city, apd.airport_city_display AS dep_airport_display,
                           i.destination_airport_code AS arr_airport_code, apa.airport_name AS arr_airport_name, apa.city_name AS arr_city, apa.airport_city_display AS arr_airport_display,
                           i.cabin_class, i.segment_status, i.flight_number,
                           al.airline_name, al.airline_code, fr.cabin_baggage, fr.checkin_baggage, fr.fare_family_name,
                           NULL AS terminal_departure, NULL AS terminal_arrival
                    FROM itinerary i
                    JOIN flight f ON f.flight_id = i.flight_id
                    JOIN airline al ON al.airline_code = f.airline_code
                    JOIN airport apd ON apd.airport_code = i.origin_airport_code
                    JOIN airport apa ON apa.airport_code = i.destination_airport_code
                    LEFT JOIN fare fr ON fr.fare_id = i.fare_id
                    WHERE i.booking_reference = %s
                    ORDER BY i.sequence_no
                    """,
                    (booking_ref,),
                )
                summary_rows = list(cur.fetchall() or [])

            try:
                cur.execute(sql_passenger, (booking_ref,))
                passenger_rows = list(cur.fetchall() or [])
            except Exception:
                passenger_rows = []

            if not passenger_rows:
                cur.execute(
                    """
                    SELECT bp.booking_passenger_id, bp.passenger_seq, bp.passenger_type,
                           CONCAT(bp.first_name_snapshot, ' ', bp.last_name_snapshot) AS passenger_name,
                           bp.nationality_iso2_snapshot, bp.document_type_snapshot, bp.document_number_snapshot, bp.document_expiry_snapshot,
                           bp.email AS passenger_email, bp.phone AS passenger_phone,
                           ip.segment_id, ip.sequence_no, ip.ticket_number, ip.seat_assignment, ip.segment_passenger_status, ip.meal_code, ip.ssr_code,
                           ip.coupon_number
                    FROM booking_passenger bp
                    LEFT JOIN itinerary_passenger ip
                      ON ip.booking_reference = bp.booking_reference
                     AND ip.booking_passenger_id = bp.booking_passenger_id
                    WHERE bp.booking_reference = %s
                    ORDER BY bp.passenger_seq, ip.segment_id
                    """,
                    (booking_ref,),
                )
                passenger_rows = list(cur.fetchall() or [])

    segments = []
    seen_segment_ids = set()
    for row in summary_rows:
        seg_id = row.get("segment_id")
        if seg_id in seen_segment_ids:
            continue
        seen_segment_ids.add(seg_id)
        segments.append({
            "segment_id": seg_id,
            "sequence_no": row.get("sequence_no"),
            "flight_number": row.get("flight_number"),
            "airline_name": row.get("airline_name"),
            "airline_code": row.get("airline_code"),
            "scheduled_departure": row.get("scheduled_departure"),
            "scheduled_arrival": row.get("scheduled_arrival"),
            "dep_airport_code": row.get("dep_airport_code") or row.get("origin_airport_code"),
            "dep_airport_name": row.get("dep_airport_name"),
            "dep_city": row.get("dep_city"),
            "dep_airport_display": row.get("dep_airport_display"),
            "arr_airport_code": row.get("arr_airport_code") or row.get("destination_airport_code"),
            "arr_airport_name": row.get("arr_airport_name"),
            "arr_city": row.get("arr_city"),
            "arr_airport_display": row.get("arr_airport_display"),
            "cabin_class": row.get("cabin_class"),
            "segment_status": row.get("segment_status"),
            "cabin_baggage": row.get("cabin_baggage"),
            "checkin_baggage": row.get("checkin_baggage"),
            "fare_family_name": row.get("fare_family_name"),
            "terminal_departure": row.get("terminal_departure"),
            "terminal_arrival": row.get("terminal_arrival"),
        })

    passengers_map = {}
    for row in passenger_rows:
        key = row.get("booking_passenger_id") or f"PAX-{row.get('passenger_seq')}"
        pax = passengers_map.get(key)
        if not pax:
            pax = {
                "booking_passenger_id": row.get("booking_passenger_id"),
                "passenger_seq": row.get("passenger_seq"),
                "passenger_type": row.get("passenger_type"),
                "passenger_name": row.get("passenger_name"),
                "nationality_iso2": row.get("nationality_iso2_snapshot"),
                "document_type": row.get("document_type_snapshot"),
                "document_number": row.get("document_number_snapshot"),
                "document_expiry": row.get("document_expiry_snapshot"),
                "email": row.get("passenger_email"),
                "phone": row.get("passenger_phone"),
                "segments": [],
            }
            passengers_map[key] = pax
        if row.get("segment_id") is not None:
            pax["segments"].append({
                "segment_id": row.get("segment_id"),
                "sequence_no": row.get("sequence_no"),
                "ticket_number": row.get("ticket_number"),
                "seat_assignment": row.get("seat_assignment"),
                "segment_passenger_status": row.get("segment_passenger_status"),
                "meal_code": row.get("meal_code"),
                "ssr_code": row.get("ssr_code"),
                "coupon_number": row.get("coupon_number"),
            })

    return {
        "booking_reference": booking_ref,
        "booking_summary": booking_summary,
        "segments": segments,
        "passengers": list(passengers_map.values()),
        "passenger_segment_rows": passenger_rows,
    }


def _render_page_shell(title: str, body: str) -> str:
    return f"""<!doctype html>
<html><head><meta charset='utf-8'><title>{escape(title)}</title>
<style>
body{{font-family:Arial,sans-serif;background:#f3f6fb;margin:0;color:#0f172a}}
.wrap{{max-width:1120px;margin:0 auto;padding:24px}}
.hero{{background:linear-gradient(135deg,#0a4bb3 0%,#1557c0 55%,#0b45a2 100%);color:#fff;border-radius:20px;padding:20px 28px 24px;display:flex;justify-content:space-between;gap:18px;align-items:center;flex-wrap:wrap;box-shadow:0 10px 24px rgba(10,75,179,.16)}}
.hero-titlebar{{flex:0 0 100%;text-align:center;margin-bottom:2px}}
.hero-left{{flex:1 1 480px;min-width:320px}}
.eyebrow{{display:inline-block;font-size:22px;color:#febb02;opacity:1;letter-spacing:.04em;font-weight:800;line-height:1.2;text-transform:none}}
h1{{margin:0;font-size:30px;line-height:1.12;font-weight:800}}
.sub{{margin-top:8px;opacity:.95;font-size:24px;line-height:1.16}}
.sub b{{font-size:28px;font-weight:900;letter-spacing:.02em}}
.actions{{display:flex;gap:10px;flex-wrap:wrap;align-items:center}}
.btn{{display:inline-flex;align-items:center;justify-content:center;padding:12px 16px;border-radius:12px;border:none;background:#febb02;color:#111827;text-decoration:none;font-weight:700;cursor:pointer}}
.btn.secondary{{background:#fff;color:#0a4bb3;border:1px solid #cfe0ff}}
.btn.ghost{{background:#eff6ff;color:#0a4bb3;border:1px solid #cfe0ff}}
.search{{display:flex;gap:10px;flex-wrap:wrap;align-items:center}}
.search input{{padding:14px 16px;border-radius:12px;border:none;min-width:280px}}
.search button{{padding:14px 18px;border:none;border-radius:12px;background:#febb02;font-weight:700;cursor:pointer}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-top:18px}}
.card,.section{{background:#fff;border:1px solid #d9e1ef;border-radius:18px}}
.card{{padding:18px}}
.label{{font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.06em}}
.value{{font-size:25px;font-weight:800;margin-top:8px;line-height:1.2}}
.value-sm{{font-size:15px;font-weight:700;margin-top:8px;line-height:1.35}}
.subtext{{color:#475569;margin-top:8px;line-height:1.45}}
.section{{padding:18px;margin-top:20px}}
.section h2{{margin:0 0 14px}}
.segments,.pax-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}}
.seg,.pax-card{{border:1px solid #d9e1ef;border-radius:16px;padding:16px;background:#fafcff}}
.seg-title,.pax-name{{font-size:18px;font-weight:800;margin-bottom:10px}}
.kv{{display:grid;grid-template-columns:130px minmax(0,1fr);gap:8px 12px}}
.k{{color:#475569;font-size:13px;font-weight:700}}
.v{{color:#0f172a;font-size:14px;line-height:1.45;word-break:break-word}}
.chip{{display:inline-flex;border-radius:999px;background:#eff6ff;color:#0a4bb3;border:1px solid #cfe0ff;padding:4px 10px;font-size:12px;font-weight:700;margin-right:6px;margin-bottom:6px}}
.mini{{margin-top:10px;display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px}}
.mini .box,.seg-passenger{{border:1px solid #d9e1ef;border-radius:12px;padding:10px 12px;background:#fff}}
.error{{margin-top:18px;background:#fff1f2;border:1px solid #fecdd3;color:#9f1239;padding:14px 16px;border-radius:14px}}
.empty{{color:#64748b}}
@media print{{.actions,.search{{display:none !important}} body{{background:#fff}}}}
</style></head><body><div class='wrap'>{body}</div></body></html>"""


def _render_provider_booking_html(booking_ref: str, booking_view: dict | None, page_error: str = "") -> str:
    safe_ref = escape((booking_ref or "").strip())
    if not booking_view:
        error_html = f"<div class='error'>{escape(page_error)}</div>" if page_error else ""
        body = f"""
        <div class='hero'>
          <div class='hero-titlebar'>
            <div class='eyebrow'>BookMyFlight Airline Portal</div>
          </div>
          <div class='hero-left'>
            <h1>Manage your booking</h1>
            <div class='sub'>Search your booking reference to see the live airline-side record.</div>
          </div>
          <form method='get' action='/manage-booking' class='search'>
            <input type='text' name='booking_ref' value='{safe_ref}' placeholder='Enter booking reference'>
            <button type='submit'>Find booking</button>
          </form>
        </div>
        {error_html}
        """
        return _render_page_shell("ARS Manage Booking", body)

    b = dict(booking_view.get("booking_summary") or {})
    segments = list(booking_view.get("segments") or [])
    passengers = list(booking_view.get("passengers") or [])
    booking_ref_disp = escape(_display(b.get("booking_reference") or booking_ref))
    contact_email = escape(_display(b.get("contact_email")))
    contact_phone = escape(_display(b.get("contact_phone")))
    total_amount = escape(_fmt_money(b.get("total_amount"), b.get("currency")))
    total_pax = escape(_display(b.get("total_pax_count"), default=str(len(passengers))))

    segments_html = "".join(
        f"<div class='seg'><div class='seg-title'>{'Outbound' if int(s.get('sequence_no') or 0) == 1 else 'Return'} · {escape(_display(s.get('airline_name')))} {escape(_display(s.get('flight_number')))}</div>"
        f"<div class='subtext' style='margin-top:8px;'><b>Departure</b> - {escape(_airport_with_code(s.get('dep_airport_code'), s.get('dep_airport_name'), s.get('dep_airport_display')))}</div>"
        f"<div class='subtext'><b>Arrival</b> - {escape(_airport_with_code(s.get('arr_airport_code'), s.get('arr_airport_name'), s.get('arr_airport_display')))}</div>"
        f"<div class='subtext'><b>Departure Date</b> : {escape(_format_portal_dt(s.get('scheduled_departure')))}</div>"
        f"<div class='subtext'><b>Arrival Date</b> : {escape(_format_portal_dt(s.get('scheduled_arrival')))}</div>"
        f"<div class='subtext'><b>Cabin</b> : {escape(_display(s.get('cabin_class')))}</div></div>"
        for s in segments
    ) or "<div class='empty'>No segments found.</div>"

    body = f"""
    <div class='hero'>
      <div class='hero-titlebar'>
        <div class='eyebrow'>BookMyFlight Airline Portal</div>
      </div>
      <div class='hero-left'>
        <h1>Manage your booking</h1>
        <div class='sub'>Booking reference <b>{booking_ref_disp}</b></div>
      </div>
      <div class='actions'>
        <form method='get' action='/manage-booking' class='search'>
          <input type='text' name='booking_ref' value='{safe_ref}' placeholder='Enter booking reference'>
          <button type='submit'>Find booking</button>
        </form>
      </div>
    </div>
    <div class='grid'>
      <div class='card'><div class='label'>Status</div><div class='value'>{escape(_display(b.get('booking_status')))}</div><div class='subtext'>{escape(_display(b.get('trip_type')))} · {total_pax} traveller(s)</div></div>
      <div class='card'><div class='label'>Total Amount</div><div class='value'>{total_amount}</div><div class='subtext'>Payment: {escape(_display(b.get('payment_status')))}</div></div>
      <div class='card'><div class='label'>Contact</div><div class='value-sm'>{contact_email}</div><div class='subtext'>{contact_phone}</div></div>
      <div class='card'><div class='label'>Itinerary</div><div class='subtext'>Open or download the airline-side itinerary document.</div><div class='actions' style='margin-top:12px;'><a class='btn secondary' href='/itinerary/view?booking_ref={safe_ref}'>View Itinerary</a><a class='btn ghost' href='/itinerary/download?booking_ref={safe_ref}'>Download PDF</a></div></div>
    </div>
    <div class='section'><h2>Your trip</h2><div class='segments'>{segments_html}</div></div>
    <div class='section'><h2>Travellers</h2><div class='pax-grid'>"""
    for p in passengers:
        body += f"<div class='pax-card'><div class='pax-name'>{escape(_display(p.get('passenger_name')))}</div><div class='kv'><div class='k'>Passenger Type</div><div class='v'>{escape(_display(p.get('passenger_type')))}</div><div class='k'>Nationality</div><div class='v'>{escape(_display(p.get('nationality_iso2')))}</div><div class='k'>Document</div><div class='v'>{escape(_display(p.get('document_type')))} {escape(_display(p.get('document_number'), default=''))}</div><div class='k'>Document Expiry</div><div class='v'>{escape(_display(p.get('document_expiry')))}</div></div>"
        if p.get("segments"):
            body += "<div style='margin-top:14px;'>"
            for seg in p.get("segments") or []:
                body += f"<div class='seg-passenger' style='margin-bottom:10px;'><div class='label'>Segment {escape(_display(seg.get('sequence_no')))}</div><div class='subtext'>Ticket: {escape(_display(seg.get('ticket_number')))}"
                if seg.get("coupon_number"):
                    body += f" · Coupon {escape(_display(seg.get('coupon_number')))}"
                body += f"</div><div class='subtext'>Seat: {escape(_display(seg.get('seat_assignment')))} · Status: {escape(_display(seg.get('segment_passenger_status')))}</div>"
                if seg.get("meal_code") or seg.get("ssr_code"):
                    body += f"<div class='subtext'>Meal: {escape(_display(seg.get('meal_code')))} · SSR: {escape(_display(seg.get('ssr_code')))}</div>"
                body += "</div>"
            body += "</div>"
        body += "</div>"
    body += "</div></div>"
    return _render_page_shell("ARS Manage Booking", body)


def _render_provider_itinerary_html(booking_ref: str, booking_view: dict, download_mode: bool = False) -> str:
    b = dict(booking_view.get("booking_summary") or {})
    segments = list(booking_view.get("segments") or [])
    passengers = list(booking_view.get("passengers") or [])
    safe_ref = escape(_display(booking_ref))
    total_amount = escape(_fmt_money(b.get("total_amount"), b.get("currency")))
    contact_email = escape(_display(b.get("contact_email")))
    contact_phone = escape(_display(b.get("contact_phone")))
    total_pax = escape(_display(b.get("total_pax_count"), default=str(len(passengers))))

    body = f"""
    <div class='hero'>
      <div>
        <div class='eyebrow'>BookMyFlight Itinerary</div>
        <h1>{safe_ref}</h1>
        <div class='sub'>Payment {escape(_display(b.get('payment_status')))} · Booking {escape(_display(b.get('booking_status')))}</div>
      </div>
      <div class='actions'>
        {'' if download_mode else f"<a class='btn secondary' href='/manage-booking?booking_ref={safe_ref}'>Back to Booking</a><a class='btn' href='/itinerary/download?booking_ref={safe_ref}'>Download Itinerary</a>"}
      </div>
    </div>
    <div class='grid'>
      <div class='card'><div class='label'>Booking Reference</div><div class='value'>{safe_ref}</div><div class='subtext'>Provider / Airline Ref: {safe_ref}</div></div>
      <div class='card'><div class='label'>Trip & Travellers</div><div class='value'>{escape(_display(b.get('trip_type')))}</div><div class='subtext'>{total_pax} traveller(s)</div></div>
      <div class='card'><div class='label'>Total Amount</div><div class='value'>{total_amount}</div><div class='subtext'>Booked on {escape(_format_portal_dt(b.get('booking_date')))}</div></div>
      <div class='card'><div class='label'>Contact</div><div class='value-sm'>{contact_email}</div><div class='subtext'>{contact_phone}</div></div>
    </div>
    <div class='section'><h2>Journey Details</h2><div class='segments'>"""
    for idx, s in enumerate(segments, start=1):
        label = "Outbound" if int(s.get("sequence_no") or idx or 0) == 1 else ("Return" if int(s.get("sequence_no") or idx or 0) == 2 else f"Segment {idx}")
        body += f"<div class='seg'><div class='seg-title'>{label} · {escape(_display(s.get('airline_name')))} {escape(_display(s.get('flight_number')))}</div><div style='margin-bottom:10px;'><span class='chip'>{escape(_display(s.get('cabin_class')))}</span><span class='chip'>{escape(_display(s.get('segment_status')))}</span>"
        if s.get("fare_family_name"):
            body += f"<span class='chip'>{escape(_display(s.get('fare_family_name')))}</span>"
        body += f"</div><div class='kv'><div class='k'>Departure</div><div class='v'>{escape(_airport_with_code(s.get('dep_airport_code'), s.get('dep_airport_name'), s.get('dep_airport_display')))}<br>{escape(_format_portal_dt(s.get('scheduled_departure')))}"
        if s.get("terminal_departure"):
            body += f"<br>Terminal {escape(_display(s.get('terminal_departure')))}"
        body += f"</div><div class='k'>Arrival</div><div class='v'>{escape(_airport_with_code(s.get('arr_airport_code'), s.get('arr_airport_name'), s.get('arr_airport_display')))}<br>{escape(_format_portal_dt(s.get('scheduled_arrival')))}"
        if s.get("terminal_arrival"):
            body += f"<br>Terminal {escape(_display(s.get('terminal_arrival')))}"
        body += f"</div></div><div class='mini'><div class='box'><div class='label'>Cabin Bag</div><div class='subtext'>{escape(_display(s.get('cabin_baggage')))}</div></div><div class='box'><div class='label'>Check-in Bag</div><div class='subtext'>{escape(_display(s.get('checkin_baggage')))}</div></div></div></div>"
    body += "</div></div><div class='section'><h2>Passenger Details</h2><div class='pax-grid'>"
    for p in passengers:
        body += f"<div class='pax-card'><div class='pax-name'>{escape(_display(p.get('passenger_name')))}</div><div class='kv'><div class='k'>Passenger Type</div><div class='v'>{escape(_display(p.get('passenger_type')))}</div><div class='k'>Nationality</div><div class='v'>{escape(_display(p.get('nationality_iso2')))}</div><div class='k'>Document</div><div class='v'>{escape(_display(p.get('document_type')))} {escape(_display(p.get('document_number'), default=''))}</div><div class='k'>Document Expiry</div><div class='v'>{escape(_display(p.get('document_expiry')))}</div></div>"
        if p.get("segments"):
            body += "<div style='margin-top:14px;'>"
            for seg in p.get("segments") or []:
                body += f"<div class='seg-passenger' style='margin-bottom:10px;'><div class='label'>Segment {escape(_display(seg.get('sequence_no')))}</div><div class='subtext'>Ticket: {escape(_display(seg.get('ticket_number')))}"
                if seg.get("coupon_number"):
                    body += f" · Coupon {escape(_display(seg.get('coupon_number')))}"
                body += f"</div><div class='subtext'>Seat: {escape(_display(seg.get('seat_assignment')))} · Status: {escape(_display(seg.get('segment_passenger_status')))}</div>"
                if seg.get("meal_code") or seg.get("ssr_code"):
                    body += f"<div class='subtext'>Meal: {escape(_display(seg.get('meal_code')))} · SSR: {escape(_display(seg.get('ssr_code')))}</div>"
                body += "</div>"
            body += "</div>"
        body += "</div>"
    body += "</div></div>"
    return _render_page_shell("ARS Itinerary", body)


def _build_provider_itinerary_pdf_bytes(booking_ref: str, booking_view: dict) -> bytes:
    if SimpleDocTemplate is None or getSampleStyleSheet is None:
        raise RuntimeError("PDF engine is not available on this server. Install reportlab in the ARS venv.")

    b = dict(booking_view.get("booking_summary") or {})
    segments = list(booking_view.get("segments") or [])
    passengers = list(booking_view.get("passengers") or [])
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=14 * mm, leftMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm, title=f"ARS Itinerary {booking_ref}")
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ARSTitle", parent=styles["Title"], fontSize=17, leading=21, alignment=TA_CENTER, textColor=colors.HexColor("#111827"), spaceAfter=8, fontName="Helvetica-Bold")
    section_style = ParagraphStyle("ARSSection", parent=styles["Heading2"], fontSize=11, leading=13, textColor=colors.HexColor("#0f172a"), spaceBefore=8, spaceAfter=6, fontName="Helvetica-Bold")
    normal_style = ParagraphStyle("ARSNormal", parent=styles["BodyText"], fontSize=9, leading=12, textColor=colors.HexColor("#111827"), fontName="Helvetica")
    story = [Paragraph("Flight Itinerary", title_style), Spacer(1, 2 * mm)]

    header_rows = [
        ["Booking Reference", _display(b.get("booking_reference") or booking_ref), "Trip & Travellers", f"{_display(b.get('trip_type'))} · {_display(b.get('total_pax_count'), default=str(len(passengers)))} traveller(s)"],
        ["Airline Reference", _display(b.get("booking_reference") or booking_ref), "Total Amount", _fmt_money(b.get("total_amount"), b.get("currency"))],
        ["Booked On", _format_portal_dt(b.get("booking_date")), "Contact", f"{_display(b.get('contact_email'))} · {_display(b.get('contact_phone'))}"],
    ]
    tbl = Table(header_rows, colWidths=[32 * mm, 56 * mm, 32 * mm, 58 * mm])
    tbl.setStyle(TableStyle([
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
    story.append(tbl)
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("Journey Details", section_style))
    for idx, seg in enumerate(segments, start=1):
        label = "Outbound" if int(seg.get("sequence_no") or idx or 0) == 1 else ("Return" if int(seg.get("sequence_no") or idx or 0) == 2 else f"Segment {idx}")
        story.append(Paragraph(f"{label} · {_display(seg.get('airline_name'))} {_display(seg.get('flight_number'))}", normal_style))
        seg_rows = [
            ["Departure", f"{_display((str(seg.get('dep_airport_code') or '').strip() + ' ' + str(seg.get('dep_airport_name') or '').strip()).strip() or seg.get('dep_airport_display') or seg.get('dep_airport_code'))}\n{_format_portal_dt(seg.get('scheduled_departure'))}"],
            ["Arrival", f"{_display((str(seg.get('arr_airport_code') or '').strip() + ' ' + str(seg.get('arr_airport_name') or '').strip()).strip() or seg.get('arr_airport_display') or seg.get('arr_airport_code'))}\n{_format_portal_dt(seg.get('scheduled_arrival'))}"],
            ["Travel Class", _display(seg.get('cabin_class')) + (f" · {_display(seg.get('fare_family_name'))}" if seg.get('fare_family_name') else "")],
            ["Baggage", f"Cabin: {_display(seg.get('cabin_baggage'))}    Check-in: {_display(seg.get('checkin_baggage'))}"],
            ["Status", f"Payment {_display(b.get('payment_status'))} · Booking {_display(seg.get('segment_status') or b.get('booking_status'))}"],
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
        story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("Passenger Details", section_style))
    for pax in passengers:
        story.append(Paragraph(_display(pax.get("passenger_name")), normal_style))
        pax_rows = [
            ["Passenger Type", _display(pax.get("passenger_type"))],
            ["Nationality", _display(pax.get("nationality_iso2"))],
            ["Document", f"{_display(pax.get('document_type'))} {_display(pax.get('document_number'), default='')}".strip()],
            ["Document Expiry", _display(pax.get("document_expiry"))],
        ]
        pax_tbl = Table(pax_rows, colWidths=[32 * mm, 146 * mm])
        pax_tbl.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9e1ef")),
            ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e2e8f0")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(pax_tbl)
        if pax.get("segments"):
            seg_rows = [["Segment", "Ticket", "Seat", "Status"]]
            for seg in pax.get("segments") or []:
                seg_rows.append([
                    _display(seg.get("sequence_no")),
                    _display(seg.get("ticket_number")),
                    _display(seg.get("seat_assignment")),
                    _display(seg.get("segment_passenger_status")),
                ])
            seg_tbl = Table(seg_rows, colWidths=[22 * mm, 58 * mm, 40 * mm, 58 * mm])
            seg_tbl.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9e1ef")),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#e2e8f0")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.2),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(Spacer(1, 2 * mm))
            story.append(seg_tbl)
        story.append(Spacer(1, 4 * mm))

    doc.build(story)
    return buf.getvalue()


@app.get("/manage-booking", response_class=HTMLResponse)
def manage_booking_portal(booking_ref: str = ""):
    ref = str(booking_ref or "").strip().upper()
    if not ref:
        return HTMLResponse(_render_provider_booking_html("", None))
    booking_view = _load_provider_booking_view(ref)
    if not booking_view:
        return HTMLResponse(_render_provider_booking_html(ref, None, f"Booking reference {ref} was not found."), status_code=404)
    return HTMLResponse(_render_provider_booking_html(ref, booking_view))


@app.get("/itinerary/view", response_class=HTMLResponse)
def provider_itinerary_view(booking_ref: str = ""):
    ref = str(booking_ref or "").strip().upper()
    if not ref:
        return HTMLResponse(_render_provider_booking_html("", None, "Missing booking reference."), status_code=400)
    booking_view = _load_provider_booking_view(ref)
    if not booking_view:
        return HTMLResponse(_render_provider_booking_html(ref, None, f"Booking reference {ref} was not found."), status_code=404)
    return HTMLResponse(_render_provider_itinerary_html(ref, booking_view, download_mode=False))


@app.get("/itinerary/download")
def provider_itinerary_download(booking_ref: str = ""):
    ref = str(booking_ref or "").strip().upper()
    if not ref:
        raise HTTPException(status_code=400, detail="Missing booking_ref")
    booking_view = _load_provider_booking_view(ref)
    if not booking_view:
        raise HTTPException(status_code=404, detail=f"Booking reference not found: {ref}")
    pdf_bytes = _build_provider_itinerary_pdf_bytes(ref, booking_view)
    filename = _safe_filename(f"ARS_Itinerary_{ref}.pdf", "ARS_Itinerary.pdf")
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

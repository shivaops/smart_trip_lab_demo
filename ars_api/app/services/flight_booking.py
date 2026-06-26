from __future__ import annotations

import datetime
import uuid
from fastapi import HTTPException

from app.db import get_conn


def _parse_date(value, field_name: str):
    if value in (None, "", "null"):
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except Exception:
            pass
    raise HTTPException(status_code=400, detail=f"Invalid date for {field_name}: {value}")


def _generate_booking_ref(conn) -> str:
    with conn.cursor() as cur:
        while True:
            candidate = "BK" + uuid.uuid4().hex[:8].upper()
            cur.execute("SELECT 1 FROM booking WHERE booking_reference=%s", (candidate,))
            if not cur.fetchone():
                return candidate


def _safe_get(data: dict, path: str):
    cur = data
    for key in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _normalize_trip_type(value) -> str:
    v = str(value or "ONE_WAY").strip().upper()
    return v if v in {"ONE_WAY", "ROUND_TRIP", "MULTI_CITY"} else "ONE_WAY"


def _normalize_passenger_type(value) -> str:
    v = str(value or "Adult").strip().title()
    return v if v in {"Adult", "Child", "Infant"} else "Adult"


def _normalize_cabin_class(value) -> str:
    v = str(value or "Economy").strip()
    allowed = {"Economy", "Premium Economy", "Business", "First"}
    return v if v in allowed else "Economy"


def _fetch_flight_snapshot(conn, flight_id: int):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT flight_id,
                   flight_number,
                   airline_code,
                   departure_airport,
                   arrival_airport,
                   scheduled_departure,
                   scheduled_arrival,
                   available_seats,
                   flight_status,
                   is_active
              FROM flight
             WHERE flight_id=%s
               AND is_active = 1
               AND available_seats > 0
               AND UPPER(TRIM(flight_status)) = 'SCHEDULED'
               AND scheduled_departure > NOW()
            """,
            (flight_id,),
        )
        return cur.fetchone()


def _fetch_fare_snapshot(conn, *, flight_id: int, fare_id: int):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT fare_id, flight_id, base_fare, taxes, fees, currency, travel_class
              FROM fare
             WHERE fare_id=%s AND flight_id=%s
               AND is_active = 1
            """,
            (fare_id, flight_id),
        )
        return cur.fetchone()


def _reserve_flight_seats(conn, *, flight_id: int, passenger_count: int, leg_label: str) -> None:
    """Atomically reserve seats for one flight.

    This is intentionally done during provider booking creation because this demo
    creates a CONFIRMED booking/PNR first and keeps payment as PENDING.
    The UPDATE condition prevents overbooking if two users book the last seats
    at the same time. If any later step fails, the surrounding transaction
    rollback restores the seats.
    """
    if passenger_count <= 0:
        raise HTTPException(status_code=400, detail="Passenger count must be greater than zero")

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE flight
               SET available_seats = available_seats - %s
             WHERE flight_id = %s
               AND is_active = 1
               AND available_seats >= %s
               AND UPPER(TRIM(flight_status)) = 'SCHEDULED'
               AND scheduled_departure > NOW()
            """,
            (passenger_count, flight_id, passenger_count),
        )
        if cur.rowcount != 1:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Not enough seats available for {leg_label} flight. "
                    f"Requested {passenger_count} seat(s). Please search again."
                ),
            )


def _find_return_segment(conn, *, outbound_flight: dict, return_date, cabin_class: str, currency: str):
    """Pick one inbound flight/fare for the return leg.

    Current Step-5 rule for demo:
    - reverse the route of the selected outbound flight
    - search flights on booking.return_date
    - prefer same airline as outbound
    - then cheapest fare in the same cabin/currency
    """
    if not outbound_flight:
        return None

    start_dt = datetime.datetime.combine(return_date, datetime.time.min)
    end_dt = start_dt + datetime.timedelta(days=1)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                f.flight_id,
                f.flight_number,
                f.airline_code,
                f.departure_airport,
                f.arrival_airport,
                f.scheduled_departure,
                f.scheduled_arrival,
                fr.fare_id,
                fr.travel_class,
                fr.base_fare,
                fr.taxes,
                fr.fees,
                fr.currency
            FROM flight f
            JOIN fare fr
              ON fr.flight_id = f.flight_id
            WHERE f.departure_airport = %s
              AND f.arrival_airport = %s
              AND f.scheduled_departure >= %s
              AND f.scheduled_departure < %s
              AND f.scheduled_departure > NOW()
              AND f.is_active = 1
              AND f.available_seats > 0
              AND UPPER(TRIM(f.flight_status)) = 'SCHEDULED'
              AND fr.travel_class = %s
              AND fr.currency = %s
              AND fr.is_active = 1
            ORDER BY
              CASE WHEN f.airline_code = %s THEN 0 ELSE 1 END,
              (fr.base_fare + fr.taxes + fr.fees) ASC,
              f.scheduled_departure ASC
            LIMIT 1
            """,
            (
                outbound_flight["arrival_airport"],
                outbound_flight["departure_airport"],
                start_dt,
                end_dt,
                cabin_class,
                currency,
                outbound_flight["airline_code"],
            ),
        )
        return cur.fetchone()


def book_flight(payload: dict) -> dict:
    booking = payload.get("booking") or {}

    flight_id = booking.get("flight_id")
    fare_id = booking.get("fare_id")

    if not flight_id:
        raise HTTPException(status_code=400, detail="Missing required field: flight_id (or booking.flight_id)")
    if not fare_id:
        raise HTTPException(status_code=400, detail="Missing required field: fare_id (or booking.fare_id)")

    flight_id = int(flight_id)
    fare_id = int(fare_id)
    trip_type = _normalize_trip_type(booking.get("trip_type"))
    return_date = _parse_date(booking.get("return_date"), "booking.return_date")
    return_flight_id = booking.get("return_flight_id")
    return_fare_id = booking.get("return_fare_id")
    if return_flight_id not in (None, "", "null"):
        return_flight_id = int(return_flight_id)
    else:
        return_flight_id = None
    if return_fare_id not in (None, "", "null"):
        return_fare_id = int(return_fare_id)
    else:
        return_fare_id = None

    passengers = booking.get("passengers")
    if not isinstance(passengers, list) or not passengers:
        passengers = [{
            "first_name": booking.get("first_name"),
            "last_name": booking.get("last_name"),
            "date_of_birth": booking.get("date_of_birth"),
            "gender": booking.get("gender"),
            "nationality_iso2": booking.get("nationality_iso2"),
            "email": booking.get("email"),
            "phone": booking.get("phone"),
            "traveler_type": booking.get("traveler_type") or "Adult",
            "travel_document": _safe_get(payload, "booking.travel_document") or {},
            "preferences": _safe_get(payload, "booking.preferences") or {},
        }]

    normalized_passengers = []
    for idx, psg in enumerate(passengers, start=1):
        if not isinstance(psg, dict):
            raise HTTPException(status_code=400, detail=f"Invalid passenger block at index {idx}")

        first_name = str(psg.get("first_name") or "").strip()
        last_name = str(psg.get("last_name") or "").strip()
        gender = str(psg.get("gender") or "").strip()
        nationality = str(psg.get("nationality_iso2") or "").strip().upper()
        dob = _parse_date(psg.get("date_of_birth"), f"passengers[{idx}].date_of_birth")
        email = str(psg.get("email") or "").strip() or None
        phone = str(psg.get("phone") or "").strip() or None
        traveler_type = _normalize_passenger_type(psg.get("traveler_type"))

        if not first_name:
            raise HTTPException(status_code=400, detail=f"Missing required field: passengers[{idx}].first_name")
        if not last_name:
            raise HTTPException(status_code=400, detail=f"Missing required field: passengers[{idx}].last_name")
        if not gender:
            raise HTTPException(status_code=400, detail=f"Missing required field: passengers[{idx}].gender")
        if not nationality or len(nationality) != 2:
            raise HTTPException(status_code=400, detail=f"Missing/invalid passengers[{idx}].nationality_iso2")

        doc = psg.get("travel_document") if isinstance(psg.get("travel_document"), dict) else {}
        doc_type = str(doc.get("document_type") or "").strip()
        doc_number = str(doc.get("document_number") or "").strip()
        issuing_country = str(doc.get("issuing_country_iso2") or "").strip().upper()
        doc_expiry = _parse_date(doc.get("expiry_date"), f"passengers[{idx}].travel_document.expiry_date")

        if not doc_type or not doc_number or not issuing_country:
            raise HTTPException(status_code=400, detail=f"Missing travel document fields for passengers[{idx}]")

        prefs = psg.get("preferences") if isinstance(psg.get("preferences"), dict) else {}
        seat_preference = str(prefs.get("seat_preference") or "Any").strip() or "Any"
        meal_preference = str(prefs.get("meal_preference") or "Standard").strip() or "Standard"
        language_preference = str(prefs.get("language_preference") or "EN").strip().upper() or "EN"

        normalized_passengers.append({
            "first_name": first_name,
            "last_name": last_name,
            "gender": gender,
            "nationality": nationality,
            "dob": dob,
            "email": email,
            "phone": phone,
            "traveler_type": traveler_type,
            "preferences": {
                "seat_preference": seat_preference,
                "meal_preference": meal_preference,
                "language_preference": language_preference,
            },
            "travel_document": {
                "document_type": doc_type,
                "document_number": doc_number,
                "issuing_country_iso2": issuing_country,
                "expiry_date": doc_expiry,
            },
        })

    conn = get_conn()
    try:
        conn.begin()

        fare = _fetch_fare_snapshot(conn, flight_id=flight_id, fare_id=fare_id)
        if not fare:
            raise HTTPException(status_code=400, detail="Invalid fare_id / flight_id")

        flight = _fetch_flight_snapshot(conn, flight_id)
        if not flight:
            raise HTTPException(status_code=400, detail="Invalid flight_id")

        base_per_pax = float(fare["base_fare"])
        tax_per_pax = float(fare["taxes"])
        fee_per_pax = float(fare["fees"])
        line_total = base_per_pax + tax_per_pax + fee_per_pax
        currency = fare["currency"]
        cabin_class = _normalize_cabin_class(fare.get("travel_class"))

        return_segment = None
        if trip_type == "ROUND_TRIP":
            if return_flight_id and return_fare_id:
                return_flight = _fetch_flight_snapshot(conn, return_flight_id)
                return_fare = _fetch_fare_snapshot(conn, flight_id=return_flight_id, fare_id=return_fare_id)
                if not return_flight or not return_fare:
                    raise HTTPException(status_code=400, detail="Invalid selected return flight/fare")
                return_segment = {
                    **return_flight,
                    **return_fare,
                }
            else:
                if not return_date:
                    raise HTTPException(status_code=400, detail="Missing required field: booking.return_date for ROUND_TRIP")
                return_segment = _find_return_segment(
                    conn,
                    outbound_flight=flight,
                    return_date=return_date,
                    cabin_class=cabin_class,
                    currency=currency,
                )
                if not return_segment:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"No return flight available for {flight['arrival_airport']} -> {flight['departure_airport']} on {return_date.isoformat()}"
                        ),
                    )

        adult_count = sum(1 for p in normalized_passengers if p["traveler_type"] == "Adult")
        child_count = sum(1 for p in normalized_passengers if p["traveler_type"] == "Child")
        infant_count = sum(1 for p in normalized_passengers if p["traveler_type"] == "Infant")
        total_pax = len(normalized_passengers)

        base_fare_total = round(base_per_pax * total_pax, 2)
        taxes_total = round(tax_per_pax * total_pax, 2)
        fees_total = round(fee_per_pax * total_pax, 2)
        total_amount = round(base_fare_total + taxes_total + fees_total, 2)

        if return_segment:
            return_base_per_pax = float(return_segment["base_fare"])
            return_tax_per_pax = float(return_segment["taxes"])
            return_fee_per_pax = float(return_segment["fees"])
            base_fare_total = round(base_fare_total + (return_base_per_pax * total_pax), 2)
            taxes_total = round(taxes_total + (return_tax_per_pax * total_pax), 2)
            fees_total = round(fees_total + (return_fee_per_pax * total_pax), 2)
            total_amount = round(base_fare_total + taxes_total + fees_total, 2)

        # Reserve inventory only after validating flights/fares/passengers and price.
        # This is inside the same DB transaction, so any later error rolls back the seat deduction.
        _reserve_flight_seats(
            conn,
            flight_id=flight_id,
            passenger_count=total_pax,
            leg_label="outbound",
        )
        if return_segment:
            _reserve_flight_seats(
                conn,
                flight_id=int(return_segment["flight_id"]),
                passenger_count=total_pax,
                leg_label="return",
            )

        passenger_ids = []
        booking_passenger_rows = []
        lead_adult_passenger_id = None
        lead_contact_email = None
        lead_contact_phone = None

        for seq, np in enumerate(normalized_passengers, start=1):
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT passenger_id FROM passenger
                    WHERE first_name=%s AND last_name=%s
                      AND date_of_birth=%s AND nationality_iso2=%s
                    """,
                    (np["first_name"], np["last_name"], np["dob"], np["nationality"]),
                )
                row = cur.fetchone()

            if row:
                passenger_id = row["passenger_id"]
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE passenger
                           SET gender=%s,
                               email=%s,
                               phone=%s,
                               updated_at=CURRENT_TIMESTAMP
                         WHERE passenger_id=%s
                        """,
                        (np["gender"], np["email"], np["phone"], passenger_id),
                    )
            else:
                passenger_uuid = str(uuid.uuid4())
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO passenger
                          (passenger_uuid, first_name, last_name, date_of_birth, gender,
                           nationality_iso2, email, phone)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            passenger_uuid,
                            np["first_name"],
                            np["last_name"],
                            np["dob"],
                            np["gender"],
                            np["nationality"],
                            np["email"],
                            np["phone"],
                        ),
                    )
                    passenger_id = cur.lastrowid

            passenger_ids.append(passenger_id)
            if lead_contact_email is None and np["email"]:
                lead_contact_email = np["email"]
            if lead_contact_phone is None and np["phone"]:
                lead_contact_phone = np["phone"]
            if lead_adult_passenger_id is None and np["traveler_type"] == "Adult":
                lead_adult_passenger_id = passenger_id

            doc = np["travel_document"]
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT document_id FROM travel_documents
                     WHERE document_type=%s
                       AND issuing_country_iso2=%s
                       AND document_number=%s
                    """,
                    (doc["document_type"], doc["issuing_country_iso2"], doc["document_number"]),
                )
                doc_row = cur.fetchone()
            if not doc_row:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO travel_documents
                          (passenger_id, document_type, document_number,
                           issuing_country_iso2, expiry_date, verification_status)
                        VALUES (%s,%s,%s,%s,%s,'Pending')
                        """,
                        (passenger_id, doc["document_type"], doc["document_number"], doc["issuing_country_iso2"], doc["expiry_date"]),
                    )
            else:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE travel_documents
                           SET passenger_id=%s,
                               expiry_date=%s
                         WHERE document_id=%s
                        """,
                        (passenger_id, doc["expiry_date"], doc_row["document_id"]),
                    )

            prefs = np["preferences"]
            with conn.cursor() as cur:
                cur.execute("SELECT passenger_id FROM passenger_preferences WHERE passenger_id=%s", (passenger_id,))
                pref_row = cur.fetchone()
            if not pref_row:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO passenger_preferences
                          (passenger_id, seat_preference, meal_preference, language_preference)
                        VALUES (%s,%s,%s,%s)
                        """,
                        (passenger_id, prefs["seat_preference"], prefs["meal_preference"], prefs["language_preference"]),
                    )
            else:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE passenger_preferences
                           SET seat_preference=%s,
                               meal_preference=%s,
                               language_preference=%s
                         WHERE passenger_id=%s
                        """,
                        (prefs["seat_preference"], prefs["meal_preference"], prefs["language_preference"], passenger_id),
                    )

            booking_passenger_rows.append({
                "passenger_id": passenger_id,
                "seq": seq,
                "traveler_type": np["traveler_type"],
                "is_lead": 1 if seq == 1 else 0,
                "linked_adult_passenger_id": None,
                "first_name": np["first_name"],
                "last_name": np["last_name"],
                "dob": np["dob"],
                "gender": np["gender"],
                "nationality": np["nationality"],
                "doc_type": doc["document_type"],
                "doc_number": doc["document_number"],
                "issuing_country": doc["issuing_country_iso2"],
                "doc_expiry": doc["expiry_date"],
                "seat_preference": prefs["seat_preference"],
                "meal_preference": prefs["meal_preference"],
                "language_preference": prefs["language_preference"],
            })

        lead_passenger_id = lead_adult_passenger_id or passenger_ids[0]
        booking_ref = _generate_booking_ref(conn)

        for row in booking_passenger_rows:
            if row["traveler_type"] == "Infant":
                row["linked_adult_passenger_id"] = lead_passenger_id

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO booking
                  (booking_reference, passenger_id, booking_status, payment_status,
                   booking_source, trip_type, currency, total_amount,
                   base_fare_total, taxes_total, fees_total,
                   total_pax_count, adult_count, child_count, infant_count,
                   pnr_status, contact_email, contact_phone)
                VALUES (%s,%s,'CONFIRMED','PENDING','Website',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Active',%s,%s)
                """,
                (
                    booking_ref,
                    lead_passenger_id,
                    trip_type,
                    currency,
                    total_amount,
                    base_fare_total,
                    taxes_total,
                    fees_total,
                    total_pax,
                    adult_count,
                    child_count,
                    infant_count,
                    lead_contact_email,
                    lead_contact_phone,
                ),
            )

        booking_passenger_ids = []
        for row in booking_passenger_rows:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO booking_passenger
                      (booking_reference, passenger_id, passenger_seq, passenger_type,
                       is_lead_passenger, linked_adult_passenger_id, booking_passenger_status,
                       first_name_snapshot, last_name_snapshot, date_of_birth_snapshot,
                       gender_snapshot, nationality_iso2_snapshot, document_type_snapshot,
                       document_number_snapshot, issuing_country_iso2_snapshot,
                       document_expiry_snapshot, base_fare_amount, tax_amount,
                       fee_amount, line_total_amount)
                    VALUES (%s,%s,%s,%s,%s,%s,'Confirmed',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        booking_ref,
                        row["passenger_id"],
                        row["seq"],
                        row["traveler_type"],
                        row["is_lead"],
                        row["linked_adult_passenger_id"],
                        row["first_name"],
                        row["last_name"],
                        row["dob"],
                        row["gender"],
                        row["nationality"],
                        row["doc_type"],
                        row["doc_number"],
                        row["issuing_country"],
                        row["doc_expiry"],
                        base_per_pax,
                        tax_per_pax,
                        fee_per_pax,
                        line_total,
                    ),
                )
                row["booking_passenger_id"] = cur.lastrowid
                booking_passenger_ids.append(cur.lastrowid)

        itinerary_segments = [
            {
                "sequence_no": 1,
                "flight_id": flight_id,
                "scheduled_departure": flight["scheduled_departure"],
                "scheduled_arrival": flight["scheduled_arrival"],
                "origin_airport_code": flight["departure_airport"],
                "destination_airport_code": flight["arrival_airport"],
                "marketing_airline_code": flight["airline_code"],
                "operating_airline_code": flight["airline_code"],
                "flight_number": flight["flight_number"],
                "cabin_class": cabin_class,
                "fare_id": fare_id,
                "leg_type": "OUTBOUND",
            }
        ]

        if return_segment:
            itinerary_segments.append(
                {
                    "sequence_no": 2,
                    "flight_id": int(return_segment["flight_id"]),
                    "scheduled_departure": return_segment["scheduled_departure"],
                    "scheduled_arrival": return_segment["scheduled_arrival"],
                    "origin_airport_code": return_segment["departure_airport"],
                    "destination_airport_code": return_segment["arrival_airport"],
                    "marketing_airline_code": return_segment["airline_code"],
                    "operating_airline_code": return_segment["airline_code"],
                    "flight_number": return_segment["flight_number"],
                    "cabin_class": _normalize_cabin_class(return_segment["travel_class"]),
                    "fare_id": int(return_segment["fare_id"]),
                    "leg_type": "INBOUND",
                }
            )

        created_segment_ids = []
        response_segments = []

        for seg in itinerary_segments:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO itinerary
                      (booking_reference, sequence_no, flight_id,
                       scheduled_departure, scheduled_arrival,
                       origin_airport_code, destination_airport_code,
                       marketing_airline_code, operating_airline_code, flight_number,
                       segment_status, cabin_class, fare_id)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Confirmed',%s,%s)
                    """,
                    (
                        booking_ref,
                        seg["sequence_no"],
                        seg["flight_id"],
                        seg["scheduled_departure"],
                        seg["scheduled_arrival"],
                        seg["origin_airport_code"],
                        seg["destination_airport_code"],
                        seg["marketing_airline_code"],
                        seg["operating_airline_code"],
                        seg["flight_number"],
                        seg["cabin_class"],
                        seg["fare_id"],
                    ),
                )
                seg["segment_id"] = cur.lastrowid

            created_segment_ids.append(seg["segment_id"])
            response_segments.append(
                {
                    "segment_id": seg["segment_id"],
                    "sequence_no": seg["sequence_no"],
                    "leg_type": seg["leg_type"],
                    "flight_id": seg["flight_id"],
                    "flight_number": seg["flight_number"],
                    "from_airport": seg["origin_airport_code"],
                    "to_airport": seg["destination_airport_code"],
                    "scheduled_departure": seg["scheduled_departure"].strftime("%Y-%m-%d %H:%M:%S") if seg["scheduled_departure"] else None,
                    "scheduled_arrival": seg["scheduled_arrival"].strftime("%Y-%m-%d %H:%M:%S") if seg["scheduled_arrival"] else None,
                    "fare_id": seg["fare_id"],
                }
            )

            for row in booking_passenger_rows:
                remarks = f"SeatPref={row['seat_preference']}; Lang={row['language_preference']}; Leg={seg['leg_type']}"
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO itinerary_passenger
                          (segment_id, booking_reference, booking_passenger_id, passenger_id,
                           segment_passenger_status, checkin_status, boarding_status,
                           baggage_status, meal_status, meal_code, ssr_code, remarks)
                        VALUES (%s,%s,%s,%s,'Confirmed','Not Checked-in','Not Boarded','None','Pending',%s,NULL,%s)
                        """,
                        (
                            seg["segment_id"],
                            booking_ref,
                            row["booking_passenger_id"],
                            row["passenger_id"],
                            row["meal_preference"],
                            remarks,
                        ),
                    )

        conn.commit()
        return {
            "booking": {
                "booking_ref": booking_ref,
                "status": "CONFIRMED",
                "payment_status": "PENDING",
                "total_amount": round(total_amount, 2),
                "currency": currency,
                "segment_id": created_segment_ids[0] if created_segment_ids else None,
                "segment_ids": created_segment_ids,
                "segment_count": len(created_segment_ids),
                "trip_type": trip_type,
                "lead_passenger_id": lead_passenger_id,
                "passenger_count": total_pax,
                "segments": response_segments,
            }
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Provider error: {e}")
    finally:
        conn.close()

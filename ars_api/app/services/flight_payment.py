from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from fastapi import HTTPException

from app.db import get_conn


ALLOWED_PAYMENT_METHODS = {"CARD", "UPI", "WALLET", "MOCK_CARD"}
ALLOWED_BOOKING_STATUSES = {"CONFIRMED", "PENDING"}


def _as_decimal(value, field_name: str) -> Decimal:
    if value in (None, "", "null"):
        raise HTTPException(status_code=400, detail=f"Missing required field: {field_name}")
    try:
        amt = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise HTTPException(status_code=400, detail=f"Invalid amount for {field_name}: {value}")
    if amt <= 0:
        raise HTTPException(status_code=400, detail=f"Amount must be greater than zero for {field_name}")
    return amt



def _normalize_payment_method(value) -> str:
    method = str(value or "MOCK_CARD").strip().upper()
    if method not in ALLOWED_PAYMENT_METHODS:
        raise HTTPException(status_code=400, detail=f"Unsupported payment_method: {value}")
    return method



def _generate_transaction_id(conn) -> str:
    with conn.cursor() as cur:
        while True:
            txn = "PAY" + uuid.uuid4().hex[:10].upper()
            cur.execute("SELECT 1 FROM payment WHERE transaction_id=%s", (txn,))
            if not cur.fetchone():
                return txn



def pay_flight(payload: dict) -> dict:
    payment = payload.get("payment") or {}

    booking_ref = str(payment.get("booking_ref") or payment.get("booking_reference") or "").strip().upper()
    if not booking_ref:
        raise HTTPException(status_code=400, detail="Missing required field: booking_ref (or payment.booking_ref)")

    payment_method = _normalize_payment_method(payment.get("payment_method"))
    amount = _as_decimal(payment.get("amount"), "payment.amount")
    currency = str(payment.get("currency") or "INR").strip().upper()

    conn = get_conn()
    try:
        conn.begin()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT booking_reference, booking_status, payment_status, total_amount, currency, contact_email, contact_phone
                FROM booking
                WHERE booking_reference=%s
                LIMIT 1
                """,
                (booking_ref,),
            )
            booking = cur.fetchone()
            if not booking:
                raise HTTPException(status_code=404, detail=f"Booking reference not found: {booking_ref}")

            booking_status = str(booking.get("booking_status") or "").strip().upper()
            current_payment_status = str(booking.get("payment_status") or "").strip().upper()
            db_currency = str(booking.get("currency") or "").strip().upper()
            db_total = Decimal(str(booking.get("total_amount") or "0")).quantize(Decimal("0.01"))

            if booking_status not in ALLOWED_BOOKING_STATUSES:
                raise HTTPException(status_code=400, detail=f"Booking cannot be paid in status: {booking_status or '-'}")
            if current_payment_status == "SUCCESS":
                raise HTTPException(status_code=400, detail=f"Booking {booking_ref} is already paid")
            if current_payment_status == "REFUNDED":
                raise HTTPException(status_code=400, detail=f"Booking {booking_ref} is already refunded")
            if currency != db_currency:
                raise HTTPException(status_code=400, detail=f"Currency mismatch. Expected {db_currency}, got {currency}")
            if amount != db_total:
                raise HTTPException(status_code=400, detail=f"Amount mismatch. Expected {db_total}, got {amount}")

            transaction_id = _generate_transaction_id(conn)

            cur.execute(
                """
                INSERT INTO payment
                  (booking_reference, payment_method, payment_status, amount, currency, transaction_id)
                VALUES (%s,%s,'SUCCESS',%s,%s,%s)
                """,
                (booking_ref, payment_method, amount, currency, transaction_id),
            )
            payment_id = cur.lastrowid

            cur.execute(
                """
                UPDATE booking
                   SET payment_status='SUCCESS',
                       updated_at=CURRENT_TIMESTAMP
                 WHERE booking_reference=%s
                """,
                (booking_ref,),
            )

        conn.commit()
        return {
            "payment": {
                "payment_id": payment_id,
                "booking_ref": booking_ref,
                "payment_ref": transaction_id,
                "payment_status": "SUCCESS",
                "payment_method": payment_method,
                "amount": float(amount),
                "currency": currency,
                "payer_email": payment.get("payer_email") or booking.get("contact_email"),
                "payer_phone": payment.get("payer_phone") or booking.get("contact_phone"),
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

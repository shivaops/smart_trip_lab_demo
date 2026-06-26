"""
repo/travelers_repo.py
---------------------
Repo for NEW user_travel_document traveler CRUD.

SQL only.
No FastAPI or HTML here.
"""

from db.session import get_conn


def list_travelers(user_id: int):
    sql = """
        SELECT
            document_id,
            user_id,
            traveler_type,
            document_type,
            document_number,
            issuing_country_iso2,
            issue_date,
            expiry_date,
            first_name,
            last_name,
            date_of_birth,
            gender,
            nationality_iso2,
            email,
            phone,
            phone_iso_code,
            phone_std_code,
            preferred_currency,
            preferred_language,
            seat_preference,
            meal_preference,
            notify_email,
            notify_sms,
            is_primary,
            is_active,
            created_at,
            updated_at
        FROM user_travel_document
        WHERE user_id = %s
        ORDER BY is_primary DESC, is_active DESC, traveler_type, first_name, document_id
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            return cur.fetchall()


def get_traveler_by_id(user_id: int, document_id: int):
    sql = """
        SELECT
            document_id,
            user_id,
            traveler_type,
            document_type,
            document_number,
            issuing_country_iso2,
            issue_date,
            expiry_date,
            first_name,
            last_name,
            date_of_birth,
            gender,
            nationality_iso2,
            email,
            phone,
            phone_iso_code,
            phone_std_code,
            preferred_currency,
            preferred_language,
            seat_preference,
            meal_preference,
            notify_email,
            notify_sms,
            is_primary,
            is_active,
            created_at,
            updated_at
        FROM user_travel_document
        WHERE user_id = %s
          AND document_id = %s
        LIMIT 1
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, document_id))
            return cur.fetchone()


def insert_traveler(
    user_id: int,
    traveler_type: str,
    document_type: str,
    document_number: str,
    issuing_country_iso2,
    issue_date,
    expiry_date,
    first_name,
    last_name,
    date_of_birth,
    gender,
    nationality_iso2,
    email,
    phone,
    phone_iso_code,
    phone_std_code,
    preferred_currency: str,
    preferred_language: str,
    seat_preference: str,
    meal_preference: str,
    notify_email: int,
    notify_sms: int,
    is_primary: int,
    is_active: int,
):
    with get_conn() as conn:
        with conn.cursor() as cur:
            if is_primary == 1:
                cur.execute(
                    """
                    UPDATE user_travel_document
                    SET is_primary = 0
                    WHERE user_id = %s
                    """,
                    (user_id,),
                )

            sql = """
                INSERT INTO user_travel_document (
                    user_id,
                    traveler_type,
                    document_type,
                    document_number,
                    issuing_country_iso2,
                    issue_date,
                    expiry_date,
                    first_name,
                    last_name,
                    date_of_birth,
                    gender,
                    nationality_iso2,
                    email,
                    phone,
                    phone_iso_code,
                    phone_std_code,
                    preferred_currency,
                    preferred_language,
                    seat_preference,
                    meal_preference,
                    notify_email,
                    notify_sms,
                    is_primary,
                    is_active
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
            """
            cur.execute(
                sql,
                (
                    user_id,
                    traveler_type,
                    document_type,
                    document_number,
                    issuing_country_iso2,
                    issue_date,
                    expiry_date,
                    first_name,
                    last_name,
                    date_of_birth,
                    gender,
                    nationality_iso2,
                    email,
                    phone,
                    phone_iso_code,
                    phone_std_code,
                    preferred_currency,
                    preferred_language,
                    seat_preference,
                    meal_preference,
                    notify_email,
                    notify_sms,
                    is_primary,
                    is_active,
                ),
            )


def update_traveler(
    user_id: int,
    document_id: int,
    traveler_type: str,
    document_type: str,
    document_number: str,
    issuing_country_iso2,
    issue_date,
    expiry_date,
    first_name,
    last_name,
    date_of_birth,
    gender,
    nationality_iso2,
    email,
    phone,
    phone_iso_code,
    phone_std_code,
    preferred_currency: str,
    preferred_language: str,
    seat_preference: str,
    meal_preference: str,
    notify_email: int,
    notify_sms: int,
    is_primary: int,
    is_active: int,
):
    with get_conn() as conn:
        with conn.cursor() as cur:
            if is_primary == 1:
                cur.execute(
                    """
                    UPDATE user_travel_document
                    SET is_primary = 0
                    WHERE user_id = %s
                      AND document_id <> %s
                    """,
                    (user_id, document_id),
                )

            sql = """
                UPDATE user_travel_document
                SET
                    traveler_type = %s,
                    document_type = %s,
                    document_number = %s,
                    issuing_country_iso2 = %s,
                    issue_date = %s,
                    expiry_date = %s,
                    first_name = %s,
                    last_name = %s,
                    date_of_birth = %s,
                    gender = %s,
                    nationality_iso2 = %s,
                    email = %s,
                    phone = %s,
                    phone_iso_code = %s,
                    phone_std_code = %s,
                    preferred_currency = %s,
                    preferred_language = %s,
                    seat_preference = %s,
                    meal_preference = %s,
                    notify_email = %s,
                    notify_sms = %s,
                    is_primary = %s,
                    is_active = %s
                WHERE user_id = %s
                  AND document_id = %s
            """
            cur.execute(
                sql,
                (
                    traveler_type,
                    document_type,
                    document_number,
                    issuing_country_iso2,
                    issue_date,
                    expiry_date,
                    first_name,
                    last_name,
                    date_of_birth,
                    gender,
                    nationality_iso2,
                    email,
                    phone,
                    phone_iso_code,
                    phone_std_code,
                    preferred_currency,
                    preferred_language,
                    seat_preference,
                    meal_preference,
                    notify_email,
                    notify_sms,
                    is_primary,
                    is_active,
                    user_id,
                    document_id,
                ),
            )


def toggle_traveler_active(user_id: int, document_id: int):
    sql = """
        UPDATE user_travel_document
        SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END
        WHERE user_id = %s
          AND document_id = %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, document_id))


def set_primary_traveler(user_id: int, document_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE user_travel_document
                SET is_primary = 0
                WHERE user_id = %s
                """,
                (user_id,),
            )
            cur.execute(
                """
                UPDATE user_travel_document
                SET is_primary = 1, is_active = 1
                WHERE user_id = %s
                  AND document_id = %s
                """,
                (user_id, document_id),
            )

def get_primary_active_traveler(user_id: int):
    """Return the user's primary active traveler row from user_travel_document.

    Why this helper exists:
    - booking autofill must now read one unified traveler source
    - old split repos (profile / travel_doc / preference) are removed from flight flow
    - value_source_type='TRAVELLER' points to columns from this row
    """
    sql = """
        SELECT
            document_id,
            user_id,
            traveler_type,
            document_type,
            document_number,
            issuing_country_iso2,
            issue_date,
            expiry_date,
            first_name,
            last_name,
            date_of_birth,
            gender,
            nationality_iso2,
            email,
            phone,
            phone_iso_code,
            phone_std_code,
            preferred_currency,
            preferred_language,
            seat_preference,
            meal_preference,
            notify_email,
            notify_sms,
            is_primary,
            is_active,
            created_at,
            updated_at
        FROM user_travel_document
        WHERE user_id = %s
          AND is_active = 1
        ORDER BY is_primary DESC, updated_at DESC, document_id DESC
        LIMIT 1
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            return cur.fetchone()

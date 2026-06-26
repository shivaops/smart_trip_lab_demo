"""
repo/travel_doc_repo.py
-----------------------
SQL for:
- user_travel_document
- travel_doc_type_rule

Features:
- List documents
- UPSERT document (update if same user_id + document_type + document_number)
- Deactivate document (soft delete)
- List document types for dropdown (dynamic from travel_doc_type_rule)
- Get doc type rules (expiry/name/country/issue required)
- Get primary active document (for booking passenger auto-fill)
"""

from typing import List, Dict, Any, Optional
from db.session import get_conn


# -----------------------------
# 1) Document Type Rules (Dropdown + Validation)
# -----------------------------
def list_doc_types(provider_code: str) -> List[str]:
    """
    Returns active document types for dropdown based on provider_code.
    Example: ['Passport','Visa','National_id']
    """
    sql = """
        SELECT document_type
        FROM travel_doc_type_rule
        WHERE provider_code = %s
          AND is_active = 'Y'
        ORDER BY document_type
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (provider_code,))
            rows = cur.fetchall() or []
            out: List[str] = []
            for r in rows:
                if isinstance(r, dict):
                    out.append(str(r.get("document_type")))
                else:
                    out.append(str(r[0]))
            return out


def get_travel_doc_rule(provider_code: str, document_type: str) -> Optional[Dict[str, Any]]:
    """
    Fetch rule flags for a document type.
    Returns dict like:
      {
        "expiry_required":"Y",
        "issue_date_required":"N",
        "issuing_country_required":"Y",
        "name_required":"N"
      }
    If not found, returns None (caller can decide defaults).
    """
    sql = """
        SELECT
          expiry_required,
          issue_date_required,
          issuing_country_required,
          name_required
        FROM travel_doc_type_rule
        WHERE provider_code = %s
          AND document_type = %s
          AND is_active = 'Y'
        LIMIT 1
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (provider_code, document_type))
            row = cur.fetchone()
            return row


# -----------------------------
# 2) User Travel Documents (CRUD)
# -----------------------------
def list_documents(user_id: int) -> List[Dict[str, Any]]:
    """
    List documents for UI cards.
    Ordered by primary first, then most recently updated.
    """
    sql = """
        SELECT document_id, user_id, document_type,
               document_number, issuing_country_iso2,
               first_name, last_name,
               issue_date, expiry_date,
               is_primary, is_active,
               created_at, updated_at
        FROM user_travel_document
        WHERE user_id = %s
        ORDER BY is_primary DESC, updated_at DESC
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            return cur.fetchall() or []


def upsert_document(
    user_id: int,
    document_type: str,
    document_number: str,
    issuing_country_iso2: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    issue_date: Optional[str],
    expiry_date: Optional[str],
    is_primary: int,
) -> int:
    """
    UPSERT behavior (required by your rule):
    - If same (user_id, document_type, document_number) exists => UPDATE it (reactivate)
    - Else INSERT new row

    Notes:
    - Uses UNIQUE uk1_user_travel_document (user_id, document_type, document_number)
    - Returns the document_id of inserted/updated row
    """

    sql_upsert = """
        INSERT INTO user_travel_document
        (
          user_id, document_type, document_number,
          issuing_country_iso2, first_name, last_name,
          issue_date, expiry_date,
          is_primary, is_active
        )
        VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
        ON DUPLICATE KEY UPDATE
          issuing_country_iso2 = VALUES(issuing_country_iso2),
          first_name      = VALUES(first_name),
          last_name       = VALUES(last_name),
          issue_date      = VALUES(issue_date),
          expiry_date     = VALUES(expiry_date),
          is_primary      = VALUES(is_primary),
          is_active       = 1,
          document_id     = LAST_INSERT_ID(document_id),
          updated_at      = CURRENT_TIMESTAMP
    """

    sql_unset_other_primaries = """
        UPDATE user_travel_document
        SET is_primary = 0
        WHERE user_id = %s
          AND document_id <> %s
          AND is_active = 1
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql_upsert,
                (
                    user_id,
                    document_type,
                    document_number,
                    issuing_country_iso2,
                    first_name,
                    last_name,
                    issue_date,
                    expiry_date,
                    is_primary,
                ),
            )

            doc_id = int(cur.lastrowid or 0)

            if is_primary == 1 and doc_id:
                cur.execute(sql_unset_other_primaries, (user_id, doc_id))

            conn.commit()
            return doc_id


def deactivate_document(user_id: int, document_id: int) -> int:
    """
    Soft-delete (keep record, mark inactive).
    Also remove primary flag so user doesn't end up with inactive primary.
    """
    sql = """
        UPDATE user_travel_document
        SET is_active = 0,
            is_primary = 0
        WHERE user_id = %s AND document_id = %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, document_id))
            conn.commit()
            return cur.rowcount


def get_document_by_id(user_id: int, document_id: int) -> Optional[Dict[str, Any]]:
    sql = """
        SELECT document_id, user_id, document_type,
               document_number, issuing_country_iso2,
               first_name, last_name,
               issue_date, expiry_date,
               is_primary, is_active,
               created_at, updated_at
        FROM user_travel_document
        WHERE user_id = %s AND document_id = %s
        LIMIT 1
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, document_id))
            return cur.fetchone()


def update_document_by_id(
    user_id: int,
    document_id: int,
    issuing_country_iso2: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    issue_date: Optional[str],
    expiry_date: Optional[str],
    is_primary: int,
) -> int:
    """
    Update existing document using document_id.
    Does NOT change document_type/document_number (identity stays same).
    Returns affected rows.
    """
    sql_update = """
        UPDATE user_travel_document
        SET issuing_country_iso2 = %s,
            first_name = %s,
            last_name = %s,
            issue_date = %s,
            expiry_date = %s,
            is_primary = %s,
            is_active = 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s AND document_id = %s
    """

    sql_unset_other_primaries = """
        UPDATE user_travel_document
        SET is_primary = 0
        WHERE user_id = %s
          AND document_id <> %s
          AND is_active = 1
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql_update,
                (
                    issuing_country_iso2,
                    first_name,
                    last_name,
                    issue_date,
                    expiry_date,
                    is_primary,
                    user_id,
                    document_id,
                ),
            )
            rows = cur.rowcount

            if is_primary == 1 and rows:
                cur.execute(sql_unset_other_primaries, (user_id, document_id))

            conn.commit()
            return rows


# -----------------------------
# 3) Primary Document Fetch (Booking Auto-Fill)
# -----------------------------
def get_primary_document(user_id: int, document_type: str = "Passport") -> Optional[Dict[str, Any]]:
    """
    Return user's active primary document of given type.

    STRICT RULES:
    - Must be is_primary=1 and is_active=1
    - No fallback to other docs
    - If not found -> return None (caller must block booking & show message)
    """
    sql = """
        SELECT document_id, user_id, document_type,
               document_number, issuing_country_iso2,
               first_name, last_name,
               issue_date, expiry_date,
               is_primary, is_active,
               created_at, updated_at
        FROM user_travel_document
        WHERE user_id = %s
          AND document_type = %s
          AND is_primary = 1
          AND is_active = 1
        ORDER BY updated_at DESC, created_at DESC
        LIMIT 1
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, document_type))
            return cur.fetchone()


def get_primary_passport(user_id: int) -> Optional[Dict[str, Any]]:
    """Convenience wrapper used by flight booking."""
    return get_primary_document(user_id=user_id, document_type="Passport")

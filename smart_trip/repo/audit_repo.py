"""
repo/audit_repo.py
------------------
Insert and read audit_event rows.

DDL (from your dump):
audit_event(
  session_id, category, event_type, status, severity,
  message, error_type, error_text, stacktrace_text, details_json
)
"""

from typing import Any, Dict, Optional
import json
from db.session import get_conn

ALLOWED_CATEGORY = {"SESSION","UI","VALIDATION","PROVIDER","DB","TOOL","ERROR"}
ALLOWED_STATUS   = {"SUCCESS","FAIL"}
ALLOWED_SEVERITY = {"INFO","WARN","ERROR"}


def _validate_audit_values(category: str, status: str, severity: str) -> None:
    c = (category or "").strip().upper()
    s = (status or "").strip().upper()
    v = (severity or "").strip().upper()

    if c not in ALLOWED_CATEGORY:
        raise ValueError(f"audit_event.category invalid: {category!r}. Allowed: {sorted(ALLOWED_CATEGORY)}")
    if s not in ALLOWED_STATUS:
        raise ValueError(f"audit_event.status invalid: {status!r}. Allowed: {sorted(ALLOWED_STATUS)}")
    if v not in ALLOWED_SEVERITY:
        raise ValueError(f"audit_event.severity invalid: {severity!r}. Allowed: {sorted(ALLOWED_SEVERITY)}")


def insert_audit_event(
    session_id: int,
    category: str,
    event_type: str,
    status: str,
    severity: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    error_type: Optional[str] = None,
    error_text: Optional[str] = None,
    stacktrace_text: Optional[str] = None,
) -> None:
    sql = """
        INSERT INTO audit_event
        (
          session_id, category, event_type, status, severity,
          message, error_type, error_text, stacktrace_text, details_json
        )
        VALUES
        (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    details_json = None
    if details is not None:
        details_json = json.dumps(details, default=str)

    with get_conn() as conn:
        _validate_audit_values(category, status, severity)

        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    session_id,
                    category.strip().upper(),
                    event_type,
                    status.strip().upper(),
                    severity.strip().upper(),
                    message[:500],
                    error_type,
                    error_text,
                    stacktrace_text,
                    details_json,
                ),
            )


def list_audit_event_types(session_id: Optional[int] = None) -> list[str]:
    sql = """
        SELECT DISTINCT event_type
        FROM audit_event
        WHERE (%s IS NULL OR session_id = %s)
          AND COALESCE(event_type, '') <> ''
        ORDER BY event_type
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (session_id, session_id))
            rows = cur.fetchall() or []
    return [str((r or {}).get('event_type') or '').strip() for r in rows if str((r or {}).get('event_type') or '').strip()]


def fetch_audit_events(
    *,
    session_id: Optional[int] = None,
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 200,
) -> list[dict]:
    safe_limit = max(1, min(int(limit or 200), 1000))
    sql = """
        SELECT session_id, category, event_type, status, severity,
               message, error_type, error_text, stacktrace_text, details_json,
               created_at
        FROM audit_event
        WHERE (%s IS NULL OR session_id = %s)
          AND (%s IS NULL OR event_type = %s)
          AND (%s IS NULL OR status = %s)
          AND (%s IS NULL OR category = %s)
        ORDER BY created_at DESC, event_id DESC
        LIMIT %s
    """
    bind = (
        session_id, session_id,
        event_type, event_type,
        status, status,
        category, category,
        safe_limit,
    )
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, bind)
            rows = cur.fetchall() or []
    for row in rows:
        raw = row.get('details_json')
        parsed = None
        if isinstance(raw, (dict, list)):
            parsed = raw
        elif raw:
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = raw
        row['details_json_parsed'] = parsed
        if parsed is None:
            row['details_json_text'] = ''
        elif isinstance(parsed, (dict, list)):
            row['details_json_text'] = json.dumps(parsed, indent=2, ensure_ascii=False, default=str)
        else:
            row['details_json_text'] = str(parsed)
    return rows

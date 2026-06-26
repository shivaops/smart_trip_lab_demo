# core/audit.py
"""
core/audit.py
-------------
Small wrapper to write audit events consistently.

LOCKED:
- Always log failures with full error text + stacktrace
- No silent failures
"""

from typing import Any, Dict, Optional
import traceback
from repo.audit_repo import insert_audit_event


def log_info(session_id: int, category: str, event_type: str, message: str, details: Optional[Dict[str, Any]] = None):
    insert_audit_event(
        session_id=session_id,
        category=category,
        event_type=event_type,
        status="SUCCESS",
        severity="INFO",
        message=message,
        details=details,
    )


def log_fail(session_id: int, category: str, event_type: str, message: str, err: Exception, details: Optional[Dict[str, Any]] = None):
    insert_audit_event(
        session_id=session_id,
        category=category,
        event_type=event_type,
        status="FAIL",
        severity="ERROR",
        message=message,
        details=details,
        error_type=type(err).__name__,
        error_text=str(err),
        stacktrace_text=traceback.format_exc(),
    )

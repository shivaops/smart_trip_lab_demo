"""
repo/provider_repo.py
---------------------
Read-only repository helpers for tt_agentic.llm_provider.

Phase 2B goal:
- Prepare a clean DB read path for LLM provider selection.
- Do NOT change UI, graph, or node logic yet.
- Keep this file safe to add even if nothing calls it today.

Table used:
  llm_provider

Important behavior:
- Prefer ACTIVE + DEFAULT provider first.
- If no default is marked, fall back to the first ACTIVE provider.
- Return None when no active provider exists.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from db.session import get_conn


SELECT_FIELDS = """
    llm_provider_id,
    provider_code,
    provider_name,
    provider_type,
    base_url,
    auth_type,
    api_key_env_var,
    model_name,
    temperature,
    max_tokens,
    is_active,
    is_default,
    notes,
    created_at
"""


def _normalize_provider_row(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Convert DB row into a stable Python dict.

    Why normalize:
    - makes boolean flags consistent
    - trims provider codes/names
    - gives later phases a predictable structure
    """
    if not row:
        return None

    return {
        "llm_provider_id": row.get("llm_provider_id"),
        "provider_code": (row.get("provider_code") or "").strip().upper(),
        "provider_name": (row.get("provider_name") or "").strip(),
        "provider_type": row.get("provider_type"),
        "base_url": row.get("base_url"),
        "auth_type": row.get("auth_type"),
        "api_key_env_var": row.get("api_key_env_var"),
        "model_name": (row.get("model_name") or "").strip(),
        "temperature": float(row.get("temperature") or 0),
        "max_tokens": int(row.get("max_tokens") or 0),
        "is_active": bool(row.get("is_active")),
        "is_default": bool(row.get("is_default")),
        "notes": row.get("notes"),
        "created_at": row.get("created_at"),
    }


def list_active_llm_providers() -> List[Dict[str, Any]]:
    """
    Return all ACTIVE providers, ordered so the default appears first.

    This is useful for future dropdown population.
    """
    sql = f"""
        SELECT {SELECT_FIELDS}
        FROM llm_provider
        WHERE is_active = 1
        ORDER BY is_default DESC, provider_name ASC, llm_provider_id ASC
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall() or []

    return [_normalize_provider_row(row) for row in rows if row]


def get_active_default_llm_provider() -> Optional[Dict[str, Any]]:
    """
    Return the active default provider.

    Fallback rule:
    - if no ACTIVE+DEFAULT row exists,
      return the first ACTIVE provider.
    - if no active provider exists, return None.
    """
    sql_default = f"""
        SELECT {SELECT_FIELDS}
        FROM llm_provider
        WHERE is_active = 1
          AND is_default = 1
        ORDER BY llm_provider_id ASC
        LIMIT 1
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_default)
            row = cur.fetchone()
            if row:
                return _normalize_provider_row(row)

            sql_fallback = f"""
                SELECT {SELECT_FIELDS}
                FROM llm_provider
                WHERE is_active = 1
                ORDER BY provider_name ASC, llm_provider_id ASC
                LIMIT 1
            """
            cur.execute(sql_fallback)
            row = cur.fetchone()
            return _normalize_provider_row(row)


def get_llm_provider_by_code(provider_code: str) -> Optional[Dict[str, Any]]:
    """
    Return one ACTIVE provider by provider_code.

    Example:
      get_llm_provider_by_code("GEMINI")
      get_llm_provider_by_code("OLLAMA")

    Returns None if:
    - code is blank
    - no active matching row exists
    """
    code = (provider_code or "").strip().upper()
    if not code:
        return None

    sql = f"""
        SELECT {SELECT_FIELDS}
        FROM llm_provider
        WHERE is_active = 1
          AND UPPER(provider_code) = %s
        ORDER BY is_default DESC, llm_provider_id ASC
        LIMIT 1
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (code,))
            row = cur.fetchone()
            return _normalize_provider_row(row)

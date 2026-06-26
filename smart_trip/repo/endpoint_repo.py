"""repo/endpoint_repo.py

Fetch provider endpoint connection details.

We keep this separate from cfg_repo:
- cfg_repo -> UI / request / response mapping rows
- endpoint_repo -> where to call (base_url + path + http_method)

NOTE:
Your historical DDLs sometimes used api_provider.website_url.
Newer code expects api_provider.base_url.
So we try base_url first, then website_url (compatibility for your current schema).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from db.session import get_conn


def get_endpoint_connection(endpoint_id: int) -> Dict[str, Any]:
    """Return dict with base_url, path, http_method, timeout_ms.

    Raises ValueError if endpoint_id not found.
    """

    # Attempt 1: api_provider.base_url
    sql1 = """
        SELECT
          p.base_url AS base_url,
          p.provider_name AS provider_name,
          p.provider_type AS provider_type,
          e.path AS path,
          e.http_method AS http_method,
          e.timeout_ms AS timeout_ms,
          e.endpoint_type AS endpoint_type,
          e.provider_code AS provider_code
        FROM api_provider_endpoint e
        JOIN api_provider p ON p.provider_code = e.provider_code
        WHERE e.endpoint_id = %s
        LIMIT 1
    """

    # Attempt 2: api_provider.website_url (older DDL)
    sql2 = """
        SELECT
          p.website_url AS base_url,
          p.provider_name AS provider_name,
          p.provider_type AS provider_type,
          e.path AS path,
          e.http_method AS http_method,
          e.timeout_ms AS timeout_ms,
          e.endpoint_type AS endpoint_type,
          e.provider_code AS provider_code
        FROM api_provider_endpoint e
        JOIN api_provider p ON p.provider_code = e.provider_code
        WHERE e.endpoint_id = %s
        LIMIT 1
    """

    row: Optional[Dict[str, Any]] = None
    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(sql1, (endpoint_id,))
                row = cur.fetchone()
            except Exception:
                # Most likely column base_url doesn't exist. Try website_url.
                cur.execute(sql2, (endpoint_id,))
                row = cur.fetchone()

    if not row:
        raise ValueError(f"Endpoint not found for endpoint_id={endpoint_id}")

    base_url = str(row.get("base_url") or "").strip()
    path = str(row.get("path") or "").strip()
    http_method = str(row.get("http_method") or "POST").strip().upper()
    timeout_ms = row.get("timeout_ms")

    if not base_url or not path:
        raise ValueError(
            f"Endpoint connection incomplete for endpoint_id={endpoint_id}: base_url/path missing"
        )

    return {
        "provider_code": row.get("provider_code"),
        "provider_name": row.get("provider_name"),
        "provider_type": row.get("provider_type"),
        "endpoint_type": row.get("endpoint_type"),
        "base_url": base_url,
        "path": path,
        "http_method": http_method,
        "timeout_ms": timeout_ms,
    }

# core/provider_client.py
"""
core/provider_client.py
-----------------------
HTTP call to provider endpoint (ARS/TTRS).

Uses:
- api_provider.base_url
- api_provider_endpoint.path
- api_provider_endpoint.http_method
- api_provider_endpoint.timeout_ms
"""

from typing import Dict, Any
# core/provider_client.py
import json
import datetime
import requests

from core.audit import log_fail, log_info

def _json_safe(obj):
    """
    Convert non-JSON types (datetime/date/Decimal, etc.) into JSON-safe values.
    This ensures requests.post(json=payload) never crashes.
    """
    if obj is None:
        return None

    # datetime/date -> ISO string
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat(sep=" ", timespec="seconds") if isinstance(obj, datetime.datetime) else obj.isoformat()

    # Decimal -> float (or str if you prefer)
    try:
        from decimal import Decimal
        if isinstance(obj, Decimal):
            return float(obj)
    except Exception:
        pass

    # bytes -> decode
    if isinstance(obj, (bytes, bytearray)):
        return obj.decode("utf-8", errors="replace")

    # dict/list -> recurse
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]

    return obj


def _provider_request(base_url: str, path: str, http_method: str, payload: dict, timeout_ms=None):
    url = f"{base_url}{path}"
    timeout_sec = (int(timeout_ms) / 1000.0) if timeout_ms else 15

    if (http_method or "").upper() != "POST":
        raise ValueError(f"Unsupported http_method={http_method}")

    safe_payload = _json_safe(payload)
    resp = requests.post(url, json=safe_payload, timeout=timeout_sec)

    if resp.status_code >= 400:
        body = (resp.text or "").strip()
        if len(body) > 1500:
            body = body[:1500] + " ...[truncated]"
        raise requests.exceptions.HTTPError(
            f"{resp.status_code} Provider Error for url={url}. Body={body}",
            response=resp,
        )

    return resp


def call_provider(base_url: str, path: str, http_method: str, payload: dict, timeout_ms=None):
    resp = _provider_request(base_url=base_url, path=path, http_method=http_method, payload=payload, timeout_ms=timeout_ms)
    return resp.json()


def call_provider_traced(
    *,
    session_id: int,
    base_url: str,
    path: str,
    http_method: str,
    payload: dict,
    timeout_ms=None,
    request_event_type: str,
    response_event_type: str,
    fail_event_type: str,
    request_message: str,
    response_message: str,
    fail_message: str,
    provider_details: dict | None = None,
    request_context: dict | None = None,
    response_context: dict | None = None,
):
    started_at = datetime.datetime.now(datetime.timezone.utc)
    provider_details = dict(provider_details or {})
    request_context = dict(request_context or {})
    response_context = dict(response_context or {})
    endpoint_url = f"{base_url}{path}"

    common = {
        **provider_details,
        "provider_endpoint": path,
        "provider_url": endpoint_url,
        "http_method": str(http_method or "POST").upper(),
        "timeout_ms": int(timeout_ms) if timeout_ms else None,
    }

    log_info(
        session_id=session_id,
        category="PROVIDER",
        event_type=request_event_type,
        message=request_message,
        details={
            **common,
            **request_context,
            "flow_direction": "TT_TO_ARS",
            "request_payload": _json_safe(payload),
        },
    )

    try:
        resp = _provider_request(base_url=base_url, path=path, http_method=http_method, payload=payload, timeout_ms=timeout_ms)
        resp_json = resp.json()
        latency_ms = int((datetime.datetime.now(datetime.timezone.utc) - started_at).total_seconds() * 1000)
        log_info(
            session_id=session_id,
            category="PROVIDER",
            event_type=response_event_type,
            message=response_message,
            details={
                **common,
                **response_context,
                "flow_direction": "ARS_TO_TT",
                "http_status": int(resp.status_code),
                "latency_ms": latency_ms,
                "response_payload": _json_safe(resp_json),
            },
        )
        return resp_json
    except Exception as err:
        latency_ms = int((datetime.datetime.now(datetime.timezone.utc) - started_at).total_seconds() * 1000)
        fail_details = {
            **common,
            **response_context,
            "flow_direction": "ARS_TO_TT",
            "latency_ms": latency_ms,
        }
        response = getattr(err, "response", None)
        if response is not None:
            fail_details["http_status"] = getattr(response, "status_code", None)
            body_text = (getattr(response, "text", None) or "").strip()
            if body_text:
                fail_details["response_body"] = body_text[:4000]
        log_fail(
            session_id=session_id,
            category="PROVIDER",
            event_type=fail_event_type,
            message=fail_message,
            err=err,
            details=fail_details,
        )
        raise

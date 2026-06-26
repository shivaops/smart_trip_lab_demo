from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Tuple

from repo.cfg_repo import build_search_form_fields
from app.llm.repositories.llm_cfg_repo import fetch_llm_field_cfg, fetch_llm_templates


ROUTE_KEY_BY_REQUEST_PATH = {
    "search.trip_type": "trip_type",
    "search.from_airport": "from_city",
    "search.to_airport": "to_city",
    "search.depart_date": "depart_date",
    "search.return_date": "return_date",
    "search.adults": "adults",
    "search.children": "children",
    "search.infants": "infants",
    "search.cabin_class": "cabin_class",
    "search.currency": "currency",
    "search.preferred_airline": "preferred_airline",
}


def _route_key_for_request_path(req_path: str) -> str | None:
    return ROUTE_KEY_BY_REQUEST_PATH.get(str(req_path or "").strip())


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _canon(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _normalize_text(value)).strip()


def _normalize_option_tuples(options: Any) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for opt in options or []:
        if isinstance(opt, (list, tuple)) and len(opt) >= 2:
            out.append((str(opt[0]), str(opt[1])))
        elif isinstance(opt, dict):
            value = str(opt.get("value") or opt.get("code") or "").strip()
            label = str(opt.get("label") or opt.get("name") or value).strip()
            if value or label:
                out.append((value or label, label or value))
        elif opt not in (None, ""):
            out.append((str(opt), str(opt)))
    return out


def _options_payload(options: List[Tuple[str, str]]) -> List[Dict[str, str]]:
    return [{"value": str(v), "label": str(l)} for v, l in options]


def _template_text(templates: Dict[str, Dict[str, Any]], key: str | None, fallback: str) -> str:
    if key and key in templates:
        txt = str(templates[key].get("template_text") or "").strip()
        if txt:
            return txt
    return fallback


def _render_template(template: str, **kwargs: Any) -> str:
    out = str(template or "")
    for k, v in kwargs.items():
        out = out.replace("{" + k + "}", "" if v is None else str(v))
    return out.strip()


def _choice_hint(field_label: str, route_key: str, templates: Dict[str, Dict[str, Any]], llm_cfg: Dict[str, Any] | None) -> str | None:
    parser_hint = str((llm_cfg or {}).get("parser_hint") or "").strip()
    if parser_hint:
        return parser_hint
    template = _template_text(templates, "OPTION_REPLY_HINT", "Reply with the exact value or select from the dropdown.")
    if route_key in ("depart_date", "return_date"):
        return "You can type a date like 2026-04-01 or 01-Apr-2026."
    return template


def _match_select_option(raw_value: Any, options: List[Tuple[str, str]] | None) -> str | None:
    text = _normalize_text(raw_value)
    if not text:
        return None
    options = options or []
    canon = _canon(text)
    compact = canon.replace(" ", "")
    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(options):
            return str(options[idx][0])

    synonyms = {
        "eco": "Economy",
        "economy": "Economy",
        "prem eco": "Premium Economy",
        "premium economy": "Premium Economy",
        "premiumeconomy": "Premium Economy",
        "biz": "Business",
        "business": "Business",
        "first": "First",
        "gf": "GF",
        "gulf air": "GF",
        "qr": "QR",
        "qatar": "QR",
        "qatar airways": "QR",
        "ek": "EK",
        "emirates": "EK",
        "ey": "EY",
        "etihad": "EY",
        "etihad airways": "EY",
        "ai": "AI",
        "air india": "AI",
        "inr": "INR",
        "usd": "USD",
        "bhd": "BHD",
    }
    wanted = synonyms.get(canon) or synonyms.get(compact)
    if wanted:
        for value, label in options:
            if _normalize_text(value) == _normalize_text(wanted) or _normalize_text(label) == _normalize_text(wanted):
                return str(value)

    exact_keys: Dict[str, str] = {}
    prefix_hits: List[str] = []
    for value, label in options:
        value_s = str(value)
        label_s = str(label)
        for key in {
            _normalize_text(value_s),
            _canon(value_s),
            _canon(value_s).replace(" ", ""),
            _normalize_text(label_s),
            _canon(label_s),
            _canon(label_s).replace(" ", ""),
        }:
            if key:
                exact_keys.setdefault(key, value_s)
        tokens = [t for t in (_canon(label_s) + " " + _canon(value_s)).split() if t]
        if len(canon) >= 2 and any(tok.startswith(canon) for tok in tokens):
            prefix_hits.append(value_s)

    if canon in exact_keys:
        return exact_keys[canon]
    if compact in exact_keys:
        return exact_keys[compact]
    unique = []
    seen = set()
    for item in prefix_hits:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    if len(unique) == 1:
        return unique[0]
    return None


def _parse_date(raw_value: Any) -> str | None:
    text = str(raw_value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%b-%y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _coerce_int(raw_value: Any) -> int | None:
    if raw_value in (None, ""):
        return None
    if isinstance(raw_value, int):
        return raw_value
    txt = str(raw_value).strip()
    return int(txt) if txt.isdigit() else None


def _field_required(field: Dict[str, Any], llm_cfg: Dict[str, Any] | None, trip_type: str) -> bool:
    req_path = str(field.get("request_json_path") or "").strip()
    if req_path == "search.return_date":
        mode = str((llm_cfg or {}).get("llm_required_mode") or "").upper()
        expr = str((llm_cfg or {}).get("required_condition_expr") or "").upper().replace(" ", "")
        if mode == "CONDITIONAL" and expr == "SEARCH.TRIP_TYPE=ROUND_TRIP":
            return trip_type == "ROUND_TRIP"
        return trip_type == "ROUND_TRIP"
    mode = str((llm_cfg or {}).get("llm_required_mode") or "").upper().strip()
    if mode == "ALWAYS":
        return True
    if mode == "NEVER":
        return False
    return bool(field.get("required"))


def _issue_descriptor(
    *,
    field: Dict[str, Any],
    llm_cfg: Dict[str, Any] | None,
    templates: Dict[str, Dict[str, Any]],
    issue_type: str,
    options: List[Tuple[str, str]] | None = None,
    invalid_value: Any = None,
) -> Dict[str, Any]:
    req_path = str(field.get("request_json_path") or "").strip()
    route_key = _route_key_for_request_path(req_path)
    field_label = str((llm_cfg or {}).get("llm_label") or field.get("label") or route_key or req_path)
    options = options or []
    option_rows = _options_payload(options)
    if issue_type == "INVALID":
        template_key = str((llm_cfg or {}).get("invalid_template_key") or "")
        fallback = "The value entered for {field_label} is not valid."
    else:
        template_key = str((llm_cfg or {}).get("missing_template_key") or "")
        fallback = "Please provide {field_label}."
    prompt = _render_template(
        _template_text(templates, template_key, fallback),
        field_label=field_label,
        invalid_value=invalid_value,
        selected_value=invalid_value,
    )
    ui_mode = "DROPDOWN" if option_rows else ("DATE" if route_key in ("depart_date", "return_date") else "TEXT")
    return {
        "cfg_id": int(field.get("cfg_id")),
        "label": field_label,
        "name": route_key,
        "request_json_path": req_path,
        "route_key": route_key,
        "data_type": field.get("data_type") or "STRING",
        "issue_type": issue_type,
        "invalid_value": invalid_value,
        "default_value": field.get("default_value"),
        "prompt": prompt,
        "hint": _choice_hint(field_label, str(route_key or ""), templates, llm_cfg),
        "ui_mode": ui_mode,
        "options": option_rows,
        "show_options_inline": False,
    }


def validate_llm_route_payload(route_payload: Dict[str, Any] | None, endpoint_id: int) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    route_payload = dict(route_payload or {})
    fields = build_search_form_fields(endpoint_id)
    llm_cfg_map = fetch_llm_field_cfg(endpoint_id)
    templates = fetch_llm_templates()

    trip_type = str(route_payload.get("trip_type") or "ONE_WAY").strip().upper() or "ONE_WAY"
    route_payload["trip_type"] = trip_type

    issues: List[Dict[str, Any]] = []
    for field in fields:
        req_path = str(field.get("request_json_path") or "").strip()
        route_key = _route_key_for_request_path(req_path)
        if not route_key:
            continue
        llm_cfg = llm_cfg_map.get(int(field.get("cfg_id")))
        required = _field_required(field, llm_cfg, trip_type)
        options = _normalize_option_tuples(field.get("options"))
        raw_value = route_payload.get(route_key)

        if req_path == "search.trip_type":
            continue
        if req_path in ("search.from_airport", "search.to_airport"):
            if raw_value in (None, ""):
                if required:
                    issues.append(_issue_descriptor(field=field, llm_cfg=llm_cfg, templates=templates, issue_type="MISSING", options=options))
                continue
            matched = _match_select_option(raw_value, options)
            if not matched:
                issues.append(_issue_descriptor(field=field, llm_cfg=llm_cfg, templates=templates, issue_type="INVALID", options=options, invalid_value=raw_value))
                route_payload[route_key] = None
                continue
            route_payload[route_key] = matched
            continue
        if req_path in ("search.cabin_class", "search.currency", "search.preferred_airline"):
            supplied = raw_value
            if req_path == "search.preferred_airline" and supplied in (None, ""):
                supplied = route_payload.get("search_preference")
            if supplied in (None, ""):
                if required:
                    issues.append(_issue_descriptor(field=field, llm_cfg=llm_cfg, templates=templates, issue_type="MISSING", options=options))
                continue
            matched = _match_select_option(supplied, options)
            if not matched:
                issues.append(_issue_descriptor(field=field, llm_cfg=llm_cfg, templates=templates, issue_type="INVALID", options=options, invalid_value=supplied))
                route_payload[route_key] = None
                continue
            route_payload[route_key] = matched
            if req_path == "search.preferred_airline":
                route_payload["search_preference"] = matched
            continue
        if req_path in ("search.depart_date", "search.return_date"):
            if req_path == "search.return_date" and trip_type != "ROUND_TRIP":
                route_payload[route_key] = None
                continue
            if raw_value in (None, ""):
                if required:
                    issues.append(_issue_descriptor(field=field, llm_cfg=llm_cfg, templates=templates, issue_type="MISSING"))
                continue
            parsed = _parse_date(raw_value)
            if not parsed:
                issues.append(_issue_descriptor(field=field, llm_cfg=llm_cfg, templates=templates, issue_type="INVALID", invalid_value=raw_value))
                route_payload[route_key] = None
                continue
            route_payload[route_key] = parsed
            continue
        if req_path in ("search.adults", "search.children", "search.infants"):
            if raw_value in (None, ""):
                if required:
                    issues.append(_issue_descriptor(field=field, llm_cfg=llm_cfg, templates=templates, issue_type="MISSING"))
                continue
            coerced = _coerce_int(raw_value)
            if coerced is None:
                issues.append(_issue_descriptor(field=field, llm_cfg=llm_cfg, templates=templates, issue_type="INVALID", invalid_value=raw_value))
                route_payload[route_key] = None
                continue
            route_payload[route_key] = coerced
            continue

    return issues, route_payload

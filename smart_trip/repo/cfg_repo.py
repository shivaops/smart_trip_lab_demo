# repo/cfg_repo.py
"""Configuration repository for api_provider_endpoint_parameter_cfg.

STRICT RULES:
- UI field names MUST be based on cfg_id only: name="cfg_{cfg_id}"
- No hardcoded field list in UI. Everything comes from cfg.
- LOV options come from cfg.lov_source_type + cfg.lov_source_sql.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from db.session import get_conn


def fetch_search_form_cfg(endpoint_id: int) -> List[Dict[str, Any]]:
    """Return cfg rows for SEARCH_FORM fields (REQUEST) in ui_order."""
    sql = """
        SELECT
            cfg_id,
            endpoint_id,
            object_type,
            parameter_role,
            is_active,
            ui_section,
            ui_control_type,
            ui_label,
            ui_placeholder,
            ui_help_text,
            ui_order,
            ui_visible,
            ui_readonly,
            is_required,
            data_type,
            default_value,
            lov_source_type,
            lov_source_sql,
            provider_parameter_name,
            request_json_path,
            send_if_empty,
            allowed_values_csv
        FROM api_provider_endpoint_parameter_cfg
        WHERE endpoint_id = %s
          AND parameter_role = 'REQUEST'
          AND ui_section = 'SEARCH_FORM'
          AND is_active = 'Y'
          AND (ui_visible = 'Y' OR UPPER(ui_control_type) = 'HIDDEN')
        ORDER BY COALESCE(ui_order, 999999), cfg_id
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (endpoint_id,))
            return list(cur.fetchall() or [])


def fetch_result_grid_cfg(endpoint_id: int) -> List[Dict[str, Any]]:
    """Return cfg rows for results grid (RESPONSE) in ui_order."""
    sql = """
        SELECT
            cfg_id,
            endpoint_id,
            object_type,
            parameter_role,
            is_active,
            ui_section,
            ui_control_type,
            ui_label,
            ui_help_text,
            ui_order,
            ui_visible,
            response_json_path,
            data_type
        FROM api_provider_endpoint_parameter_cfg
        WHERE endpoint_id = %s
          AND parameter_role = 'RESPONSE'
          AND ui_section = 'RESULT_GRID'
          AND is_active = 'Y'
          AND ui_visible = 'Y'
        ORDER BY COALESCE(ui_order, 999999), cfg_id
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (endpoint_id,))
            return list(cur.fetchall() or [])


def fetch_lov_options(cfg_row: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Return list of (value,label) for SELECT fields."""
    src = (cfg_row.get("lov_source_type") or "").upper().strip()

    if src == "STATIC":
        csv = str(cfg_row.get("allowed_values_csv") or "").strip()
        if not csv:
            return []
        items = [x.strip() for x in csv.split(",") if x.strip()]
        return [(x, x) for x in items]

    if src == "SQL":
        sql = str(cfg_row.get("lov_source_sql") or "").strip()
        if not sql:
            raise ValueError(f"LOV SQL missing for cfg_id={cfg_row.get('cfg_id')}")
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = list(cur.fetchall() or [])
        opts: List[Tuple[str, str]] = []
        for r in rows:
            keys = list(r.keys())
            if not keys:
                continue
            if "value" in r and "label" in r:
                opts.append((str(r["value"]), str(r["label"])))
            elif len(keys) >= 2:
                opts.append((str(r[keys[0]]), str(r[keys[1]])))
            else:
                v = str(r[keys[0]])
                opts.append((v, v))
        return opts

    if src == "API":
        raise ValueError(f"lov_source_type='API' not implemented in Step-1 (cfg_id={cfg_row.get('cfg_id')})")

    return []


def build_search_form_fields(endpoint_id: int) -> List[Dict[str, Any]]:
    cfg_rows = fetch_search_form_cfg(endpoint_id)
    fields: List[Dict[str, Any]] = []
    for r in cfg_rows:
        cfg_id = int(r["cfg_id"])
        control = (r.get("ui_control_type") or "TEXT").upper()
        field: Dict[str, Any] = {
            "cfg_id": cfg_id,
            "name": f"cfg_{cfg_id}",
            "label": r.get("ui_label") or f"CFG {cfg_id}",
            "placeholder": r.get("ui_placeholder") or "",
            "help_text": r.get("ui_help_text") or "",
            "control": control,
            "required": (r.get("is_required") or "N") == "Y",
            "readonly": (r.get("ui_readonly") or "N") == "Y",
            "data_type": r.get("data_type") or "STRING",
            "default_value": r.get("default_value"),
            "provider_parameter_name": r.get("provider_parameter_name"),
            "request_json_path": r.get("request_json_path"),
            "send_if_empty": (r.get("send_if_empty") or "N") == "Y",
        }
        if control == "SELECT":
            field["options"] = fetch_lov_options(r)
        fields.append(field)
    return fields


def build_result_grid_fields(endpoint_id: int) -> List[Dict[str, Any]]:
    cfg_rows = fetch_result_grid_cfg(endpoint_id)
    cols: List[Dict[str, Any]] = []
    for r in cfg_rows:
        cfg_id = int(r["cfg_id"])
        cols.append(
            {
                "cfg_id": cfg_id,
                "label": r.get("ui_label") or f"CFG {cfg_id}",
                "response_json_path": (r.get("response_json_path") or "").strip(),
                "data_type": r.get("data_type") or "STRING",
            }
        )
    return cols


def fetch_booking_form_cfg(endpoint_id: int) -> List[Dict[str, Any]]:
    # ✅ FIX: include HIDDEN rows even if ui_visible='N'
    sql = """
        SELECT *
        FROM api_provider_endpoint_parameter_cfg
        WHERE endpoint_id = %s
          AND parameter_role = 'REQUEST'
          AND ui_section = 'BOOK_FORM'
          AND is_active = 'Y'
          AND (ui_visible = 'Y' OR UPPER(ui_control_type) = 'HIDDEN')
        ORDER BY COALESCE(ui_order, 999999), cfg_id
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (endpoint_id,))
            return list(cur.fetchall() or [])


def build_booking_form_fields(endpoint_id: int) -> List[Dict[str, Any]]:
    rows = fetch_booking_form_cfg(endpoint_id)
    fields: List[Dict[str, Any]] = []
    for r in rows:
        cfg_id = int(r["cfg_id"])
        control = (r.get("ui_control_type") or "TEXT").upper()

        field: Dict[str, Any] = {
            "cfg_id": cfg_id,
            "name": f"cfg_{cfg_id}",
            "label": r.get("ui_label") or f"CFG {cfg_id}",
            "placeholder": r.get("ui_placeholder") or "",
            "help_text": r.get("ui_help_text") or "",
            "control": control,
            "required": (r.get("is_required") or "N") == "Y",
            "readonly": (r.get("ui_readonly") or "N") == "Y",
            "data_type": r.get("data_type") or "STRING",
            "default_value": r.get("default_value"),
            "request_json_path": (r.get("request_json_path") or "").strip(),
            "value_source_type": (r.get("value_source_type") or ""),
            "value_source_key": (r.get("value_source_key") or ""),
            "parameter_name": (r.get("provider_parameter_name") or r.get("parameter_name") or ""),
        }

        if control == "SELECT":
            field["options"] = fetch_lov_options(r)

        fields.append(field)

    return fields


def fetch_booking_confirm_cfg(endpoint_id: int) -> List[Dict[str, Any]]:
    sql = """
        SELECT *
        FROM api_provider_endpoint_parameter_cfg
        WHERE endpoint_id = %s
          AND parameter_role = 'RESPONSE'
          AND ui_section = 'BOOK_CONFIRM'
          AND is_active = 'Y'
          AND ui_visible = 'Y'
        ORDER BY COALESCE(ui_order, 999999), cfg_id
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (endpoint_id,))
            return list(cur.fetchall() or [])


def build_booking_confirm_fields(endpoint_id: int) -> List[Dict[str, Any]]:
    """UI-ready confirm fields (same idea as search/result builders)."""
    rows = fetch_booking_confirm_cfg(endpoint_id)
    out: List[Dict[str, Any]] = []
    for r in rows:
        cfg_id = int(r["cfg_id"])
        out.append(
            {
                "cfg_id": cfg_id,
                "label": r.get("ui_label") or f"CFG {cfg_id}",
                "response_json_path": (r.get("response_json_path") or "").strip(),
                "data_type": r.get("data_type") or "STRING",
                "ui_order": r.get("ui_order"),
            }
        )
    return out
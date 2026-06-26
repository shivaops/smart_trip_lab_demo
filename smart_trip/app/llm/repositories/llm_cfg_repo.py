from __future__ import annotations

from typing import Any, Dict

from db.session import get_conn


def fetch_llm_field_cfg(endpoint_id: int) -> Dict[int, Dict[str, Any]]:
    sql = """
        SELECT
            l.llm_cfg_id,
            l.cfg_id,
            l.is_active,
            l.llm_field_code,
            l.llm_label,
            l.llm_short_label,
            l.ask_in_chat,
            l.show_in_summary_card,
            l.show_in_system_card,
            l.show_in_user_card,
            l.show_in_trace,
            l.input_mode,
            l.correction_mode,
            l.option_source_type,
            l.option_source_value,
            l.llm_required_mode,
            l.required_condition_expr,
            l.visibility_condition_expr,
            l.normalization_rule,
            l.parser_hint,
            l.missing_template_key,
            l.invalid_template_key,
            l.selection_template_key,
            l.confirm_template_key,
            l.sort_order,
            l.developer_notes
        FROM api_provider_endpoint_parameter_llm_cfg l
        JOIN api_provider_endpoint_parameter_cfg p
          ON p.cfg_id = l.cfg_id
        WHERE p.endpoint_id = %s
          AND l.is_active = 'Y'
        ORDER BY COALESCE(l.sort_order, 999999), l.cfg_id
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (endpoint_id,))
            rows = list(cur.fetchall() or [])
    return {int(r["cfg_id"]): r for r in rows}


def fetch_llm_templates() -> Dict[str, Dict[str, Any]]:
    sql = """
        SELECT template_key, template_type, template_text
        FROM llm_chat_template_cfg
        WHERE is_active = 'Y'
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = list(cur.fetchall() or [])
    return {
        str(r["template_key"]): {
            "template_key": str(r["template_key"]),
            "template_type": str(r.get("template_type") or "").strip(),
            "template_text": str(r.get("template_text") or "").strip(),
        }
        for r in rows
    }

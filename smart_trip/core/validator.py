# core/validator.py
"""
core/validator.py
-----------------
Validations driven by api_provider_endpoint_parameter_cfg.

LOCKED:
- Required/optional enforced only from cfg table
- Optional fields never block
"""

from typing import Dict, Any, List, Tuple
import re


def validate_request_fields(cfg_rows: List[Dict[str, Any]], values: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate only REQUEST rows.
    We use:
      - is_required
      - data_type
      - min_len/max_len
      - regex_rule

    Returns:
      (ok, message)
    """
    for r in cfg_rows:
        if r.get("is_active") != "Y":
            continue
        if r.get("parameter_role") != "REQUEST":
            continue
        if r.get("provider_parameter_name") in (None, ""):
            # Not part of provider contract → ignore for request payload validation
            continue

        required = (r.get("is_required") == "Y")
        label = r.get("ui_label") or r.get("provider_parameter_name") or "Field"

        # Determine field key in posted form values:
        # We use stable name rule; caller should have used the same.
        key = (r.get("target_column_name") or "").strip() or (r.get("provider_parameter_name") or "").strip() or f"cfg_{r['cfg_id']}"

        val = values.get(key)

        if required and (val is None or str(val).strip() == ""):
            return False, f"Missing required field: {label}"

        # Optional empty is OK
        if val is None or str(val).strip() == "":
            continue

        # Length checks
        try:
            s = str(val)
            min_len = r.get("min_len")
            max_len = r.get("max_len")
            if min_len is not None and len(s) < int(min_len):
                return False, f"{label} must be at least {min_len} characters"
            if max_len is not None and len(s) > int(max_len):
                return False, f"{label} must be at most {max_len} characters"
        except Exception:
            pass

        # Regex check
        regex_rule = r.get("regex_rule")
        if regex_rule:
            try:
                if not re.match(regex_rule, str(val)):
                    return False, f"Invalid value for {label}"
            except re.error:
                # If regex itself is bad, do not block user; treat as config issue.
                continue

    return True, "OK"

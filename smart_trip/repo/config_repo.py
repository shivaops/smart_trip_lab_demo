"""DB queries for app_config."""

from db.session import get_conn


def get_config_value(config_key: str, default: str = "") -> str:
    sql = "SELECT config_value FROM app_config WHERE config_key = %s LIMIT 1"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (config_key,))
            row = cur.fetchone()
    if row and row.get("config_value") not in (None, ""):
        return str(row["config_value"])
    return default


def get_app_title() -> str:
    return get_config_value("COMPANY", "Smart Trip")

from db.session import get_conn
import json


def get_active_state(session_id: int, endpoint_id: int):
    sql = """
    SELECT state_json
    FROM llm_chat_session_state
    WHERE session_id=%s AND endpoint_id=%s AND is_active='Y'
    ORDER BY llm_state_id DESC
    LIMIT 1
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (session_id, endpoint_id))
            row = cur.fetchone()
            return json.loads(row[0]) if row else None


def insert_state(session_id, endpoint_id, llm_provider_id, state, last_user_message=None):
    sql = """
    INSERT INTO llm_chat_session_state
    (session_id, endpoint_id, llm_provider_id, state_status,
     awaiting_cfg_id, awaiting_reason, last_user_message, state_json)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (
                session_id,
                endpoint_id,
                llm_provider_id,
                state.get("conversation_status"),
                state.get("awaiting_cfg_id"),
                state.get("awaiting_reason"),
                last_user_message,
                json.dumps(state)
            ))
            conn.commit()
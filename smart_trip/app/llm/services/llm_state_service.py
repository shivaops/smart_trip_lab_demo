from app.llm.repositories.llm_state_repo import get_active_state, insert_state


def load_state(session_id: int, endpoint_id: int):
    return get_active_state(session_id, endpoint_id)


def save_state(session_id, endpoint_id, provider_id, state, user_msg=None):
    insert_state(session_id, endpoint_id, provider_id, state, user_msg)


def clear_state():
    # keep empty for now (future use)
    pass
from langgraph.graph import StateGraph, END

from app.llm.graph_state import LLMGraphState
from app.llm.nodes import (
    extract_intent_node,
    normalize_intent_node,
    decide_next_step_node,
)


def build_llm_graph():
    """
    Build Step-1 LLM graph for Smart Trip.

    Flow:
      START
        -> extract_intent_node
        -> normalize_intent_node
        -> decide_next_step_node
        -> END
    """
    builder = StateGraph(LLMGraphState)

    builder.add_node("extract_intent", extract_intent_node)
    builder.add_node("normalize_intent", normalize_intent_node)
    builder.add_node("decide_next_step", decide_next_step_node)

    builder.set_entry_point("extract_intent")
    builder.add_edge("extract_intent", "normalize_intent")
    builder.add_edge("normalize_intent", "decide_next_step")
    builder.add_edge("decide_next_step", END)

    return builder.compile()
from typing import Optional, List, Literal
from pydantic import BaseModel, Field

from app.llm.schemas import LLMIntent, NormalizedIntent


GraphStatus = Literal[
    "STARTED",
    "INTENT_EXTRACTED",
    "NORMALIZED",
    "NEEDS_CONFIRMATION",
    "READY_TO_ROUTE",
    "FAILED",
]


class LLMGraphState(BaseModel):
    user_input: str
    today_date: str

    user_id: Optional[int] = None
    session_id: Optional[int] = None

    # Existing (keep it)
    provider_code: Optional[str] = None

    # ✅ ADD THESE (REQUIRED FOR PHASE 4B/5B)
    llm_provider_code: Optional[str] = None
    llm_provider_name: Optional[str] = None

    llm_intent: Optional[LLMIntent] = None
    normalized_intent: Optional[NormalizedIntent] = None

    selected_date: Optional[str] = None
    route_payload: Optional[dict] = None

    status: GraphStatus = "STARTED"
    next_action: Optional[str] = None
    next_route: Optional[str] = None
    user_message: Optional[str] = None

    # Foundation for future persistent / checkpoint-based continuation.
    checkpoint_state: Optional[dict] = None

    errors: List[str] = Field(default_factory=list)
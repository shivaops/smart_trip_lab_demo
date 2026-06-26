from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# ------------------------------------------------------------
# Intent Types (extend later if needed)
# ------------------------------------------------------------
IntentType = Literal[
    "search_flights",
    "view_itinerary",
    "manage_booking",
    "pay_booking",
]


# ------------------------------------------------------------
# Clarification Option (for ambiguity handling)
# ------------------------------------------------------------
class ClarificationOption(BaseModel):
    label: str
    value: str


# ------------------------------------------------------------
# LLM Extracted Intent (RAW OUTPUT STRUCTURE)
# ------------------------------------------------------------
class LLMIntent(BaseModel):
    intent: IntentType

    trip_type: Optional[str] = None  # ONE_WAY / ROUND_TRIP

    from_city: Optional[str] = None
    to_city: Optional[str] = None

    # Raw + normalized dates
    depart_date_raw: Optional[str] = None
    depart_date: Optional[str] = None

    return_date_raw: Optional[str] = None
    return_date: Optional[str] = None

    # Traveller info
    adults: int = 1
    children: int = 0
    infants: int = 0

    # Preferences
    cabin_class: Optional[str] = None
    currency: Optional[str] = None
    meal_preference: Optional[str] = None
    preferred_airline: Optional[str] = None
    search_preference: Optional[str] = None

    # Validation / completeness
    missing_fields: List[str] = Field(default_factory=list)


# ------------------------------------------------------------
# Normalized Intent (AFTER BACKEND PROCESSING)
# ------------------------------------------------------------
class NormalizedIntent(BaseModel):
    intent: IntentType

    trip_type: Optional[str] = None

    from_city: Optional[str] = None
    to_city: Optional[str] = None

    depart_date_raw: Optional[str] = None
    depart_date: Optional[str] = None

    return_date_raw: Optional[str] = None
    return_date: Optional[str] = None

    adults: int = 1
    children: int = 0
    infants: int = 0

    cabin_class: Optional[str] = None
    currency: Optional[str] = None
    meal_preference: Optional[str] = None
    preferred_airline: Optional[str] = None
    search_preference: Optional[str] = None

    missing_fields: List[str] = Field(default_factory=list)

    # --------------------------------------------------------
    # Ambiguity handling (CRITICAL FEATURE)
    # --------------------------------------------------------
    needs_confirmation: bool = False
    clarification_type: Optional[str] = None

    clarification_options: List[ClarificationOption] = Field(default_factory=list)
    
# ------------------------------------------------------------
# Step-2 confirmation request/response helper models
# ------------------------------------------------------------
class DateConfirmationSelection(BaseModel):
    selected_date: str


class SearchRoutePayload(BaseModel):
    trip_type: Optional[str] = None
    from_city: Optional[str] = None
    to_city: Optional[str] = None
    depart_date: Optional[str] = None
    return_date: Optional[str] = None
    adults: int = 1
    children: int = 0
    infants: int = 0
    cabin_class: Optional[str] = None
    currency: Optional[str] = None
    meal_preference: Optional[str] = None
    preferred_airline: Optional[str] = None
    search_preference: Optional[str] = None    
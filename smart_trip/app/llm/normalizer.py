from datetime import datetime, timedelta
from typing import Optional, List

from app.llm.schemas import LLMIntent, NormalizedIntent, ClarificationOption


WEEKDAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


AMBIGUOUS_RELATIVE_DATE_PHRASES = {
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "next monday",
    "next tuesday",
    "next wednesday",
    "next thursday",
    "next friday",
    "next saturday",
    "next sunday",
    "next week",
}


def parse_iso_date(date_str: str) -> datetime.date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def format_human_date(date_str: str) -> str:
    dt = parse_iso_date(date_str)
    return dt.strftime("%A, %Y-%m-%d")


def normalize_simple_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    v = value.strip().lower()

    meal_map = {
        "non-veg": "NON_VEG",
        "non veg": "NON_VEG",
        "veg": "VEG",
        "vegetarian": "VEG",
        "jain": "JAIN",
    }

    search_pref_map = {
        "cheapest": "CHEAPEST",
        "lowest": "CHEAPEST",
        "lowest fare": "CHEAPEST",
        "lowest price": "CHEAPEST",
        "fastest": "FASTEST",
        "shortest": "FASTEST",
    }

    cabin_map = {
        "economy": "Economy",
        "premium economy": "Premium Economy",
        "business": "Business",
        "first": "First",
    }

    if v in meal_map:
        return meal_map[v]

    if v in search_pref_map:
        return search_pref_map[v]

    if v in cabin_map:
        return cabin_map[v]

    return value


def parse_explicit_date(date_str: Optional[str]) -> Optional[str]:
    if not date_str:
        return None

    raw = date_str.strip()

    formats = [
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue

    return None


def next_weekday_date(base_date, target_weekday: int) -> str:
    current_weekday = base_date.weekday()
    days_ahead = (target_weekday - current_weekday) % 7
    if days_ahead == 0:
        days_ahead = 7
    return (base_date + timedelta(days=days_ahead)).isoformat()


def next_weekday_in_following_week(base_date, target_weekday: int) -> str:
    current_weekday = base_date.weekday()
    days_ahead = (target_weekday - current_weekday) % 7

    if days_ahead == 0:
        days_ahead = 7
    else:
        days_ahead += 7

    return (base_date + timedelta(days=days_ahead)).isoformat()


def resolve_relative_date(raw_value: Optional[str], today_date) -> Optional[str]:
    if not raw_value:
        return None

    text = raw_value.strip().lower()

    if text == "tomorrow":
        return (today_date + timedelta(days=1)).isoformat()

    if text == "day after tomorrow":
        return (today_date + timedelta(days=2)).isoformat()

    if text == "next week":
        return (today_date + timedelta(days=7)).isoformat()

    if text.startswith("next "):
        tail = text.replace("next ", "", 1).strip()
        if tail in WEEKDAY_MAP:
            return next_weekday_in_following_week(today_date, WEEKDAY_MAP[tail])

    if text in WEEKDAY_MAP:
        return next_weekday_date(today_date, WEEKDAY_MAP[text])

    return None


def build_ambiguity_options(raw_value: Optional[str], today_date) -> List[ClarificationOption]:
    if not raw_value:
        return []

    text = raw_value.strip().lower()
    options: List[ClarificationOption] = []

    if text == "next week":
        option_1 = (today_date + timedelta(days=7)).isoformat()
        option_2 = (today_date + timedelta(days=14)).isoformat()
        return [
            ClarificationOption(label=format_human_date(option_1), value=option_1),
            ClarificationOption(label=format_human_date(option_2), value=option_2),
        ]

    if text.startswith("next "):
        tail = text.replace("next ", "", 1).strip()
        if tail in WEEKDAY_MAP:
            target = WEEKDAY_MAP[tail]

            # First possible meaning:
            # nearest upcoming weekday
            option_1 = next_weekday_date(today_date, target)

            # Second possible meaning:
            # same weekday one more week after option_1
            option_1_date = parse_iso_date(option_1)
            option_2 = (option_1_date + timedelta(days=7)).isoformat()

            return [
                ClarificationOption(label=format_human_date(option_1), value=option_1),
                ClarificationOption(label=format_human_date(option_2), value=option_2),
            ]

    if text in WEEKDAY_MAP:
        target = WEEKDAY_MAP[text]
        option_1 = next_weekday_date(today_date, target)
        option_2 = next_weekday_in_following_week(today_date, target)
        return [
            ClarificationOption(label=format_human_date(option_1), value=option_1),
            ClarificationOption(label=format_human_date(option_2), value=option_2),
        ]

    return options


def is_ambiguous_relative_date(raw_value: Optional[str]) -> bool:
    if not raw_value:
        return False
    return raw_value.strip().lower() in AMBIGUOUS_RELATIVE_DATE_PHRASES


def normalize_intent(intent: LLMIntent, today_date_str: str) -> NormalizedIntent:
    today_date = parse_iso_date(today_date_str)

    data = intent.model_dump()

    # Normalize explicit dates first
    if not data.get("depart_date"):
        data["depart_date"] = parse_explicit_date(data.get("depart_date_raw"))
    else:
        data["depart_date"] = parse_explicit_date(data.get("depart_date")) or data.get("depart_date")

    if not data.get("return_date"):
        data["return_date"] = parse_explicit_date(data.get("return_date_raw"))
    else:
        data["return_date"] = parse_explicit_date(data.get("return_date")) or data.get("return_date")

    # Resolve relative departure date only after explicit-date parsing
    if not data.get("depart_date") and data.get("depart_date_raw"):
        data["depart_date"] = resolve_relative_date(data.get("depart_date_raw"), today_date)

    # Normalize small values
    data["meal_preference"] = normalize_simple_value(data.get("meal_preference"))
    data["preferred_airline"] = normalize_simple_value(data.get("preferred_airline"))
    data["search_preference"] = normalize_simple_value(data.get("search_preference"))
    data["cabin_class"] = normalize_simple_value(data.get("cabin_class"))

    # Ambiguity detection
    needs_confirmation = False
    clarification_type = None
    clarification_options: List[ClarificationOption] = []

    if is_ambiguous_relative_date(data.get("depart_date_raw")):
        needs_confirmation = True
        clarification_type = "AMBIGUOUS_RELATIVE_DATE"
        clarification_options = build_ambiguity_options(data.get("depart_date_raw"), today_date)

    # Required-field validation
    missing_fields = list(data.get("missing_fields") or [])

    if not data.get("from_city"):
        missing_fields.append("from_city")

    if not data.get("to_city"):
        missing_fields.append("to_city")

    # User-facing flow should care about the resolved date field, not *_raw helper fields.
    if not data.get("depart_date"):
        missing_fields.append("depart_date")

    if data.get("trip_type") == "ROUND_TRIP" and not data.get("return_date"):
        missing_fields.append("return_date")

    # Remove duplicates preserving order and hide internal *_raw fields from UI / step decisions.
    seen = set()
    cleaned_missing = []
    for item in missing_fields:
        item = str(item or "").strip()
        if not item or item.endswith("_raw"):
            continue
        if item not in seen:
            seen.add(item)
            cleaned_missing.append(item)

    data.pop("missing_fields", None)

    return NormalizedIntent(
        **data,
        missing_fields=cleaned_missing,
        needs_confirmation=needs_confirmation,
        clarification_type=clarification_type,
        clarification_options=clarification_options,
    )
from app.llm.graph_state import LLMGraphState
from app.llm.intent_service import extract_intent
from app.llm.normalizer import normalize_intent


def extract_intent_node(state: LLMGraphState) -> LLMGraphState:
    """
    Step-1:
    Call LLM and extract raw structured intent.
    """
    try:
        selected_provider_code = state.llm_provider_code or state.provider_code
        llm_intent = extract_intent(
            user_input=state.user_input,
            today_date=state.today_date,
            provider_code=selected_provider_code,
        )
        state.provider_code = selected_provider_code
        state.llm_provider_code = selected_provider_code

        state.llm_intent = llm_intent
        state.status = "INTENT_EXTRACTED"
        return state

    except Exception as exc:
        state.status = "FAILED"
        state.errors.append(f"extract_intent_node failed: {str(exc)}")
        state.user_message = "I could not understand your travel request right now."
        return state


def normalize_intent_node(state: LLMGraphState) -> LLMGraphState:
    """
    Step-2:
    Normalize LLM output into safer backend-ready intent.
    """
    try:
        if state.llm_intent is None:
            state.status = "FAILED"
            state.errors.append("normalize_intent_node failed: llm_intent is missing")
            state.user_message = "I could not continue because no extracted intent was available."
            return state

        normalized = normalize_intent(
            intent=state.llm_intent,
            today_date_str=state.today_date,
        )

        state.normalized_intent = normalized
        state.status = "NORMALIZED"
        return state

    except Exception as exc:
        state.status = "FAILED"
        state.errors.append(f"normalize_intent_node failed: {str(exc)}")
        state.user_message = "I could not normalize your travel request."
        return state


def decide_next_step_node(state: LLMGraphState) -> LLMGraphState:
    """
    Step-3:
    Decide whether to:
    - ask for confirmation
    - ask for missing fields
    - route to search flow
    """
    try:
        if state.normalized_intent is None:
            state.status = "FAILED"
            state.errors.append("decide_next_step_node failed: normalized_intent is missing")
            state.user_message = "I could not decide the next step for your request."
            return state

        ni = state.normalized_intent

        if ni.needs_confirmation:
            state.status = "NEEDS_CONFIRMATION"
            state.next_action = "ASK_DATE_CONFIRMATION"

            lines = [
                f'I found an ambiguous travel date in your request: "{ni.depart_date_raw}".',
                "Please confirm which date you want:",
            ]

            for idx, option in enumerate(ni.clarification_options, start=1):
                lines.append(f"{idx}. {option.label}")

            state.user_message = "\n".join(lines)
            return state

        if ni.missing_fields:
            state.status = "NEEDS_CONFIRMATION"
            state.next_action = "ASK_MISSING_FIELDS"
            state.user_message = (
                "I need a few more details before I can continue: "
                + ", ".join(ni.missing_fields)
            )
            return state

        if ni.intent == "search_flights":
            state.status = "READY_TO_ROUTE"
            state.next_action = "ROUTE_TO_SEARCH"
            state.next_route = "/portal/flight/search"
            state.user_message = "I’ve understood your request. Here are the details for your trip:"
            return state

        if ni.intent == "view_itinerary":
            state.status = "READY_TO_ROUTE"
            state.next_action = "ROUTE_TO_ITINERARY"
            state.next_route = "/portal/itinerary"
            state.user_message = "I’ve understood your request. I’m ready to look up your itinerary details."
            return state

        if ni.intent == "manage_booking":
            state.status = "READY_TO_ROUTE"
            state.next_action = "ROUTE_TO_MANAGE_BOOKING"
            state.next_route = "/portal/manage-booking"
            state.user_message = "I’ve understood your request. I’m ready to help with your booking."
            return state

        if ni.intent == "pay_booking":
            state.status = "READY_TO_ROUTE"
            state.next_action = "ROUTE_TO_PAYMENT"
            state.next_route = "/portal/payment"
            state.user_message = "Your request is understood and ready for payment processing."
            return state

        state.status = "FAILED"
        state.errors.append(f"Unsupported intent: {ni.intent}")
        state.user_message = "I understood your request, but I cannot route it yet."
        return state

    except Exception as exc:
        state.status = "FAILED"
        state.errors.append(f"decide_next_step_node failed: {str(exc)}")
        state.user_message = "I could not decide what to do next."
        return state


def apply_date_confirmation_node(state: LLMGraphState) -> LLMGraphState:
    """
    Step-2:
    Apply user-selected confirmed date into normalized intent.
    """
    try:
        if state.normalized_intent is None:
            state.status = "FAILED"
            state.errors.append("apply_date_confirmation_node failed: normalized_intent is missing")
            state.user_message = "I could not apply your date confirmation."
            return state

        if not state.selected_date:
            state.status = "FAILED"
            state.errors.append("apply_date_confirmation_node failed: selected_date is missing")
            state.user_message = "No confirmed date was provided."
            return state

        ni = state.normalized_intent
        allowed_values = [opt.value for opt in ni.clarification_options]

        if state.selected_date not in allowed_values:
            state.status = "FAILED"
            state.errors.append(
                f"apply_date_confirmation_node failed: selected_date '{state.selected_date}' is not in allowed options"
            )
            state.user_message = "The selected date is not one of the valid clarification options."
            return state

        ni.depart_date = state.selected_date
        ni.needs_confirmation = False
        ni.clarification_type = None
        ni.clarification_options = []

        state.normalized_intent = ni
        state.status = "NORMALIZED"
        state.user_message = f"Confirmed departure date: {state.selected_date}"
        return state

    except Exception as exc:
        state.status = "FAILED"
        state.errors.append(f"apply_date_confirmation_node failed: {str(exc)}")
        state.user_message = "I could not apply the selected date."
        return state


def build_search_route_payload_node(state: LLMGraphState) -> LLMGraphState:
    """
    Step-2:
    Build safe handoff payload for Smart Trip search flow.
    """
    try:
        if state.normalized_intent is None:
            state.status = "FAILED"
            state.errors.append("build_search_route_payload_node failed: normalized_intent is missing")
            state.user_message = "I could not prepare the search handoff."
            return state

        ni = state.normalized_intent

        if ni.missing_fields:
            state.status = "NEEDS_CONFIRMATION"
            state.next_action = "ASK_MISSING_FIELDS"
            state.user_message = (
                "I still need a few more details before I can continue: "
                + ", ".join(ni.missing_fields)
            )
            return state

        if ni.needs_confirmation:
            state.status = "NEEDS_CONFIRMATION"
            state.next_action = "ASK_DATE_CONFIRMATION"
            state.user_message = "A date confirmation is still required before search can continue."
            return state

        route_payload = {
            "trip_type": ni.trip_type,
            "from_city": ni.from_city,
            "to_city": ni.to_city,
            "depart_date": ni.depart_date,
            "return_date": ni.return_date,
            "adults": ni.adults,
            "children": ni.children,
            "infants": ni.infants,
            "cabin_class": ni.cabin_class,
            "currency": ni.currency,
            "meal_preference": ni.meal_preference,
            "search_preference": ni.search_preference,
        }

        state.route_payload = route_payload
        state.status = "READY_TO_ROUTE"
        state.next_action = "ROUTE_TO_SEARCH"
        state.next_route = "/portal/flight/search"
        state.user_message = "Your date is confirmed and the request is ready for flight search."
        return state

    except Exception as exc:
        state.status = "FAILED"
        state.errors.append(f"build_search_route_payload_node failed: {str(exc)}")
        state.user_message = "I could not prepare your search request."
        return state

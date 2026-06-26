import json
from typing import Optional
from datetime import date
from app.llm.schemas import LLMIntent
from core.llm_client import LLMClientError, generate_text


DEFAULT_TODAY_DATE = date.today().isoformat()


def build_intent_prompt(user_input: str, today_date: str) -> str:
    return f"""
You are an airline travel assistant.

Your job is to extract structured flight-related intent information from the user request.

Rules:
1. Output ONLY valid JSON
2. Do NOT add explanation
3. Do NOT add markdown
4. Do NOT guess airport codes
5. Keep city names as user-friendly names for now
6. If a value is missing, use null
7. If trip looks like return journey, set trip_type as ROUND_TRIP, otherwise ONE_WAY
8. If user says total travellers but does not split adult/child/infant, put all in adults for now
9. Today date is {today_date}
10. If user provides relative date (like "next Friday", "tomorrow"), then:
    - set depart_date = null
    - store original value in depart_date_raw
11. NEVER convert relative date into actual date
12. Only populate depart_date if user gives full explicit date
13. Convert clearly explicit dates like 20-apr-2026 into YYYY-MM-DD
14. Preserve important search intent words like cheapest / fastest
15. Extract preferred airline separately when the user says preferred airline / airline preference / only <airline> flights
16. Do NOT put cheapest / cheap / lowest fare / budget into preferred_airline; keep those in search_preference
17. Return cabin_class as a clean value only, for example Economy or Business, not "class economy" or "cabin business"
18. Understand compact punctuation such as "INR.adult 2" or "business.preferred airline Air India"
19. Use exactly this JSON shape

Return JSON in exactly this shape:

{{
  "intent": "search_flights",
  "trip_type": null,
  "from_city": null,
  "to_city": null,
  "depart_date_raw": null,
  "depart_date": null,
  "return_date_raw": null,
  "return_date": null,
  "adults": 1,
  "children": 0,
  "infants": 0,
  "cabin_class": null,
  "currency": null,
  "meal_preference": null,
  "preferred_airline": null,
  "search_preference": null,
  "missing_fields": []
}}

User request:
{user_input}
""".strip()


def extract_intent_raw(
    user_input: str,
    today_date: str = DEFAULT_TODAY_DATE,
    provider_code: Optional[str] = None,
    model_name: Optional[str] = None,
) -> str:
    prompt = build_intent_prompt(user_input=user_input, today_date=today_date)
    response = generate_text(
        prompt=prompt,
        provider_code=provider_code,
    )
    text = str(response.text or "").strip()
    if not text:
        raise LLMClientError("LLM returned an empty response.")
    return _extract_json_text(text)


def extract_intent(
    user_input: str,
    today_date: str = DEFAULT_TODAY_DATE,
    provider_code: Optional[str] = None,
    model_name: Optional[str] = None,
) -> LLMIntent:
    raw_text = extract_intent_raw(
        user_input=user_input,
        today_date=today_date,
        provider_code=provider_code,
        model_name=model_name,
    )

    payload = json.loads(raw_text)
    payload = _coerce_llm_scalar_values(payload)
    return LLMIntent(**payload)


def _coerce_llm_scalar_values(payload: dict) -> dict:
    """Make LLM JSON tolerant before Pydantic validation.

    Some local models may return a list for fields like meal_preference,
    for example ["dinner"]. The schema expects a string/null, so normalize
    list values to a comma-separated string instead of failing the whole flow.
    """
    if not isinstance(payload, dict):
        return payload
    scalar_keys = [
        "trip_type", "from_city", "to_city", "depart_date_raw", "depart_date",
        "return_date_raw", "return_date", "cabin_class", "currency",
        "meal_preference", "preferred_airline", "search_preference",
    ]
    for key in scalar_keys:
        value = payload.get(key)
        if isinstance(value, list):
            cleaned = [str(item).strip() for item in value if str(item or "").strip()]
            payload[key] = ", ".join(cleaned) if cleaned else None
        elif isinstance(value, dict):
            payload[key] = json.dumps(value, ensure_ascii=False)
    return payload


def _extract_json_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = cleaned[first_brace:last_brace + 1].strip()
        if candidate:
            return candidate
    return cleaned

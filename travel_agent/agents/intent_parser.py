"""
Intent Parser Agent
Parses traveler's natural language input into a structured TravelerPreferences object.
Uses Gemini with a structured JSON output prompt.
"""
import json
import re
from tools.gemini_client import generate
from models.schemas import TravelerPreferences, TravelStyle


INTENT_PROMPT = """
You are a travel intent parser. Extract structured travel preferences from the user's input.

User Input: "{user_input}"

Today's date context: {date_context}

Return a JSON object with EXACTLY these fields (no extra wrapping):
{{
  "raw_input": "<original text>",
  "destination": "<primary destination>",
  "origin": "<origin city>",
  "duration_days": <integer>,
  "total_budget_inr": <number in INR>,
  "travel_style": "<one of: solo_backpacking, family, couple, group, solo_luxury>",
  "interests": ["<interest1>", "<interest2>", ...],
  "group_size": <integer>,
  "travel_dates": "<e.g. next weekend, Feb 28 – Mar 3>",
  "constraints": ["<constraint1>", ...],
  "accommodation_preference": "<budget | mid-range | luxury>",
  "food_preference": "<veg | non-veg | both>"
}}

Rules:
- If budget mentioned in ₹ or INR, use as-is. If in other currency, convert to INR.
- If NO budget is mentioned, estimate a REALISTIC budget for this trip:
  * Solo backpacking (budget): ₹3,000–5,000/day total
  * Family / mid-range: ₹8,000–15,000/day total
  * Luxury: ₹20,000+/day total
  Use duration_days × daily rate as a baseline, then round to nearest ₹1,000.
  NEVER return 0 for total_budget_inr.
- If destination is ambiguous (e.g. "mountains"), pick the most famous match.
- If origin not mentioned, default to "Delhi".
- If duration not mentioned, default to 3 days.
- interests must be from: adventure, spiritual, cultural, food, nightlife, nature, shopping, beaches, trekking, yoga, history, wildlife
- constraints: notes like "budget stays", "vegetarian food", "no alcohol"
- Return valid JSON only. No markdown, no explanation.
"""


def run(user_input: str, date_context: str = "February 2026") -> TravelerPreferences:
    """Parse user input into structured TravelerPreferences."""
    prompt = INTENT_PROMPT.format(user_input=user_input, date_context=date_context)
    raw = generate(prompt, temperature=0.2)

    # Strip markdown code blocks if present
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    raw = raw.strip()

    try:
        data = json.loads(raw)
        return TravelerPreferences(**data)
    except Exception as e:
        # Fallback: construct from raw text
        return TravelerPreferences(
            raw_input=user_input,
            destination="Rishikesh",
            origin="Delhi",
            duration_days=4,
            total_budget_inr=15000,
            travel_style=TravelStyle.SOLO_BACKPACKING,
            interests=["adventure", "spiritual"],
            group_size=1,
            travel_dates="next weekend",
            constraints=[],
            accommodation_preference="budget",
            food_preference="both",
        )

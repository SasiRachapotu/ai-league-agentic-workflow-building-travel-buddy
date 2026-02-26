"""
Resilience Agent — "What Could Go Wrong?"
Proactively generates 2-3 risk scenarios and concrete fallback plans
for the finalized itinerary. Displayed as a "Plan B" section in the UI.
"""
import json
import re
from tools.openai_client import generate
from models.schemas import ItineraryPlan


RESILIENCE_PROMPT = """
You are a travel risk analyst. Given a confirmed trip itinerary, identify the top 3 things
that could realistically go wrong and provide actionable fallback plans.

Trip:
- Destination: {destination}
- Duration: {duration_days} days
- Total Budget: ₹{budget}
- Transport: {transport}
- Hotel: {hotel}
- Key Activities: {activities}
- Travel style: {style}

Return a JSON array of exactly 3 risk scenarios:
[
  {{
    "risk": "<short title of what could go wrong>",
    "likelihood": "<Low | Medium | High>",
    "description": "<1-2 sentences explaining the scenario>",
    "fallback_action": "<specific, actionable alternative — what to do instead>",
    "fallback_url": "<real booking URL for the alternative, e.g. MakeMyTrip, Goibibo, Thrillophilia>",
    "budget_impact_inr": <0 or positive number — extra cost if fallback is used>
  }}
]

Good risk examples:
- Hotel overbooked on arrival
- Main activity (e.g. rafting) shut due to weather/season
- Train cancelled or heavily delayed
- Budget overshoot due to unexpected expenses

Rules:
- Risks must be realistic and specific to this trip (not generic)
- Fallback actions must name a specific alternative (hotel, activity, route)
- Fallback URLs must be real websites (IRCTC, MakeMyTrip, Goibibo, Thrillophilia, Zostel, etc.)
- Return valid JSON array ONLY. No markdown.
"""


def run(itinerary: ItineraryPlan) -> list[dict]:
    """
    Generate 3 contingency plans for the finalized itinerary.
    Returns list of dicts with: risk, likelihood, description, fallback_action, fallback_url, budget_impact_inr
    """
    prefs = itinerary.preferences
    transport_name = itinerary.transport_booking.name if itinerary.transport_booking else "Train"
    hotel_name = itinerary.hotel_booking.name if itinerary.hotel_booking else "Booked hotel"
    activity_names = ", ".join([a.name for a in itinerary.activity_bookings[:4]]) if itinerary.activity_bookings else "Sightseeing"

    prompt = RESILIENCE_PROMPT.format(
        destination=prefs.destination,
        duration_days=prefs.duration_days,
        budget=int(prefs.total_budget_inr),
        transport=transport_name,
        hotel=hotel_name,
        activities=activity_names,
        style=prefs.travel_style.value,
    )

    raw = generate(prompt, temperature=0.5)
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)

    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        raw = match.group(0)

    try:
        plans = json.loads(raw)
        # Ensure required fields exist
        for p in plans:
            p.setdefault("budget_impact_inr", 0)
            p.setdefault("fallback_url", "https://www.makemytrip.com")
        return plans
    except Exception:
        dest = prefs.destination
        dest_slug = dest.lower().replace(" ", "-")
        return [
            {
                "risk": f"Hotel overbooked on arrival",
                "likelihood": "Low",
                "description": f"Your booked stay in {dest} may show no available rooms due to overbooking, especially during peak season.",
                "fallback_action": f"Book an alternate hostel or guesthouse in {dest} via Goibibo or Zostel — search for same-day availability.",
                "fallback_url": f"https://www.goibibo.com/hotels/{dest_slug}/",
                "budget_impact_inr": 500,
            },
            {
                "risk": "Key activity cancelled due to weather",
                "likelihood": "Medium",
                "description": f"Outdoor adventure activities in {dest} (rafting, trekking) are sometimes suspended due to rain, flood alerts, or high water levels.",
                "fallback_action": f"Switch to an indoor cultural experience or local market tour, available on Thrillophilia.",
                "fallback_url": f"https://www.thrillophilia.com/places/{dest_slug}",
                "budget_impact_inr": 0,
            },
            {
                "risk": "Train/bus significantly delayed",
                "likelihood": "Medium",
                "description": f"Your transport from {prefs.origin} to {dest} could face delays of 2-6 hours, compressing your Day 1 itinerary.",
                "fallback_action": f"If delayed over 2 hours, skip morning activity on Day 1 and proceed directly to hotel. Book a shared taxi as backup via redBus.",
                "fallback_url": "https://www.redbus.in",
                "budget_impact_inr": 300,
            },
        ]

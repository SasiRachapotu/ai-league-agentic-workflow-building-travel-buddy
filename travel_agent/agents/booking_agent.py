"""
Booking Agent
Finds specific, bookable transport, hotel, and activity options with real URLs.
Checkpoint 3: Booking Cart.
"""
import json
import re
from tools.gemini_client import generate
from tools.tavily_tool import search_to_context
from models.schemas import TravelerPreferences, PlanOption, BudgetBreakdown, BookingOption


BOOKING_PROMPT = """
You are a travel booking expert for India. Find specific, real, bookable options.

Traveler:
- From: {origin} → To: {destination}
- Duration: {duration_days} days, {nights} nights
- Travel Dates: {travel_dates}
- Plan Style: {plan_style}
- Budget for Travel: ₹{travel_budget}
- Budget for Stay: ₹{stay_budget} total
- Budget for Activities: ₹{activities_budget} total
- Accommodation pref: {accommodation}
- Interests: {interests}

Web Search Context:
{web_context}

Return a JSON object with EXACTLY this structure:
{{
  "transport": {{
    "type": "<train|bus|flight>",
    "name": "<e.g. Jan Shatabdi Express / Volvo AC Bus>",
    "description": "<route and key details>",
    "cost_inr": <one-way fare per person>,
    "duration": "<e.g. 5-6 hrs>",
    "location": "{origin} → {destination}",
    "booking_url": "<real URL e.g. https://www.irctc.co.in>",
    "maps_url": null,
    "notes": "<booking tips>"
  }},
  "hotel": {{
    "type": "<hostel|hotel|guesthouse>",
    "name": "<specific property name>",
    "description": "<location + amenities>",
    "cost_inr": <price per night>,
    "cost_per_night_inr": <same as cost_inr>,
    "location": "<area in {destination}>",
    "booking_url": "<real URL e.g. https://www.zostel.com or https://www.goibibo.com>",
    "maps_url": "<google maps link>",
    "rating": <rating out of 5>,
    "notes": "<best features>"
  }},
  "activities": [
    {{
      "type": "activity",
      "name": "<activity name>",
      "description": "<brief description>",
      "cost_inr": <per person cost>,
      "duration": "<estimated duration>",
      "location": "<specific location>",
      "booking_url": "<real booking URL>",
      "maps_url": "<google maps link>",
      "notes": "<tips>"
    }}
  ]
}}

Rules:
- Use REAL, verifiable booking URLs (IRCTC for trains, Zostel/HostelWorld for hostels, Thrillophilia/GetYourGuide for activities, Goibibo/MakeMyTrip for hotels)
- Activities list must have 3-5 items matching traveler interests
- All costs must fit within the specified budgets
- Google Maps URLs format: https://maps.google.com/?q=<place+name>
- Return valid JSON ONLY. No markdown.
"""


def run(
    prefs: TravelerPreferences,
    selected_option: PlanOption,
    budget: BudgetBreakdown,
) -> tuple[BookingOption, BookingOption, list[BookingOption]]:
    """Find bookable transport, hotel, and activities."""

    travel_budget = next((c.amount_inr for c in budget.categories if "Travel" in c.category), prefs.total_budget_inr * 0.07)
    stay_budget = next((c.amount_inr for c in budget.categories if "Stay" in c.category), prefs.total_budget_inr * 0.25)
    activities_budget = next((c.amount_inr for c in budget.categories if "Activities" in c.category), prefs.total_budget_inr * 0.25)
    nights = prefs.duration_days - 1

    web_context = search_to_context(
        f"{prefs.origin} to {prefs.destination} train bus best hostel hotel {prefs.destination} activities booking",
        max_results=5,
    )

    prompt = BOOKING_PROMPT.format(
        origin=prefs.origin,
        destination=prefs.destination,
        duration_days=prefs.duration_days,
        nights=nights,
        travel_dates=prefs.travel_dates or "next weekend",
        plan_style=selected_option.style,
        travel_budget=int(travel_budget),
        stay_budget=int(stay_budget),
        activities_budget=int(activities_budget),
        accommodation=prefs.accommodation_preference,
        interests=", ".join(prefs.interests),
        web_context=web_context,
    )

    raw = generate(prompt, temperature=0.4)
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)

    try:
        data = json.loads(raw)
        transport = BookingOption(**data["transport"])
        hotel = BookingOption(**data["hotel"])
        activities = [BookingOption(**a) for a in data["activities"]]
        return transport, hotel, activities
    except Exception:
        # Fallback defaults (Rishikesh example)
        dest = prefs.destination
        transport = BookingOption(
            type="train",
            name="Jan Shatabdi Express",
            description=f"{prefs.origin} → Haridwar → {dest} by train + shared cab",
            cost_inr=550,
            duration="6-7 hrs",
            location=f"{prefs.origin} → {dest}",
            booking_url="https://www.irctc.co.in/",
            notes="Book 2 weeks in advance for best availability",
        )
        hotel = BookingOption(
            type="hostel",
            name=f"Zostel {dest}",
            description=f"Popular backpacker hostel in {dest} with great amenities",
            cost_inr=stay_budget / max(nights, 1),
            cost_per_night_inr=stay_budget / max(nights, 1),
            location="Tapovan area",
            booking_url="https://www.zostel.com/",
            maps_url=f"https://maps.google.com/?q=Zostel+{dest.replace(' ', '+')}",
            rating=4.3,
            notes="Dorm beds available, great community vibe",
        )
        activities = [
            BookingOption(
                type="activity",
                name="White Water Rafting",
                description="16 km stretch – Shivpuri to Rishikesh",
                cost_inr=1500,
                duration="3-4 hrs",
                location=dest,
                booking_url="https://www.thrillophilia.com/",
                maps_url=f"https://maps.google.com/?q=Shivpuri+{dest.replace(' ', '+')}",
                notes="Book 1 day in advance",
            ),
            BookingOption(
                type="activity",
                name="Ganga Aarti – Triveni Ghat",
                description="Spiritual fire ritual at sunset on the Ganges",
                cost_inr=0,
                duration="1.5 hrs",
                location="Triveni Ghat, Rishikesh",
                booking_url="https://maps.google.com/?q=Triveni+Ghat+Rishikesh",
                maps_url="https://maps.google.com/?q=Triveni+Ghat+Rishikesh",
                notes="Arrive 30 mins early for a good spot",
            ),
            BookingOption(
                type="activity",
                name="Beatles Ashram",
                description="Iconic ashram where The Beatles studied meditation",
                cost_inr=150,
                duration="2 hrs",
                location="Rishikesh",
                booking_url="https://maps.google.com/?q=Beatles+Ashram+Rishikesh",
                maps_url="https://maps.google.com/?q=Beatles+Ashram+Rishikesh",
                notes="Photography allowed; carry water",
            ),
        ]
        return transport, hotel, activities

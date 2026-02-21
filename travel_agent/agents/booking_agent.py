"""
Booking Agent
Finds specific, bookable transport, hotel, and activity options with real URLs.
Checkpoint 3: Booking Cart.
"""
import json
import re
from tools.openai_client import generate
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
        # Fallback defaults — use actual destination and interests
        dest = prefs.destination
        interests = prefs.interests or ["culture", "nature"]
        transport = BookingOption(
            type="train",
            name=f"Express Train to {dest}",
            description=f"{prefs.origin} → {dest} by train",
            cost_inr=travel_budget,
            duration="Varies",
            location=f"{prefs.origin} → {dest}",
            booking_url="https://www.irctc.co.in/",
            notes="Book in advance on IRCTC for best availability",
        )
        hotel = BookingOption(
            type="hotel",
            name=f"Budget Stay in {dest}",
            description=f"Comfortable budget accommodation in central {dest}",
            cost_inr=stay_budget / max(nights, 1),
            cost_per_night_inr=stay_budget / max(nights, 1),
            location=f"Central {dest}",
            booking_url=f"https://www.goibibo.com/hotels/{dest.lower().replace(' ', '-')}/",
            maps_url=f"https://maps.google.com/?q=hotels+in+{dest.replace(' ', '+')}",
            rating=3.8,
            notes="Check MakeMyTrip and Goibibo for best rates",
        )
        # Build interest-aware generic activities for the actual destination
        activity_templates = {
            "adventure": ("Adventure Activity", f"Exciting outdoor adventure experience in {dest}", 1200),
            "spiritual": ("Temple & Spiritual Tour", f"Visit key temples and spiritual sites in {dest}", 200),
            "cultural": ("Heritage & Culture Walk", f"Guided walk through {dest}'s historical and cultural landmarks", 500),
            "food": ("Local Food Tour", f"Street food and local cuisine exploration in {dest}", 800),
            "nature": ("Nature & Parks Tour", f"Explore parks and natural attractions around {dest}", 400),
            "wildlife": ("Wildlife Safari / Zoo Visit", f"Explore wildlife sanctuaries near {dest}", 1000),
            "trekking": ("Day Trek", f"Scenic day trek near {dest}", 600),
            "shopping": ("Local Market Tour", f"Explore {dest}'s vibrant local markets and bazaars", 0),
            "history": ("Historical Sites Tour", f"Visit forts, monuments and museums in {dest}", 300),
            "beaches": ("Beach Exploration", f"Explore beaches near {dest}", 200),
            "nightlife": ("Evening Entertainment", f"Experience {dest}'s nightlife scene", 500),
            "yoga": ("Yoga & Wellness Session", f"Morning yoga class in {dest}", 400),
        }
        activities = []
        for interest in interests[:4]:  # max 4 activities
            template = activity_templates.get(interest, (
                f"{interest.title()} Experience",
                f"Curated {interest} experience in {dest}",
                500,
            ))
            activities.append(BookingOption(
                type="activity",
                name=template[0],
                description=template[1],
                cost_inr=template[2],
                duration="2-3 hrs",
                location=dest,
                booking_url=f"https://www.thrillophilia.com/places/{dest.lower().replace(' ', '-')}",
                maps_url=f"https://maps.google.com/?q={interest}+in+{dest.replace(' ', '+')}",
                notes=f"Book in advance; check local guides in {dest}",
            ))
        if not activities:  # ultimate fallback
            activities = [BookingOption(
                type="activity",
                name=f"City Sightseeing Tour — {dest}",
                description=f"Explore the best of {dest} with a local guide",
                cost_inr=800, duration="4 hrs", location=dest,
                booking_url="https://www.thrillophilia.com/",
                maps_url=f"https://maps.google.com/?q=sightseeing+{dest.replace(' ', '+')}",
                notes="Book online or through hotel concierge",
            )]
        return transport, hotel, activities

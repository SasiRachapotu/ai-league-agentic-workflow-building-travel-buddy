"""
Itinerary Planner Agent
Assembles a detailed day-by-day itinerary with timings, costs, maps, and insider tips.
"""
import json
import re
from tools.openai_client import generate
from tools.tavily_tool import search_to_context
from models.schemas import (
    TravelerPreferences, PlanOption, BudgetBreakdown,
    BookingOption, ItineraryPlan, DayPlan, TimeBlock
)


ITINERARY_PROMPT = """
You are an expert travel itinerary planner. Build a detailed day-by-day itinerary.

Traveler:
- Destination: {destination}
- Origin: {origin}
- Duration: {duration_days} days
- Plan Style: {plan_style}
- Interests: {interests}
- Travel Dates: {travel_dates}
- Constraints: {constraints}
- Food preference: {food}

Transport: {transport_name} (₹{transport_cost}, {transport_duration})
Hotel: {hotel_name} at {hotel_location} (₹{hotel_cost}/night)
Key Activities: {activities_summary}

Web Context:
{web_context}

Return ONLY a valid JSON object:
{{
  "days": [
    {{
      "day_number": 1,
      "title": "Day 1 – <short evocative title>",
      "highlights": ["<1>", "<2>"],
      "total_cost_inr": <estimated cost for this day>,
      "blocks": [
        {{
          "time": "6:00 AM – 12:00 PM",
          "activity": "<Activity Name>",
          "description": "<What to do, experience, see>",
          "location": "<Specific place name>",
          "maps_url": "https://maps.google.com/?q=<Place+Name+{destination}>",
          "cost_inr": <0 or cost>,
          "booking_url": "<URL or null>",
          "tips": "<Insider tip>"
        }}
      ]
    }}
  ],
  "total_estimated_cost_inr": <sum of all day costs + transport + hotel>,
  "remaining_budget_inr": <total_budget - total_estimated_cost_inr>,
  "booking_checklist": ["<item 1>", "<item 2>", "<item 3>"],
  "insider_tips": ["<tip 1>", "<tip 2>", "<tip 3>"]
}}

Rules:
- Generate exactly {duration_days} day objects
- Day 1 must include travel from {origin} (morning departure, afternoon arrival)
- Last day must include return travel to {origin}
- Each day must have 3-5 time blocks covering morning, afternoon, and evening
- All times must be realistic (no teleporting, include travel time between places)
- Include meals (breakfast, lunch, dinner) with local restaurant recommendations
- All Google Maps URLs must be real format
- Costs per item must match the budget allocation
- Return valid JSON ONLY. No markdown, no extra text.
"""


def run(
    prefs: TravelerPreferences,
    selected_option: PlanOption,
    budget: BudgetBreakdown,
    transport: BookingOption,
    hotel: BookingOption,
    activities: list[BookingOption],
) -> ItineraryPlan:
    """Build a full day-by-day itinerary."""

    activities_summary = "; ".join(
        [f"{a.name} (₹{a.cost_inr})" for a in activities]
    )
    web_context = search_to_context(
        f"{prefs.destination} travel itinerary day by day tips local food",
        max_results=4,
    )

    prompt = ITINERARY_PROMPT.format(
        destination=prefs.destination,
        origin=prefs.origin,
        duration_days=prefs.duration_days,
        plan_style=selected_option.style,
        interests=", ".join(prefs.interests),
        travel_dates=prefs.travel_dates or "next weekend",
        constraints=", ".join(prefs.constraints) if prefs.constraints else "none",
        food=prefs.food_preference,
        transport_name=transport.name,
        transport_cost=transport.cost_inr,
        transport_duration=transport.duration or "varies",
        hotel_name=hotel.name,
        hotel_location=hotel.location or prefs.destination,
        hotel_cost=hotel.cost_per_night_inr or hotel.cost_inr,
        activities_summary=activities_summary,
        web_context=web_context,
    )

    raw = generate(prompt, temperature=0.6)
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)

    try:
        data = json.loads(raw)
        days = []
        for d in data["days"]:
            blocks = [TimeBlock(**b) for b in d["blocks"]]
            days.append(DayPlan(
                day_number=d["day_number"],
                title=d["title"],
                highlights=d.get("highlights", []),
                total_cost_inr=d["total_cost_inr"],
                blocks=blocks,
            ))

        return ItineraryPlan(
            preferences=prefs,
            selected_option=selected_option,
            budget_breakdown=budget,
            transport_booking=transport,
            hotel_booking=hotel,
            activity_bookings=activities,
            days=days,
            total_estimated_cost_inr=data["total_estimated_cost_inr"],
            remaining_budget_inr=data["remaining_budget_inr"],
            booking_checklist=data.get("booking_checklist", []),
            insider_tips=data.get("insider_tips", []),
        )
    except Exception as e:
        # Fallback: return minimal structure
        return _fallback_itinerary(prefs, selected_option, budget, transport, hotel, activities)


def _fallback_itinerary(prefs, option, budget, transport, hotel, activities):
    days = []
    dest = prefs.destination
    for i in range(1, prefs.duration_days + 1):
        if i == 1:
            title = f"Day {i} – Travel + Arrival"
            blocks = [
                TimeBlock(time="6:00 AM – 12:00 PM", activity=f"{prefs.origin} → {dest}",
                          description=f"Depart via {transport.name}", cost_inr=transport.cost_inr,
                          booking_url=transport.booking_url),
                TimeBlock(time="2:00 PM – 3:00 PM", activity="Hotel Check-in",
                          description=f"Check in at {hotel.name}", cost_inr=0,
                          maps_url=hotel.maps_url, booking_url=hotel.booking_url),
                TimeBlock(time="6:00 PM – 8:00 PM", activity="Evening Exploration",
                          description=f"Explore {dest} city center", cost_inr=0,
                          maps_url=f"https://maps.google.com/?q={dest.replace(' ', '+')}"),
            ]
        elif i == prefs.duration_days:
            title = f"Day {i} – Sunrise + Return"
            blocks = [
                TimeBlock(time="5:30 AM – 7:00 AM", activity="Sunrise Visit",
                          description="Early morning scenic viewpoint", cost_inr=0),
                TimeBlock(time="8:00 AM – 9:00 AM", activity="Hotel Check-out + Breakfast",
                          description="Final meal and pack up", cost_inr=200),
                TimeBlock(time="10:00 AM – 5:00 PM", activity=f"Return to {prefs.origin}",
                          description=f"Board {transport.name} back", cost_inr=transport.cost_inr,
                          booking_url=transport.booking_url),
            ]
        else:
            act = activities[(i - 2) % len(activities)] if activities else None
            title = f"Day {i} – Explore & Experience"
            blocks = [
                TimeBlock(time="8:00 AM – 9:00 AM", activity="Breakfast",
                          description="Local restaurant", cost_inr=200),
                TimeBlock(time="10:00 AM – 1:00 PM",
                          activity=act.name if act else "Local Sightseeing",
                          description=act.description if act else "Explore key sites",
                          cost_inr=act.cost_inr if act else 300,
                          booking_url=act.booking_url if act else None,
                          maps_url=act.maps_url if act else None),
                TimeBlock(time="3:00 PM – 6:00 PM", activity="Afternoon Activities",
                          description="Free time / optional activities", cost_inr=200),
                TimeBlock(time="7:00 PM – 9:00 PM", activity="Dinner",
                          description="Local cuisine recommendation", cost_inr=300),
            ]
        total = sum(b.cost_inr for b in blocks)
        days.append(DayPlan(day_number=i, title=title, blocks=blocks,
                             total_cost_inr=total, highlights=[]))

    total_cost = sum(d.total_cost_inr for d in days) + hotel.cost_inr * (prefs.duration_days - 1)
    return ItineraryPlan(
        preferences=prefs, selected_option=option, budget_breakdown=budget,
        transport_booking=transport, hotel_booking=hotel, activity_bookings=activities,
        days=days, total_estimated_cost_inr=total_cost,
        remaining_budget_inr=prefs.total_budget_inr - total_cost,
        booking_checklist=["Book train tickets on IRCTC", "Confirm hotel booking", "Reserve activity slots"],
        insider_tips=["Carry cash for local vendors", "Book trains 2 weeks in advance", "Bargain at local markets"],
    )

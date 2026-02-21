"""
Plan Options Agent
Generates 3 plan options (A/B/C) for user to choose at Checkpoint 1.
Each option has a different theme, estimated cost, highlights, pros/cons.
"""
import json
import re
from tools.gemini_client import generate
from tools.tavily_tool import search_to_context
from tools.weather_tool import get_weather_summary
from models.schemas import TravelerPreferences, PlanOption


PLAN_OPTIONS_PROMPT = """
You are a travel planning expert. Generate exactly 3 distinct trip plan options for a traveler.

Traveler Details:
- Destination: {destination}
- Origin: {origin}
- Duration: {duration_days} days
- Total Budget: ₹{budget}
- Travel Style: {style}
- Interests: {interests}
- Group Size: {group_size}
- Travel Dates: {travel_dates}
- Constraints: {constraints}
- Stay Preference: {accommodation}
- Food: {food}

Web Research Context:
{web_context}

Weather:
{weather}

Generate 3 plan options. Return JSON array with EXACTLY 3 objects:
[
  {{
    "label": "A",
    "style": "<descriptive style, e.g. Balanced Adventure + Spiritual>",
    "estimated_total_inr": <number>,
    "highlights": ["<highlight 1>", "<highlight 2>", "<highlight 3>"],
    "pros": ["<pro 1>", "<pro 2>"],
    "cons": ["<con 1>"],
    "recommended": true
  }},
  {{
    "label": "B",
    "style": "<descriptive style>",
    "estimated_total_inr": <number>,
    "highlights": ["<highlight 1>", "<highlight 2>", "<highlight 3>"],
    "pros": ["<pro 1>", "<pro 2>"],
    "cons": ["<con 1>"],
    "recommended": false
  }},
  {{
    "label": "C",
    "style": "<descriptive style>",
    "estimated_total_inr": <number>,
    "highlights": ["<highlight 1>", "<highlight 2>", "<highlight 3>"],
    "pros": ["<pro 1>", "<pro 2>"],
    "cons": ["<con 1>"],
    "recommended": false
  }}
]

Rules:
- All estimated costs MUST be within or close to the budget ₹{budget}
- Options A, B, C must be noticeably different in focus/theme
- Only ONE option should have recommended=true (the best balanced one)
- Highlights must be real, specific activities/places in {destination}
- Return valid JSON array ONLY. No markdown, no explanation.
"""


def run(prefs: TravelerPreferences) -> list[PlanOption]:
    """Generate 3 plan options based on traveler preferences."""
    web_context = search_to_context(
        f"{prefs.destination} travel guide {' '.join(prefs.interests)} {prefs.duration_days} days",
        max_results=4,
    )
    weather = get_weather_summary(prefs.destination, prefs.travel_dates or "next weekend")

    prompt = PLAN_OPTIONS_PROMPT.format(
        destination=prefs.destination,
        origin=prefs.origin,
        duration_days=prefs.duration_days,
        budget=prefs.total_budget_inr,
        style=prefs.travel_style.value,
        interests=", ".join(prefs.interests),
        group_size=prefs.group_size,
        travel_dates=prefs.travel_dates or "flexible",
        constraints=", ".join(prefs.constraints) if prefs.constraints else "none",
        accommodation=prefs.accommodation_preference,
        food=prefs.food_preference,
        web_context=web_context,
        weather=weather,
    )

    raw = generate(prompt, temperature=0.7)
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)

    # Extract JSON array
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        raw = match.group(0)

    try:
        data = json.loads(raw)
        return [PlanOption(**item) for item in data]
    except Exception:
        # Fallback defaults
        return [
            PlanOption(
                label="A",
                style="Balanced Adventure + Spiritual",
                estimated_total_inr=prefs.total_budget_inr * 0.88,
                highlights=["White Water Rafting", "Ganga Aarti at Triveni Ghat", "Beatles Ashram"],
                pros=["Best balance of activities", "Within budget with buffer"],
                cons=["Moderate physical effort needed"],
                recommended=True,
            ),
            PlanOption(
                label="B",
                style="Spiritual Focus",
                estimated_total_inr=prefs.total_budget_inr * 0.77,
                highlights=["Ashram Stay", "Daily Yoga Sessions", "Temple Circuit"],
                pros=["Very budget-friendly", "Peaceful & rejuvenating"],
                cons=["Less adventure activities"],
                recommended=False,
            ),
            PlanOption(
                label="C",
                style="Adventure Heavy",
                estimated_total_inr=prefs.total_budget_inr * 0.98,
                highlights=["Rafting", "Cliff Jumping", "Neer Garh Waterfall Trek"],
                pros=["Max adventure", "Memorable adrenaline experience"],
                cons=["Uses almost full budget", "Physically demanding"],
                recommended=False,
            ),
        ]

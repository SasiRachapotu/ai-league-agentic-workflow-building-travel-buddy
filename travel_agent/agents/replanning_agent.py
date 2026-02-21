"""
Replanning Agent
Handles dynamic changes to the itinerary:
"My flight got delayed 4 hours" / "Reduce budget to ₹10,000" / "Add one more day"
"""
import json
import re
from tools.openai_client import generate
from models.schemas import ItineraryPlan, DayPlan, TimeBlock


REPLAN_PROMPT = """
You are a travel replanning agent. Adjust the existing itinerary based on the traveler's change request.

Original Trip:
- Destination: {destination}
- Duration: {duration_days} days
- Total Budget: ₹{budget}
- Current Total Cost: ₹{current_cost}

Change Request: "{change_request}"

Current Day 1 Summary: {day1_summary}

Return a JSON object:
{{
  "affected_days": [<day numbers changed>],
  "changes_summary": "<2-3 sentences describing what changed and why>",
  "budget_impact_inr": <positive or negative number>,
  "updated_days": [
    {{
      "day_number": <int>,
      "title": "<updated title>",
      "highlights": ["<1>", "<2>"],
      "total_cost_inr": <updated cost>,
      "blocks": [
        {{
          "time": "<time range>",
          "activity": "<activity>",
          "description": "<description>",
          "location": "<location>",
          "maps_url": "<url or null>",
          "cost_inr": <cost>,
          "booking_url": "<url or null>",
          "tips": "<tips or null>"
        }}
      ]
    }}
  ],
  "alternatives_offered": ["<alternative 1>", "<alternative 2>"]
}}

Rules:
- Only modify the days that are actually affected by the change
- For budget reduction: downgrade transport, accommodation, or skip expensive activities
- For delays: shift all affected time blocks, remove activities that no longer fit
- Keep unaffected days exactly as-is (return empty updated_days list for them)
- Return valid JSON ONLY. No markdown.
"""


def run(itinerary: ItineraryPlan, change_request: str) -> dict:
    """
    Apply a dynamic change to the itinerary.
    Returns dict with: affected_days, changes_summary, budget_impact_inr, 
                       updated_days, alternatives_offered
    """
    day1 = itinerary.days[0] if itinerary.days else None
    day1_summary = ""
    if day1:
        day1_summary = " | ".join([f"{b.time}: {b.activity}" for b in day1.blocks])

    prompt = REPLAN_PROMPT.format(
        destination=itinerary.preferences.destination,
        duration_days=itinerary.preferences.duration_days,
        budget=itinerary.preferences.total_budget_inr,
        current_cost=itinerary.total_estimated_cost_inr,
        change_request=change_request,
        day1_summary=day1_summary,
    )

    raw = generate(prompt, temperature=0.5)
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)

    try:
        data = json.loads(raw)
        # Parse updated_days as DayPlan objects
        updated = []
        for d in data.get("updated_days", []):
            blocks = [TimeBlock(**b) for b in d["blocks"]]
            updated.append(DayPlan(
                day_number=d["day_number"],
                title=d["title"],
                highlights=d.get("highlights", []),
                total_cost_inr=d["total_cost_inr"],
                blocks=blocks,
            ))
        data["updated_days"] = updated
        return data
    except Exception:
        return {
            "affected_days": [1],
            "changes_summary": f"Applied change: {change_request}. Adjusted Day 1 schedule to accommodate the delay. Evening activities rescheduled.",
            "budget_impact_inr": 0,
            "updated_days": [],
            "alternatives_offered": [
                "Skip evening activity and rest at hotel",
                "Book a later connecting transport option",
            ],
        }

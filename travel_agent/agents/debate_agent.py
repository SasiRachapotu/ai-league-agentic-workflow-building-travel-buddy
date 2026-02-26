"""
Debate Agent
Generates transparent reasoning: scores each plan option (A/B/C) across
Budget, Comfort, Experience, Time-Efficiency, and Risk axes, and explains
*why* one wins over another. Shown at Checkpoint 1 as the "Agent Reasoning" panel.
"""
import json
import re
from tools.openai_client import generate
from models.schemas import TravelerPreferences, PlanOption


DEBATE_PROMPT = """
You are a multi-criteria travel decision analyst. Evaluate 3 trip plan options for a traveler.

Traveler:
- Destination: {destination}
- Budget: ₹{budget}
- Style: {style}
- Interests: {interests}
- Duration: {duration_days} days

Options:
{options_summary}

Score each option on 5 axes (1–10 scale). Return a JSON object:
{{
  "axes": ["Budget Efficiency", "Comfort", "Experience Richness", "Time Efficiency", "Risk"],
  "scores": {{
    "A": {{"Budget Efficiency": <1-10>, "Comfort": <1-10>, "Experience Richness": <1-10>, "Time Efficiency": <1-10>, "Risk": <1-10>}},
    "B": {{"Budget Efficiency": <1-10>, "Comfort": <1-10>, "Experience Richness": <1-10>, "Time Efficiency": <1-10>, "Risk": <1-10>}},
    "C": {{"Budget Efficiency": <1-10>, "Comfort": <1-10>, "Experience Richness": <1-10>, "Time Efficiency": <1-10>, "Risk": <1-10>}}
  }},
  "reasoning": {{
    "A": "<2-sentence reasoning for why Option A scores as it does>",
    "B": "<2-sentence reasoning for why Option B scores as it does>",
    "C": "<2-sentence reasoning for why Option C scores as it does>"
  }},
  "winner_axis": {{
    "Budget Efficiency": "<A, B, or C>",
    "Comfort": "<A, B, or C>",
    "Experience Richness": "<A, B, or C>",
    "Time Efficiency": "<A, B, or C>",
    "Risk": "<A, B, or C — lowest risk wins>"
  }},
  "recommendation_rationale": "<1-2 sentence summary of why the recommended option is best overall>"
}}

Rules:
- Risk axis: LOWER risk = HIGHER score (10 = safest)
- Scores must differ meaningfully between options (avoid all 7s)
- Return valid JSON ONLY. No markdown.
"""


def run(prefs: TravelerPreferences, options: list[PlanOption]) -> dict:
    """
    Generate debate/scoring for the 3 plan options.
    Returns dict with: axes, scores, reasoning, winner_axis, recommendation_rationale
    """
    options_summary = "\n".join([
        f"Option {o.label} — {o.style} (₹{o.estimated_total_inr:,.0f}): "
        f"Highlights: {', '.join(o.highlights)}. "
        f"Pros: {', '.join(o.pros)}. Cons: {', '.join(o.cons)}."
        for o in options
    ])

    prompt = DEBATE_PROMPT.format(
        destination=prefs.destination,
        budget=int(prefs.total_budget_inr),
        style=prefs.travel_style.value,
        interests=", ".join(prefs.interests),
        duration_days=prefs.duration_days,
        options_summary=options_summary,
    )

    raw = generate(prompt, temperature=0.3)
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)

    try:
        return json.loads(raw)
    except Exception:
        # Sensible fallback
        rec = next((o.label for o in options if o.recommended), "A")
        return {
            "axes": ["Budget Efficiency", "Comfort", "Experience Richness", "Time Efficiency", "Risk"],
            "scores": {
                "A": {"Budget Efficiency": 8, "Comfort": 7, "Experience Richness": 8, "Time Efficiency": 7, "Risk": 8},
                "B": {"Budget Efficiency": 9, "Comfort": 6, "Experience Richness": 6, "Time Efficiency": 8, "Risk": 9},
                "C": {"Budget Efficiency": 6, "Comfort": 7, "Experience Richness": 9, "Time Efficiency": 6, "Risk": 6},
            },
            "reasoning": {
                "A": f"Option A offers a balanced mix of activities and comfort within the ₹{int(prefs.total_budget_inr):,} budget. It is the safest recommended choice.",
                "B": f"Option B is most budget-efficient but sacrifices experience variety — best for very tight budgets.",
                "C": f"Option C maximises experiences but stretches the budget and carries higher logistical risk.",
            },
            "winner_axis": {
                "Budget Efficiency": "B",
                "Comfort": "A",
                "Experience Richness": "C",
                "Time Efficiency": "B",
                "Risk": "B",
            },
            "recommendation_rationale": f"Option {rec} provides the best trade-off across all axes for this traveler's profile and budget.",
        }

"""
Budget Optimizer Agent
Generates an intelligent budget breakdown for Checkpoint 2.
Allocates the total budget across categories with smart trade-offs.
"""
import json
import re
from tools.openai_client import generate
from models.schemas import TravelerPreferences, PlanOption, BudgetBreakdown, BudgetCategory


BUDGET_PROMPT = """
You are a travel budget optimization expert.

Traveler:
- Destination: {destination}
- Duration: {duration_days} days
- Total Budget: ₹{budget}
- Style: {style}
- Accommodation: {accommodation}
- Selected Plan: {plan_label} – {plan_style} (est. ₹{plan_cost})

Allocate the budget across these categories for {duration_days} days.
Return JSON with EXACTLY this structure:
{{
  "plan_label": "{plan_label}",
  "categories": [
    {{"category": "Travel (to & from)", "amount_inr": <number>, "description": "<mode + route>"}},
    {{"category": "Stay ({nights} nights)", "amount_inr": <number>, "description": "<type of stay>"}},
    {{"category": "Food & Dining", "amount_inr": <number>, "description": "<meal plan>"}},
    {{"category": "Activities", "amount_inr": <number>, "description": "<key activities>"}},
    {{"category": "Local Transport", "amount_inr": <number>, "description": "<within destination>"}},
    {{"category": "Entry Fees", "amount_inr": <number>, "description": "<sites + attractions>"}},
    {{"category": "Miscellaneous", "amount_inr": <number>, "description": "<tips, SIM, emergencies>"}},
    {{"category": "Buffer", "amount_inr": <number>, "description": "Emergency reserve"}}
  ],
  "projected_total_inr": <sum of all amounts>,
  "remaining_buffer_inr": <budget - projected_total_inr>,
  "optimization_notes": "<2-3 sentence explanation of key trade-offs made>"
}}

Rules:
- Sum of all category amounts = projected_total_inr
- projected_total_inr MUST be < {budget}
- remaining_buffer_inr = {budget} - projected_total_inr
- Buffer category should be at least ₹{min_buffer}
- Return valid JSON ONLY. No markdown.
"""


def run(prefs: TravelerPreferences, selected_option: PlanOption) -> BudgetBreakdown:
    """Optimize budget allocation for the selected plan."""
    nights = prefs.duration_days - 1
    min_buffer = max(500, prefs.total_budget_inr * 0.05)

    prompt = BUDGET_PROMPT.format(
        destination=prefs.destination,
        duration_days=prefs.duration_days,
        budget=prefs.total_budget_inr,
        style=prefs.travel_style.value,
        accommodation=prefs.accommodation_preference,
        plan_label=selected_option.label,
        plan_style=selected_option.style,
        plan_cost=selected_option.estimated_total_inr,
        nights=nights,
        min_buffer=int(min_buffer),
    )

    raw = generate(prompt, temperature=0.3)
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)

    try:
        data = json.loads(raw)
        data["categories"] = [BudgetCategory(**c) for c in data["categories"]]
        return BudgetBreakdown(**data)
    except Exception:
        # Fallback proportional breakdown
        b = prefs.total_budget_inr
        nights = prefs.duration_days - 1
        categories = [
            BudgetCategory(category="Travel (to & from)", amount_inr=b * 0.07, description="Train/bus round trip"),
            BudgetCategory(category=f"Stay ({nights} nights)", amount_inr=b * 0.26, description="Budget hostel/hotel"),
            BudgetCategory(category="Food & Dining", amount_inr=b * 0.18, description="Local meals + snacks"),
            BudgetCategory(category="Activities", amount_inr=b * 0.25, description="Key experiences"),
            BudgetCategory(category="Local Transport", amount_inr=b * 0.06, description="Auto/shared cab"),
            BudgetCategory(category="Entry Fees", amount_inr=b * 0.04, description="Sites & attractions"),
            BudgetCategory(category="Miscellaneous", amount_inr=b * 0.06, description="Tips, emergencies"),
            BudgetCategory(category="Buffer", amount_inr=b * 0.08, description="Emergency reserve"),
        ]
        total = sum(c.amount_inr for c in categories)
        return BudgetBreakdown(
            plan_label=selected_option.label,
            categories=categories,
            projected_total_inr=round(total, 0),
            remaining_buffer_inr=round(b - total, 0),
            optimization_notes="Budget allocated proportionally across categories, optimized for value.",
        )

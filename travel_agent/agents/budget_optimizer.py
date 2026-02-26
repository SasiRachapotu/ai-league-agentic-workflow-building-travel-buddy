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
You are a travel budget optimization expert. Allocate a trip budget with STRICT math constraints.

Traveler:
- Destination: {destination}
- Duration: {duration_days} days ({nights} nights)
- TOTAL BUDGET: ₹{budget} (this is the hard limit — you MUST NOT exceed it)
- Travel Style: {style}
- Accommodation: {accommodation}
- Selected Plan: Option {plan_label} – {plan_style}

STRICT RULES — violating these is wrong:
1. The Buffer row is FIXED at ₹{min_buffer}. Do not change it.
2. The remaining ₹{spending_limit} must be split across the other 7 categories.
3. Sum of all 8 rows (including Buffer) MUST equal exactly ₹{budget}.
4. Every amount must be a round number (multiple of 50 or 100). No decimals.
5. Return valid JSON only. No markdown fences.

Return EXACTLY this JSON structure:
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
    {{"category": "Buffer", "amount_inr": {min_buffer}, "description": "Emergency reserve"}}
  ],
  "projected_total_inr": {budget},
  "remaining_buffer_inr": 0,
  "optimization_notes": "<2-3 sentences on trade-offs made>"
}}

Verify before responding: sum all 8 amount_inr values. They MUST add up to exactly ₹{budget}.
"""


def run(prefs: TravelerPreferences, selected_option: PlanOption) -> BudgetBreakdown:
    """Optimize budget allocation for the selected plan."""
    nights = prefs.duration_days - 1
    budget = int(prefs.total_budget_inr)
    min_buffer = max(500, int(budget * 0.05))
    # Round min_buffer to nearest 100 for clean numbers
    min_buffer = round(min_buffer / 100) * 100
    spending_limit = budget - min_buffer  # what's left after reserving buffer

    prompt = BUDGET_PROMPT.format(
        destination=prefs.destination,
        duration_days=prefs.duration_days,
        budget=budget,
        style=prefs.travel_style.value,
        accommodation=prefs.accommodation_preference,
        plan_label=selected_option.label,
        plan_style=selected_option.style,
        nights=nights,
        min_buffer=min_buffer,
        spending_limit=spending_limit,
    )

    raw = generate(prompt, temperature=0.3)
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)

    try:
        data = json.loads(raw)
        categories = [BudgetCategory(**c) for c in data["categories"]]

        # Safety clamp: if LLM still exceeded the budget, trim the last
        # non-buffer category by the overshoot amount so amounts stay clean.
        actual_total = sum(c.amount_inr for c in categories)
        if actual_total > budget:
            overshoot = actual_total - budget
            # Find last non-buffer category and reduce it
            for i in range(len(categories) - 1, -1, -1):
                if categories[i].category.lower() != "buffer":
                    new_amount = max(0, categories[i].amount_inr - overshoot)
                    categories[i] = BudgetCategory(
                        category=categories[i].category,
                        amount_inr=new_amount,
                        description=categories[i].description,
                    )
                    break
            actual_total = sum(c.amount_inr for c in categories)

        actual_total = round(actual_total, 0)
        actual_buffer = max(0.0, round(budget - actual_total, 0))

        return BudgetBreakdown(
            plan_label=data.get("plan_label", selected_option.label),
            categories=categories,
            projected_total_inr=actual_total,
            remaining_buffer_inr=actual_buffer,
            optimization_notes=data.get("optimization_notes", ""),
        )
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

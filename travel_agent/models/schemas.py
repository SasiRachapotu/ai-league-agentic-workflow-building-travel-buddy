from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from enum import Enum


class TravelStyle(str, Enum):
    SOLO_BACKPACKING = "solo_backpacking"
    FAMILY = "family"
    COUPLE = "couple"
    GROUP = "group"
    SOLO_LUXURY = "solo_luxury"


class TravelerPreferences(BaseModel):
    raw_input: str = Field(description="Original user query")
    destination: str = Field(description="Primary destination city/place")
    origin: str = Field(description="Origin city")
    duration_days: int = Field(description="Number of days")
    total_budget_inr: float = Field(description="Total budget in INR")
    travel_style: TravelStyle = Field(default=TravelStyle.SOLO_BACKPACKING)
    interests: List[str] = Field(default_factory=list, description="e.g. adventure, spiritual, food, culture")
    group_size: int = Field(default=1)
    travel_dates: Optional[str] = Field(default=None, description="e.g. 'next weekend', 'March 15-18'")
    constraints: List[str] = Field(default_factory=list, description="Special constraints or preferences")
    accommodation_preference: Literal["budget", "mid-range", "luxury"] = "budget"
    food_preference: Literal["veg", "non-veg", "both"] = "both"
    persona: Optional[str] = Field(default=None, description="Traveler persona e.g. 'Backpacker', 'Adrenaline Junkie'")


class PlanOption(BaseModel):
    label: str = Field(description="A, B, or C")
    style: str = Field(description="e.g. 'Balanced Adventure + Spiritual'")
    estimated_total_inr: float
    highlights: List[str] = Field(description="3-4 key highlights")
    pros: List[str]
    cons: List[str]
    recommended: bool = False


class BudgetCategory(BaseModel):
    category: str
    amount_inr: float
    description: str


class BudgetBreakdown(BaseModel):
    plan_label: str
    categories: List[BudgetCategory]
    projected_total_inr: float
    remaining_buffer_inr: float
    optimization_notes: str


class BookingOption(BaseModel):
    type: Literal["flight", "train", "bus", "hotel", "hostel", "activity", "transport"]
    name: str
    description: str
    cost_inr: float
    cost_per_night_inr: Optional[float] = None
    duration: Optional[str] = None
    location: Optional[str] = None
    booking_url: str
    maps_url: Optional[str] = None
    rating: Optional[float] = None
    notes: Optional[str] = None


class TimeBlock(BaseModel):
    time: str = Field(description="e.g. '8:00 AM – 10:00 AM'")
    activity: str
    description: str
    location: Optional[str] = None
    maps_url: Optional[str] = None
    cost_inr: float = 0
    booking_url: Optional[str] = None
    tips: Optional[str] = None


class DayPlan(BaseModel):
    day_number: int
    title: str = Field(description="e.g. 'Day 1 – Travel + Spiritual Evening'")
    blocks: List[TimeBlock]
    total_cost_inr: float
    highlights: List[str]


class ContingencyPlan(BaseModel):
    risk: str
    likelihood: Literal["Low", "Medium", "High"]
    description: str
    fallback_action: str
    fallback_url: str
    budget_impact_inr: float = 0


class ItineraryPlan(BaseModel):
    preferences: TravelerPreferences
    selected_option: PlanOption
    budget_breakdown: BudgetBreakdown
    transport_booking: BookingOption
    hotel_booking: BookingOption
    activity_bookings: List[BookingOption]
    days: List[DayPlan]
    total_estimated_cost_inr: float
    remaining_budget_inr: float
    booking_checklist: List[str]
    insider_tips: List[str]
    weather_summary: Optional[str] = None
    contingency_plans: Optional[List[ContingencyPlan]] = None


class WeatherInfo(BaseModel):
    destination: str
    period: str
    summary: str
    avg_temp_c: float
    conditions: str
    clothing_tips: str


class AgentLog(BaseModel):
    agent_name: str
    status: Literal["running", "done", "error"]
    message: str
    details: Optional[str] = None

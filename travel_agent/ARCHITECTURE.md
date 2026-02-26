# ✈️ AI Travel Agent — System Architecture

> **Multi-Agent Agentic Workflow for Intelligent Trip Planning**  
> Built with Python · Streamlit · OpenAI GPT-4o-mini · Tavily · OpenWeatherMap

---

## 🗺️ High-Level System Flow

```mermaid
flowchart TD
    USER([👤 User]) -->|Natural language trip request| APP[🖥️ Streamlit App\napp.py]

    APP -->|Input Validation| V{Valid\nPrompt?}
    V -- "No" --> WARN[⚠️ Validation Warning\nAsk for more details]
    V -- "No Origin" --> ORIGIN[📍 Ask for\nDeparture City]
    ORIGIN -->|User confirms| APP
    V -- "Yes" --> IP

    subgraph AGENTS ["🤖 Multi-Agent Pipeline"]
        IP[🧠 Intent Parser\nParse NL → Structured Prefs]
        IP --> POA[📋 Plan Options Agent\nGenerate 3 Plan Options A/B/C]
        POA --> DA[⚖️ Debate Agent\nScore & Rank Plans on 5 Axes]
    end

    APP --> AGENTS

    DA --> CP1{🧾 Checkpoint 1\nUser Picks Plan}

    CP1 -->|User selects A/B/C| BO[💰 Budget Optimizer\nAllocate Budget Across Categories]
    BO --> CP2{🧾 Checkpoint 2\nUser Approves Budget}

    CP2 -->|User approves| BA[🔍 Booking Agent\nFind Transport, Hotel, Activities]
    BA --> CP3{🧾 Checkpoint 3\nUser Confirms Bookings}

    CP3 -->|User confirms| ITP[🗓️ Itinerary Planner\nBuild Day-by-Day Plan]
    ITP --> RA[⚠️ Resilience Agent\nGenerate Contingency Plans]
    RA --> DONE[✅ Complete Trip Package]

    DONE --> TAB1[🗺️ Itinerary & Map View]
    DONE --> TAB2[💰 Budget Breakdown]
    DONE --> TAB3[📥 PDF / JSON Export]

    subgraph REPLAN ["🔄 Dynamic Replanning"]
        REA[🔁 Replanning Agent\nApply Mid-Trip Changes]
    end
    DONE -->|"User requests change\n(e.g. delay, budget cut)"| REA
    REA --> DONE
```

---

## 🏗️ Project Structure

```
travel_agent/
├── app.py                    # Main Streamlit UI & Orchestrator
├── agents/
│   ├── intent_parser.py      # Agent 1 – NL → Structured Preferences
│   ├── plan_options_agent.py # Agent 2 – Generate 3 Plan Options
│   ├── debate_agent.py       # Agent 3 – Score & Rank Plans
│   ├── budget_optimizer.py   # Agent 4 – Budget Allocation
│   ├── booking_agent.py      # Agent 5 – Find Bookable Options
│   ├── itinerary_planner.py  # Agent 6 – Day-by-Day Itinerary
│   ├── resilience_agent.py   # Agent 7 – Contingency Plans
│   └── replanning_agent.py   # Agent 8 – Dynamic Re-planning
├── tools/
│   ├── openai_client.py      # LLM Gateway (GPT-4o-mini)
│   ├── tavily_tool.py        # Live Web Search Tool
│   └── weather_tool.py       # Weather Data Tool
├── models/
│   └── schemas.py            # Pydantic Data Models
└── ui/
    ├── map_view.py            # Interactive Map (Folium)
    └── pdf_export.py         # PDF Generation (FPDF2)
```

---

## 🤖 Agent Responsibilities

| # | Agent | Role | Key Inputs | Key Outputs |
|---|-------|------|-----------|-------------|
| 1 | **Intent Parser** | Parses free-text → structured data | Natural language query | `TravelerPreferences` object |
| 2 | **Plan Options Agent** | Creates 3 distinct trip options | Preferences + Web/Weather data | 3× `PlanOption` (A/B/C) |
| 3 | **Debate Agent** | Scores options on 5 axes | 3 Plan Options | Scores + reasoning per axis |
| 4 | **Budget Optimizer** | Allocates budget intelligently | Selected option + budget | `BudgetBreakdown` with 8 categories |
| 5 | **Booking Agent** | Finds real bookable options | Budget + preferences | Transport, Hotel, Activities |
| 6 | **Itinerary Planner** | Builds day-by-day schedule | All booking details | `ItineraryPlan` with `DayPlan[]` |
| 7 | **Resilience Agent** | Anticipates what could go wrong | Finalized itinerary | 3× `ContingencyPlan` |
| 8 | **Replanning Agent** | Handles mid-trip changes | Itinerary + change request | Updated `DayPlan[]` |

---

## 🔁 Human-in-the-Loop (HITL) Checkpoints

```mermaid
sequenceDiagram
    participant U as 👤 User
    participant O as 🖥️ Orchestrator
    participant A as 🤖 Agents

    U->>O: "Plan 4-day Rishikesh trip under ₹15,000"
    O->>A: Run Intent Parser → Plan Options → Debate
    A-->>O: 3 Options + Debate Scores
    O-->>U: 📍 Checkpoint 1 — Pick a Plan (A/B/C)

    U->>O: Selects Option A
    O->>A: Run Budget Optimizer
    A-->>O: Budget Breakdown (8 categories)
    O-->>U: 📍 Checkpoint 2 — Approve Budget

    U->>O: Approves Budget
    O->>A: Run Booking Agent
    A-->>O: Transport + Hotel + Activities
    O-->>U: 📍 Checkpoint 3 — Confirm Bookings

    U->>O: Confirms Bookings
    O->>A: Run Itinerary Planner + Resilience Agent
    A-->>O: Full ItineraryPlan + Contingency Plans
    O-->>U: ✅ Complete Trip Package (Map + PDF + JSON)
```

---

## 🧰 Tools & External APIs

```mermaid
graph LR
    subgraph TOOLS ["🔧 Tool Layer"]
        OAI[🧠 OpenAI GPT-4o-mini\nopenai_client.py]
        TAV[🌐 Tavily Web Search\ntavily_tool.py]
        WTH[🌤️ OpenWeatherMap\nweather_tool.py]
    end

    subgraph AGENTS2 ["🤖 Agents"]
        A1[Intent Parser]
        A2[Plan Options Agent]
        A3[Debate Agent]
        A4[Budget Optimizer]
        A5[Booking Agent]
        A6[Itinerary Planner]
        A7[Resilience Agent]
        A8[Replanning Agent]
    end

    A1 --> OAI
    A2 --> OAI
    A2 --> TAV
    A2 --> WTH
    A3 --> OAI
    A4 --> OAI
    A5 --> OAI
    A5 --> TAV
    A6 --> OAI
    A6 --> TAV
    A7 --> OAI
    A8 --> OAI
```

---

## 📦 Data Models (Pydantic Schemas)

```mermaid
classDiagram
    class TravelerPreferences {
        +str destination
        +str origin
        +int duration_days
        +float total_budget_inr
        +TravelStyle travel_style
        +List~str~ interests
        +int group_size
        +Optional~str~ travel_dates
        +str accommodation_preference
        +Optional~str~ persona
    }

    class PlanOption {
        +str label
        +str style
        +float estimated_total_inr
        +List~str~ highlights
        +List~str~ pros
        +List~str~ cons
        +bool recommended
    }

    class BudgetBreakdown {
        +str plan_label
        +List~BudgetCategory~ categories
        +float projected_total_inr
        +float remaining_buffer_inr
        +str optimization_notes
    }

    class BookingOption {
        +str type
        +str name
        +float cost_inr
        +Optional~str~ booking_url
        +Optional~str~ maps_url
        +Optional~float~ rating
    }

    class ItineraryPlan {
        +TravelerPreferences preferences
        +PlanOption selected_option
        +BudgetBreakdown budget_breakdown
        +BookingOption transport_booking
        +BookingOption hotel_booking
        +List~BookingOption~ activity_bookings
        +List~DayPlan~ days
        +float total_estimated_cost_inr
        +List~ContingencyPlan~ contingency_plans
    }

    class DayPlan {
        +int day_number
        +str title
        +List~TimeBlock~ blocks
        +float total_cost_inr
        +List~str~ highlights
    }

    class ContingencyPlan {
        +str risk
        +str likelihood
        +str description
        +str fallback_action
        +float budget_impact_inr
    }

    TravelerPreferences "1" --> "1..*" PlanOption
    PlanOption "1" --> "1" BudgetBreakdown
    BudgetBreakdown "1" --> "3..5" BookingOption
    ItineraryPlan "1" --> "1..*" DayPlan
    ItineraryPlan "1" --> "0..3" ContingencyPlan
```

---

## 🎭 Traveler Personas

The system supports 4 personas that shape every agent's decision:

| Persona | Focus | Budget Style | Activities |
|---------|-------|-------------|------------|
| 🎒 **Backpacker** | Max experiences per ₹ | Dormitory / hostels | Free activities, street food |
| 👨‍👩‍👧 **Family** | Safe & kid-friendly | Comfortable hotels | Easy activities, meal breaks |
| 🏔️ **Adrenaline Junkie** | High-intensity adventure | Any | Rafting, trekking, paragliding |
| 🧘 **Spiritual Seeker** | Inner peace | Ashrams / budget | Yoga, temples, meditation |

---

## 🖥️ UI Pages & Navigation

```mermaid
graph TD
    SIDEBAR[🗂️ Sidebar\nAgent Activity Log\nNavigation\nNew Trip Reset]

    P1[🏠 Plan Trip\nStage 0–4 Journey]
    P2[🗺️ Itinerary & Map\nInteractive Route Map\nDay-by-Day Cards]
    P3[💰 Budget\nBreakdown Charts\nSpend Analysis]
    P4[📋 Sample Plans\nPre-loaded Demo Trips]

    SIDEBAR --> P1
    SIDEBAR --> P2
    SIDEBAR --> P3
    SIDEBAR --> P4

    P1 -->|Stage 0| INPUT[Text Input + Persona Picker]
    P1 -->|Stage 1| CP1V[View 3 Plan Options + Debate Scores]
    P1 -->|Stage 2| CP2V[Budget Approval Table]
    P1 -->|Stage 3| CP3V[Booking Cart]
    P1 -->|Stage 4| FINAL[Trip Ready — Navigate to Itinerary]
```

---

## ⚙️ Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend / UI** | Streamlit (Python) |
| **LLM / AI Core** | OpenAI GPT-4o-mini |
| **Web Search** | Tavily Search API |
| **Weather** | OpenWeatherMap API |
| **Maps** | Folium + streamlit-folium |
| **Data Validation** | Pydantic v2 |
| **PDF Export** | FPDF2 |
| **Charts** | Plotly |
| **Environment** | python-dotenv |

---

## 🔄 Key Design Principles

1. **Agentic Workflow** — Each agent has a single responsibility and a structured JSON output
2. **Human-in-the-Loop (HITL)** — 3 explicit checkpoints where the user reviews and approves
3. **Graceful Fallbacks** — Every agent has a hardcoded fallback if LLM parsing fails
4. **Persona-Aware** — Traveler persona propagates through all agents from intent to itinerary
5. **Live Grounding** — Tavily web search and weather data reduce hallucinations
6. **Resilience First** — A dedicated agent proactively identifies risks and pre-generates Plan B options
7. **Dynamic Replanning** — Supports mid-trip itinerary changes without restarting the full pipeline

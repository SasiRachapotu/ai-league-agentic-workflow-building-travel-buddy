# ✈️ AI Travel Planning & Booking Agent
### AI League Hackathon — Multi-Agent Agentic Workflow

A **multi-agent AI system** that converts a natural language trip request into a complete, bookable travel package — with 3 human-in-the-loop approval checkpoints, interactive maps, budget charts, and a downloadable PDF itinerary.

---

## 🏗️ System Architecture

```
User Input (Natural Language)
        │
        ▼
┌─────────────────────────────────────────────────────┐
│              STREAMLIT ORCHESTRATOR                  │
│         (session_state stage machine)               │
└────┬──────────────────────────────────┬─────────────┘
     │                                  │
     ▼                                  ▼
┌──────────────┐                  ┌──────────────────┐
│ Intent Parser│                  │  Tavily Search   │
│  (OpenAI)    │                  │  Weather Tool    │
└──────┬───────┘                  └────────┬─────────┘
       │                                   │
       └──────────────┬────────────────────┘
                      ▼
           ┌──────────────────────┐
           │  CHECKPOINT 1: HITL  │◄── User picks A/B/C plan
           │  Plan Options (A/B/C)│
           └──────────┬───────────┘
                      ▼
           ┌──────────────────────┐
           │  CHECKPOINT 2: HITL  │◄── User approves budget
           │  Budget Allocation   │
           └──────────┬───────────┘
                      ▼
           ┌──────────────────────┐
           │  CHECKPOINT 3: HITL  │◄── User confirms bookings
           │  Booking Cart        │
           └──────────┬───────────┘
                      ▼
           ┌──────────────────────┐
           │  Itinerary Planner   │
           │  Day-by-day plan     │
           └──────────┬───────────┘
                      ▼
        ┌─────────────────────────────┐
        │  Map + PDF + JSON + Charts  │
        └─────────────────────────────┘
                      ↕
        ┌─────────────────────────────┐
        │  Replanning Agent (on-demand)│
        └─────────────────────────────┘
```

---

## 🤖 Agents (6 Specialized)

| Agent | File | Role |
|---|---|---|
| **Intent Parser** | `agents/intent_parser.py` | Natural language → structured preferences. Estimates budget if not given. |
| **Plan Options** | `agents/plan_options_agent.py` | Generates 3 distinct trip plans (A/B/C) with highlights, pros/cons |
| **Budget Optimizer** | `agents/budget_optimizer.py` | Splits budget across 8 categories (travel, stay, food, activities...) |
| **Booking Agent** | `agents/booking_agent.py` | Finds real bookable transport, hotel & activities with actual URLs |
| **Itinerary Planner** | `agents/itinerary_planner.py` | Builds day-by-day plan with time blocks, costs, maps, tips |
| **Replanning Agent** | `agents/replanning_agent.py` | Adjusts itinerary from natural language changes ("my train got delayed") |

---

## 🚀 Quick Start

### 1. Create & activate virtual environment
```bash
cd travel_agent
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API keys
```bash
cp .env.example .env
# Edit .env → add OPENAI_API_KEY=sk-...
```

Get your key at: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

### 4. Run the app
```bash
streamlit run app.py
```
Open **http://localhost:8501**

---

## 🔑 API Keys

| Key | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | ✅ Required | GPT-4o-mini for all agent reasoning |
| `TAVILY_API_KEY` | Optional | Live web search for real booking options |
| `OPENWEATHERMAP_API_KEY` | Optional | Live weather at destination |
| `GOOGLE_MAPS_API_KEY` | Optional | Enhanced place search |

> The app works with **only `OPENAI_API_KEY`** — other APIs enhance output with real-time data but are not required.

---

## 💬 Sample Queries

```
Plan a 4-day solo backpacking trip to Rishikesh under ₹15,000.
I love adventure sports and spiritual experiences. Traveling from Delhi next weekend.

Plan a 5-day family vacation to Goa with two kids. Budget ₹60,000.
We want beaches, water sports, seafood, and comfortable hotels. Flying from Mumbai.

Weekend getaway to Coorg from Bangalore. 2 days, budget ₹8,000.
Love nature, coffee estates, trekking. Solo trip.

Plan a trip to Nagpur for 7 days. Interested in culture, food and wildlife.
```

---

## 📁 Project Structure

```
travel_agent/
├── app.py                    # Streamlit UI + HITL flow
├── requirements.txt
├── .env.example
├── agents/
│   ├── intent_parser.py
│   ├── plan_options_agent.py
│   ├── budget_optimizer.py
│   ├── booking_agent.py
│   ├── itinerary_planner.py
│   └── replanning_agent.py
├── tools/
│   ├── openai_client.py      # GPT-4o-mini wrapper
│   ├── tavily_tool.py
│   └── weather_tool.py
├── models/schemas.py         # Pydantic data models
├── ui/
│   ├── map_view.py           # Folium interactive map
│   └── pdf_export.py         # fpdf2 PDF generation
└── samples/
    ├── rishikesh_solo.json
    ├── goa_family.json
    └── coorg_weekend.json
```

---

## ✨ Features

- 🤖 **6 Specialized Agents** — each with a distinct role and independent fallback logic
- ✋ **3 HITL Checkpoints** — user approves plan, budget, and bookings before proceeding
- 🗺️ **Interactive Map** — Folium map with day-wise color-coded routes and booking popups
- 💰 **Budget Charts** — Plotly donut chart + bar chart breakdown
- 📥 **PDF & JSON Export** — downloadable itinerary
- 🔁 **Dynamic Replanning** — natural language change requests update the itinerary live
- 🛡️ **Graceful Fallbacks** — every agent falls back to destination-aware defaults if LLM fails
- 📋 **3 Sample Plans** — pre-built demos for instant testing (Rishikesh, Goa, Coorg)

---

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| LLM | OpenAI GPT-4o-mini |
| UI | Streamlit |
| Maps | Folium + streamlit-folium |
| Charts | Plotly |
| PDF | fpdf2 |
| Data Models | Pydantic v2 |
| Web Search | Tavily |
| Environment | python-dotenv |

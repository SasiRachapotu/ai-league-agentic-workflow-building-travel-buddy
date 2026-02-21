# 🌍 AI Travel Planning & Booking Agent

A **multi-agent AI system** that plans your complete trip — from research to day-by-day itinerary — with 3 human-in-the-loop approval checkpoints.

## Features

- **9 Specialized Agents**: Intent Parser → Research → Plan Options → Budget Optimizer → Booking Agent → Itinerary Planner → Re-planning Agent
- **3 HITL Checkpoints**: Destination/Plan Selection → Budget Approval → Booking Cart Confirmation
- **Interactive Map**: Folium map with day-wise color-coded route and markers
- **PDF Download**: Professional itinerary PDF with budget, bookings, day plans
- **Dynamic Re-planning**: Natural language changes ("delay 3 hours", "reduce budget")
- **3 Sample Plans**: Pre-built plans for instant demo

## Quick Start

### 1. Install Dependencies
```bash
cd travel_agent
pip install -r requirements.txt
```

### 2. Configure API Keys
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY (required)
```

Get your free Gemini API key at: https://aistudio.google.com/app/apikey

### 3. Run the App
```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## API Keys

| Key | Required | Purpose | Free Tier |
|---|---|---|---|
| `OPENAI_API_KEY` | ✅ Required | LLM reasoning | — |
| `TAVILY_API_KEY` | Optional | Live web search | 1000/month |
| `OPENWEATHERMAP_API_KEY` | Optional | Live weather | 60 calls/min |
| `GOOGLE_MAPS_API_KEY` | Optional | Places search | Limited |

> The app works with **only OPENAI_API_KEY** — other APIs enhance results with real-time data.

## Sample Queries

```
Plan a 4-day solo backpacking trip to Rishikesh under ₹15,000.
I love adventure sports and spiritual experiences. Traveling from Delhi next weekend.

Plan a 5-day family vacation to Goa with two kids. Budget ₹60,000.
We want beaches, water sports, seafood, and comfortable hotels. Flying from Mumbai.

Weekend getaway to Coorg from Bangalore. 2 days, budget ₹8,000.
Love nature, coffee estates, trekking. Solo trip.
```

## Project Structure

```
travel_agent/
├── app.py                    # Streamlit main app (HITL flow)
├── agents/
│   ├── intent_parser.py      # Parse traveler preferences
│   ├── plan_options_agent.py # Generate A/B/C plan options
│   ├── budget_optimizer.py   # Smart budget allocation
│   ├── booking_agent.py      # Find bookable transport/hotels/activities
│   ├── itinerary_planner.py  # Day-by-day itinerary assembly
│   └── replanning_agent.py   # Dynamic itinerary changes
├── tools/
│   ├── gemini_client.py      # Gemini LLM client
│   ├── tavily_tool.py        # Web search
│   └── weather_tool.py       # OpenWeatherMap
├── models/
│   └── schemas.py            # All Pydantic data models
├── ui/
│   ├── map_view.py           # Folium interactive map
│   └── pdf_export.py         # PDF generation
└── samples/
    ├── rishikesh_solo.json
    ├── goa_family.json
    └── coorg_weekend.json
```

## Framework

- **LLM**: OpenAI GPT-4o-mini (swap to `gpt-4o` in `.env` for higher quality)
- **Agent Orchestration**: LangGraph-style state machine (implemented via Streamlit session_state)
- **Frontend**: Streamlit
- **Maps**: Folium + streamlit-folium
- **PDF**: fpdf2
- **Charts**: Plotly
- **Data Models**: Pydantic v2

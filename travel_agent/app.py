"""
AI Travel Planning & Booking Agent — Main Streamlit App
Multi-agent system with 3 HITL checkpoints and dynamic replanning.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Travel Agent",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main { background: #f8faff; }

.hero-banner {
    background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #0ea5e9 100%);
    border-radius: 16px; padding: 32px 40px; color: white; margin-bottom: 24px;
    box-shadow: 0 8px 32px rgba(30, 58, 138, 0.3);
}
.hero-banner h1 { font-size: 2.2rem; font-weight: 700; margin: 0 0 6px 0; }
.hero-banner p { font-size: 1rem; opacity: 0.85; margin: 0; }

.agent-card {
    background: white; border-radius: 12px; padding: 16px 20px;
    border-left: 4px solid #2563eb; margin: 8px 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.agent-card.done { border-left-color: #22c55e; }
.agent-card.running { border-left-color: #f59e0b; animation: pulse 1.5s infinite; }
.agent-card.error { border-left-color: #ef4444; }

.plan-card {
    background: white; border-radius: 16px; padding: 20px 24px;
    border: 2px solid #e2e8f0; cursor: pointer; transition: all 0.25s;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04); margin-bottom: 12px;
}
.plan-card:hover { border-color: #2563eb; box-shadow: 0 6px 24px rgba(37,99,235,0.15); transform: translateY(-2px); }
.plan-card.recommended { border-color: #22c55e; background: #f0fdf4; }

.plan-label {
    font-size: 1.4rem; font-weight: 700; color: #1e3a8a; display: inline-block;
    background: #dbeafe; border-radius: 8px; padding: 2px 12px; margin-bottom: 8px;
}
.plan-label.rec { background: #dcfce7; color: #15803d; }

.budget-table { width: 100%; border-collapse: collapse; }
.budget-table th { background: #1e3a8a; color: white; padding: 10px 14px; text-align: left; }
.budget-table td { padding: 9px 14px; border-bottom: 1px solid #e2e8f0; color: #0f172a !important; background: #ffffff !important; }
.budget-table tr:nth-child(even) td { background: #f0f4ff !important; color: #0f172a !important; }
.budget-total td { background: #1e3a8a !important; color: white !important; font-weight: 700; }

.booking-card {
    background: #ffffff !important; border-radius: 12px; padding: 16px 20px;
    border: 1px solid #e2e8f0; margin-bottom: 12px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.05); color: #0f172a !important;
}
.booking-card h4 { color: #1e3a8a !important; margin: 0 0 8px 0; font-size: 1rem; }
.booking-card b { color: #0f172a !important; }
.booking-card span, .booking-card div { color: #0f172a !important; }

.day-card {
    background: white; border-radius: 16px; padding: 20px 24px;
    margin-bottom: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    border-top: 4px solid #2563eb;
}
.day-title { font-size: 1.15rem; font-weight: 700; color: #1e3a8a; margin-bottom: 12px; }

.time-block {
    background: #f8faff; border-radius: 10px; padding: 12px 16px;
    margin-bottom: 10px; border-left: 3px solid #0ea5e9;
}
.time-label { font-size: 0.78rem; color: #64748b; font-weight: 500; }
.activity-name { font-size: 0.97rem; font-weight: 600; color: #0f172a; }
.activity-desc { font-size: 0.87rem; color: #475569; margin: 4px 0; }

.checkpoint-banner {
    background: linear-gradient(135deg, #fef3c7, #fde68a);
    border-radius: 12px; padding: 16px 20px; margin: 16px 0;
    border: 1px solid #f59e0b;
}
.checkpoint-banner h3 { color: #92400e; margin: 0 0 4px 0; }
.checkpoint-banner p { color: #78350f; margin: 0; font-size: 0.9rem; }

.replan-box {
    background: linear-gradient(135deg, #ede9fe, #ddd6fe);
    border-radius: 12px; padding: 16px 20px; margin: 16px 0;
    border: 1px solid #7c3aed;
}

.tip-card {
    background: linear-gradient(135deg, #f0fdf4, #dcfce7);
    border-radius: 10px; padding: 10px 14px; margin: 6px 0;
    border-left: 3px solid #22c55e; font-size: 0.9rem; color: #166534;
}

.stat-box {
    background: white; border-radius: 12px; padding: 16px; text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06); border: 1px solid #e2e8f0;
}
.stat-value { font-size: 1.5rem; font-weight: 700; color: #1e3a8a; }
.stat-label { font-size: 0.8rem; color: #64748b; }

.badge {
    display: inline-block; background: #dbeafe; color: #1e40af;
    border-radius: 20px; padding: 2px 10px; font-size: 0.78rem; font-weight: 500;
    margin: 2px;
}

@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
</style>
""", unsafe_allow_html=True)


# ── Session State Init ───────────────────────────────────────────────────────
def init_state():
    defaults = {
        "stage": 0,
        "preferences": None,
        "plan_options": None,
        "selected_option": None,
        "budget": None,
        "transport": None,
        "hotel": None,
        "activities": None,
        "itinerary": None,
        "agent_logs": [],
        "replan_history": [],
        "active_tab": "🏠 Plan Trip",
        "demo_mode": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ── Helper: Add Agent Log ────────────────────────────────────────────────────
def add_log(agent: str, status: str, message: str, details: str = ""):
    st.session_state.agent_logs.append({
        "agent": agent, "status": status,
        "message": message, "details": details,
        "time": datetime.now().strftime("%H:%M:%S"),
    })


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 12px 0 4px 0;">
        <span style="font-size:2.5rem">✈️</span>
        <h2 style="margin:4px 0; color:#1e3a8a;">AI Travel Agent</h2>
        <p style="font-size:0.8rem; color:#64748b;">Multi-Agent Planning System</p>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    # Navigation
    tab = st.radio(
        "Navigate",
        ["🏠 Plan Trip", "🗺️ Itinerary & Map", "💰 Budget", "📋 Sample Plans"],
        index=["🏠 Plan Trip", "🗺️ Itinerary & Map", "💰 Budget", "📋 Sample Plans"].index(st.session_state.active_tab),
    )
    st.session_state.active_tab = tab

    st.divider()

    # Agent Log Panel
    st.markdown("### 🤖 Agent Activity Log")
    if not st.session_state.agent_logs:
        st.info("Agents will appear here as they work...")
    else:
        for log in reversed(st.session_state.agent_logs[-10:]):
            icon = "✅" if log["status"] == "done" else ("⚡" if log["status"] == "running" else "❌")
            color = "#22c55e" if log["status"] == "done" else ("#f59e0b" if log["status"] == "running" else "#ef4444")
            st.markdown(f"""
            <div style="background:white;border-left:3px solid {color};padding:6px 10px;
                        border-radius:6px;margin:4px 0;font-size:0.8rem;color:#0f172a;">
                {icon} <b style="color:#0f172a;">{log['agent']}</b><br/>
                <span style="color:#64748b;">{log['time']}</span>
                <span style="color:#334155;"> — {log['message']}</span>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # Reset button
    if st.button("🔄 Start New Trip", use_container_width=True):
        for key in ["stage", "preferences", "plan_options", "selected_option",
                    "budget", "transport", "hotel", "activities", "itinerary",
                    "agent_logs", "replan_history"]:
            st.session_state[key] = None if key not in [
                "stage", "agent_logs", "replan_history"
            ] else (0 if key == "stage" else [])
        st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# PAGE: Plan Trip
# ════════════════════════════════════════════════════════════════════════════
if st.session_state.active_tab == "🏠 Plan Trip":

    # Hero Banner
    st.markdown("""
    <div class="hero-banner">
        <h1>✈️ AI Travel Planning Agent</h1>
        <p>Multi-agent system that plans your entire trip — research, bookings, day-by-day itinerary, budget optimization. All with human-in-the-loop approvals.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── STAGE 0: Input ───────────────────────────────────────────────────────
    if st.session_state.stage == 0:
        st.markdown("### 🧳 Tell me about your trip")

        col1, col2 = st.columns([3, 1])
        with col1:
            user_input = st.text_area(
                "Describe your trip",
                placeholder='e.g. "Plan a 4-day solo backpacking trip to Rishikesh under ₹15,000. I love adventure sports and spiritual experiences. Traveling from Delhi next weekend."',
                height=100,
                label_visibility="collapsed",
            )
        with col2:
            st.markdown("<br/>", unsafe_allow_html=True)
            plan_btn = st.button("🚀 Start Planning", use_container_width=True, type="primary")

        # Quick example chips
        st.markdown("**Quick Examples:**")
        ex_col1, ex_col2, ex_col3 = st.columns(3)
        with ex_col1:
            if st.button("🏕️ Rishikesh Solo", use_container_width=True):
                user_input = "Plan a 4-day solo backpacking trip to Rishikesh under ₹15,000. I love adventure sports and spiritual experiences. Traveling from Delhi next weekend. I prefer budget stays and local food."
                plan_btn = True
        with ex_col2:
            if st.button("🌴 Goa Family", use_container_width=True):
                user_input = "Plan a 5-day family vacation to Goa with two kids. Budget ₹60,000. We want beaches, water sports, seafood, and comfortable hotels. Flying from Mumbai."
                plan_btn = True
        with ex_col3:
            if st.button("🌿 Coorg Weekend", use_container_width=True):
                user_input = "Weekend getaway to Coorg from Bangalore. 2 days, budget ₹8,000. Love nature, coffee estates, trekking. Solo trip."
                plan_btn = True

        if plan_btn and user_input:
            with st.spinner("🤖 AI agents are researching your trip..."):
                try:
                    # Intent Parser
                    add_log("Intent Parser", "running", "Parsing your travel preferences...")
                    from agents import intent_parser
                    prefs = intent_parser.run(user_input, date_context="February 2026")
                    st.session_state.preferences = prefs
                    add_log("Intent Parser", "done", f"Parsed: {prefs.destination}, {prefs.duration_days} days, ₹{prefs.total_budget_inr:,.0f}")

                    # Plan Options Agent
                    add_log("Plan Options Agent", "running", f"Generating 3 plan options for {prefs.destination}...")
                    from agents import plan_options_agent
                    options = plan_options_agent.run(prefs)
                    st.session_state.plan_options = options
                    add_log("Plan Options Agent", "done", f"Generated {len(options)} options (A/B/C)")

                    st.session_state.stage = 1
                    st.rerun()
                except ValueError as e:
                    st.error(f"⚠️ {e}\n\nAdd your OPENAI_API_KEY to the .env file and restart.")
                except Exception as e:
                    st.error(f"Agent error: {e}")

    # ── STAGE 1: Checkpoint 1 — Plan Options ────────────────────────────────
    elif st.session_state.stage == 1:
        prefs = st.session_state.preferences
        options = st.session_state.plan_options

        st.markdown("""
        <div class="checkpoint-banner">
            <h3>🧾 Review Checkpoint 1: Destination & Plan Direction</h3>
            <p>Choose one of the 3 plan options below. The system recommends Option A.</p>
        </div>
        """, unsafe_allow_html=True)

        # Trip Understanding Card
        st.markdown("#### ✨ Trip Understanding")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="stat-box"><div class="stat-value">📍 {prefs.destination}</div><div class="stat-label">Destination</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="stat-box"><div class="stat-value">🗓️ {prefs.duration_days}d</div><div class="stat-label">Duration</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="stat-box"><div class="stat-value">💰 ₹{prefs.total_budget_inr:,.0f}</div><div class="stat-label">Budget</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="stat-box"><div class="stat-value">👤 {prefs.group_size}</div><div class="stat-label">Travelers</div></div>', unsafe_allow_html=True)

        st.markdown(f"**Interests:** " + " ".join([f'<span class="badge">🏷️ {i}</span>' for i in prefs.interests]), unsafe_allow_html=True)
        st.markdown(f"**Travel Dates:** {prefs.travel_dates or 'Flexible'}  |  **From:** {prefs.origin}")

        # Show notice if AI estimated the budget (user didn't mention one)
        raw_lower = (prefs.raw_input or "").lower()
        budget_mentioned = any(kw in raw_lower for kw in ["₹", "inr", "budget", "rs.", "rupee", "k budget", "thousand"])
        if not budget_mentioned and prefs.total_budget_inr > 0:
            st.info(f"💡 **Budget not specified** — AI estimated **₹{prefs.total_budget_inr:,.0f}** based on your travel style and duration. You can adjust this by mentioning a budget in your query.")

        st.markdown("---")
        st.markdown("#### 🗺️ Choose Your Plan")

        for opt in options:
            is_rec = opt.recommended
            label_class = "rec" if is_rec else ""
            card_class = "plan-card recommended" if is_rec else "plan-card"
            # Pre-compute badge so f-string never has a blank line (Streamlit bug workaround)
            rec_badge = '<span style="background:#bbf7d0;color:#15803d;border-radius:20px;padding:2px 10px;font-size:0.78rem;font-weight:600;margin-left:8px;">⭐ Recommended</span>' if is_rec else '<span></span>'
            highlights_str = " · ".join(opt.highlights)
            pros_str = " · ".join(opt.pros)
            cons_str = " · ".join(opt.cons)
            cost_str = f"₹{opt.estimated_total_inr:,.0f}" if opt.estimated_total_inr else "See details"

            with st.container():
                st.markdown(f"""<div class="{card_class}">
<span class="plan-label {label_class}">Option {opt.label}</span> {rec_badge}
<h4 style="margin:6px 0 4px;color:#0f172a;">{opt.style}</h4>
<div style="font-size:1.1rem;font-weight:700;color:#1e3a8a;margin-bottom:8px;">{cost_str}</div>
<b>Highlights:</b> {highlights_str}<br/>
<span style="color:#16a34a">✓ {pros_str}</span><br/>
<span style="color:#dc2626">✗ {cons_str}</span>
</div>""", unsafe_allow_html=True)

                if st.button(f"✅ Select Option {opt.label}", key=f"select_{opt.label}", use_container_width=True, type="primary" if is_rec else "secondary"):
                    add_log("Orchestrator", "running", f"User selected Option {opt.label} — {opt.style}")
                    with st.spinner("💰 Running Budget Optimizer..."):
                        from agents import budget_optimizer
                        budget = budget_optimizer.run(prefs, opt)
                        st.session_state.selected_option = opt
                        st.session_state.budget = budget
                        add_log("Budget Optimizer", "done", f"Budget allocated: ₹{budget.projected_total_inr:,.0f} / ₹{prefs.total_budget_inr:,.0f}")
                        st.session_state.stage = 2
                        st.rerun()

    # ── STAGE 2: Checkpoint 2 — Budget Approval ──────────────────────────────
    elif st.session_state.stage == 2:
        prefs = st.session_state.preferences
        opt = st.session_state.selected_option
        budget = st.session_state.budget

        st.markdown("""
        <div class="checkpoint-banner">
            <h3>🧾 Review Checkpoint 2: Budget Allocation Approval</h3>
            <p>Review the proposed budget breakdown and approve or go back to choose a different plan.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"**Selected:** Option {opt.label} — {opt.style}")

        # Budget table
        table_rows = ""
        for cat in budget.categories:
            pct = int(cat.amount_inr / max(prefs.total_budget_inr, 1) * 100)
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            table_rows += f"<tr><td><b>{cat.category}</b></td><td>₹{cat.amount_inr:,.0f}</td><td style='font-size:0.8rem;color:#64748b;'>{cat.description}</td><td style='font-family:monospace;font-size:0.75rem;color:#2563eb;'>{bar} {pct}%</td></tr>"

        st.markdown(f"""
        <table class="budget-table">
            <thead><tr><th>Category</th><th>Amount</th><th>Details</th><th>% of Budget</th></tr></thead>
            <tbody>{table_rows}</tbody>
            <tr class="budget-total">
                <td colspan="1"><b>Projected Total</b></td>
                <td colspan="1">₹{budget.projected_total_inr:,.0f}</td>
                <td colspan="2">Buffer remaining: ₹{budget.remaining_buffer_inr:,.0f}</td>
            </tr>
        </table>
        """, unsafe_allow_html=True)

        st.markdown(f"💡 **Optimization Notes:** {budget.optimization_notes}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Approve Budget & Find Bookings", type="primary", use_container_width=True):
                add_log("Orchestrator", "running", "Budget approved — fetching booking options...")
                with st.spinner("🔍 Booking Agent searching for flights, hotels, activities..."):
                    from agents import booking_agent
                    transport, hotel, activities = booking_agent.run(prefs, opt, budget)
                    st.session_state.transport = transport
                    st.session_state.hotel = hotel
                    st.session_state.activities = activities
                    add_log("Booking Agent", "done", f"Found: {transport.name} + {hotel.name} + {len(activities)} activities")
                    st.session_state.stage = 3
                    st.rerun()
        with col2:
            if st.button("← Back to Plan Options", use_container_width=True):
                st.session_state.stage = 1
                st.rerun()

    # ── STAGE 3: Checkpoint 3 — Booking Cart ─────────────────────────────────
    elif st.session_state.stage == 3:
        prefs = st.session_state.preferences
        transport = st.session_state.transport
        hotel = st.session_state.hotel
        activities = st.session_state.activities
        budget = st.session_state.budget
        nights = prefs.duration_days - 1

        st.markdown("""
        <div class="checkpoint-banner">
            <h3>🧾 Review Checkpoint 3: Booking Cart Confirmation</h3>
            <p>Review the booking options below. Confirm to generate your complete itinerary.</p>
        </div>
        """, unsafe_allow_html=True)

        # Transport
        st.markdown("#### 🚆 Transport Option")
        st.markdown(f"""
        <div class="booking-card">
            <h4>🚆 {transport.name}</h4>
            <b>Route:</b> {transport.location or f'{prefs.origin} → {prefs.destination}'}<br/>
            <b>Cost:</b> ₹{transport.cost_inr:,.0f} per person &nbsp; | &nbsp; <b>Duration:</b> {transport.duration or '—'}<br/>
            {'<b>Notes:</b> ' + transport.notes + '<br/>' if transport.notes else ''}
            <a href="{transport.booking_url}" target="_blank">🔗 Book Now — {transport.booking_url}</a>
        </div>
        """, unsafe_allow_html=True)

        # Hotel
        st.markdown("#### 🏨 Stay Option")
        st.markdown(f"""
        <div class="booking-card">
            <h4>🏨 {hotel.name}</h4>
            <b>Location:</b> {hotel.location or prefs.destination}<br/>
            <b>Cost:</b> ₹{hotel.cost_inr:,.0f}/night × {nights} nights = ₹{hotel.cost_inr * nights:,.0f}<br/>
            {'<b>Rating:</b> ⭐ ' + str(hotel.rating) + '/5<br/>' if hotel.rating else ''}
            {'<b>Features:</b> ' + hotel.notes + '<br/>' if hotel.notes else ''}
            <a href="{hotel.booking_url}" target="_blank">🔗 Book Now — {hotel.booking_url}</a>
            {('&nbsp; | &nbsp; <a href="' + hotel.maps_url + '" target="_blank">📍 View on Map</a>') if hotel.maps_url else ''}
        </div>
        """, unsafe_allow_html=True)

        # Activities
        st.markdown("#### 🎯 Activity Options")
        for act in activities:
            st.markdown(f"""
            <div class="booking-card">
                <h4>🎯 {act.name}</h4>
                <b>Description:</b> {act.description}<br/>
                <b>Cost:</b> {'Free' if act.cost_inr == 0 else f'₹{act.cost_inr:,.0f}'} &nbsp;
                {('| <b>Duration:</b> ' + act.duration) if act.duration else ''}<br/>
                {('<b>Location:</b> ' + act.location + '<br/>') if act.location else ''}
                {'<b>Tips:</b> ' + act.notes + '<br/>' if act.notes else ''}
                <a href="{act.booking_url}" target="_blank">🔗 Book / Info</a>
                {('&nbsp; | &nbsp; <a href="' + act.maps_url + '" target="_blank">📍 Map</a>') if act.maps_url else ''}
            </div>
            """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirm & Generate Full Itinerary", type="primary", use_container_width=True):
                add_log("Orchestrator", "running", "Booking confirmed — building day-by-day itinerary...")
                with st.spinner("🗓️ Itinerary Planner building your day-by-day plan..."):
                    from agents import itinerary_planner
                    itinerary = itinerary_planner.run(
                        prefs,
                        st.session_state.selected_option,
                        budget,
                        transport, hotel, activities,
                    )
                    st.session_state.itinerary = itinerary
                    add_log("Itinerary Planner", "done", f"Complete! {len(itinerary.days)} days planned, ₹{itinerary.total_estimated_cost_inr:,.0f} total")
                    st.session_state.stage = 4
                    st.session_state.active_tab = "🗺️ Itinerary & Map"
                    st.rerun()
        with col2:
            if st.button("← Back to Budget", use_container_width=True):
                st.session_state.stage = 2
                st.rerun()

    # ── STAGE 4: Done — prompt to see itinerary ──────────────────────────────
    elif st.session_state.stage == 4:
        st.success("✅ Your complete Trip Execution Package is ready!")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗺️ View Full Itinerary & Map", type="primary", use_container_width=True):
                st.session_state.active_tab = "🗺️ Itinerary & Map"
                st.rerun()
        with col2:
            if st.button("💰 View Budget Breakdown", use_container_width=True):
                st.session_state.active_tab = "💰 Budget"
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════
# PAGE: Itinerary & Map
# ════════════════════════════════════════════════════════════════════════════
elif st.session_state.active_tab == "🗺️ Itinerary & Map":
    if not st.session_state.itinerary:
        st.info("No itinerary yet. Go to **🏠 Plan Trip** to plan your trip first!")
    else:
        itinerary = st.session_state.itinerary
        prefs = itinerary.preferences

        st.markdown(f"""
        <div class="hero-banner">
            <h1>📍 {prefs.destination} — {prefs.duration_days}-Day Trip</h1>
            <p>✈️ From {prefs.origin} &nbsp;|&nbsp; 🗓️ {prefs.travel_dates or 'As planned'} &nbsp;|&nbsp;
               💰 ₹{itinerary.total_estimated_cost_inr:,.0f} used &nbsp;|&nbsp;
               🟢 ₹{itinerary.remaining_budget_inr:,.0f} remaining</p>
        </div>
        """, unsafe_allow_html=True)

        # Downloads
        dl_col1, dl_col2, dl_col3 = st.columns(3)
        with dl_col1:
            try:
                from ui.pdf_export import generate_pdf
                pdf_bytes = generate_pdf(itinerary)
                st.download_button("📥 Download PDF", data=pdf_bytes,
                                   file_name=f"{prefs.destination.replace(' ','_')}_itinerary.pdf",
                                   mime="application/pdf", use_container_width=True)
            except Exception as e:
                st.warning(f"PDF unavailable: {e}")
        with dl_col2:
            json_str = itinerary.model_dump_json(indent=2)
            st.download_button("📄 Download JSON", data=json_str,
                               file_name=f"{prefs.destination.replace(' ','_')}_itinerary.json",
                               mime="application/json", use_container_width=True)
        with dl_col3:
            st.button("📊 View Budget →", on_click=lambda: st.session_state.update({"active_tab": "💰 Budget"}), use_container_width=True)

        st.markdown("---")

        # Map
        st.markdown("### 🗺️ Interactive Route Map")
        try:
            from ui.map_view import build_map
            from streamlit_folium import st_folium
            m = build_map(itinerary)
            st_folium(m, width=None, height=450, returned_objects=[])
        except Exception as e:
            st.warning(f"Map unavailable: {e}")

        st.markdown("---")

        # Day-by-Day Itinerary
        st.markdown("### 🗓️ Day-by-Day Itinerary")

        DAY_COLORS_CSS = ["#2563eb", "#16a34a", "#9333ea", "#ea580c", "#0891b2", "#be123c"]

        for day in itinerary.days:
            color = DAY_COLORS_CSS[(day.day_number - 1) % len(DAY_COLORS_CSS)]
            st.markdown(f"""
            <div class="day-card" style="border-top-color:{color}">
                <div class="day-title" style="color:{color}">
                    {day.title} &nbsp;
                    <span style="font-size:0.85rem;font-weight:400;color:#64748b;">
                        Estimated: ₹{day.total_cost_inr:,.0f}
                    </span>
                </div>
                {"".join([f'<span class="badge" style="background:{color}22;color:{color};">⭐ {h}</span>' for h in day.highlights]) if day.highlights else ""}
            </div>
            """, unsafe_allow_html=True)

            for block in day.blocks:
                col1, col2 = st.columns([5, 1])
                with col1:
                    tips_html = f'<div style="color:#15803d;font-size:0.82rem;">💡 {block.tips}</div>' if block.tips else ""
                    maps_link = f'<a href="{block.maps_url}" target="_blank" style="font-size:0.82rem;">📍 View on Map</a>' if block.maps_url else ""
                    book_link = f'<a href="{block.booking_url}" target="_blank" style="font-size:0.82rem;margin-left:12px;">🔗 Book</a>' if block.booking_url else ""
                    st.markdown(f"""
                    <div class="time-block" style="border-left-color:{color}">
                        <div class="time-label">⏰ {block.time}</div>
                        <div class="activity-name">{block.activity}</div>
                        <div class="activity-desc">{block.description}</div>
                        <div style="margin-top:4px;">
                            <span style="font-size:0.82rem;font-weight:600;color:#1e3a8a;">
                                {'Free' if block.cost_inr == 0 else f'💰 ₹{block.cost_inr:,.0f}'}
                            </span>
                            &nbsp;{maps_link}{book_link}
                        </div>
                        {tips_html}
                    </div>
                    """, unsafe_allow_html=True)

        # Insider Tips
        if itinerary.insider_tips:
            st.markdown("### 💡 Insider Tips")
            for tip in itinerary.insider_tips:
                st.markdown(f'<div class="tip-card">💡 {tip}</div>', unsafe_allow_html=True)

        # Booking Checklist
        if itinerary.booking_checklist:
            st.markdown("### 📌 Booking Checklist")
            for item in itinerary.booking_checklist:
                st.checkbox(item, key=f"check_{item[:20]}")

        # ── Dynamic Replanning ───────────────────────────────────────────────
        st.markdown("---")
        st.markdown("""
        <div class="replan-box">
            <h3 style="color:#4c1d95;margin:0 0 4px 0;">🔁 Dynamic Re-planning</h3>
            <p style="margin:0;color:#5b21b6;font-size:0.9rem;">
                Changed plans? Tell the AI agent and it will adjust your itinerary automatically.
            </p>
        </div>
        """, unsafe_allow_html=True)

        change_request = st.text_input(
            "What changed?",
            placeholder='e.g. "My train got delayed by 3 hours" or "Reduce budget by ₹3,000" or "Add a yoga session on Day 2"',
        )
        if st.button("🔁 Re-plan Now", type="primary") and change_request:
            with st.spinner("🤖 Replanning Agent adjusting your itinerary..."):
                add_log("Replanning Agent", "running", f"Processing: {change_request}")
                from agents import replanning_agent
                result = replanning_agent.run(st.session_state.itinerary, change_request)

                # Apply updated days to itinerary
                updated_map = {d.day_number: d for d in result.get("updated_days", [])}
                new_days = []
                for d in st.session_state.itinerary.days:
                    new_days.append(updated_map.get(d.day_number, d))
                st.session_state.itinerary.days = new_days

                st.session_state.replan_history.append({
                    "request": change_request,
                    "summary": result.get("changes_summary", ""),
                    "budget_impact": result.get("budget_impact_inr", 0),
                })
                add_log("Replanning Agent", "done", f"Re-planned: {result.get('changes_summary', '')[:60]}...")

                st.success(f"✅ {result.get('changes_summary', 'Itinerary updated')}")
                if result.get("alternatives_offered"):
                    st.info("**Alternatives:** " + " | ".join(result["alternatives_offered"]))
                if result.get("budget_impact_inr", 0) != 0:
                    impact = result["budget_impact_inr"]
                    st.warning(f"💰 Budget impact: {'+ ₹' if impact > 0 else '- ₹'}{abs(impact):,.0f}")
                st.rerun()

        # Replan history
        if st.session_state.replan_history:
            with st.expander("📜 Re-planning History"):
                for i, rp in enumerate(st.session_state.replan_history):
                    st.markdown(f"**{i+1}. Change:** {rp['request']}")
                    st.markdown(f"   **Result:** {rp['summary']}")
                    if rp.get("budget_impact", 0):
                        st.markdown(f"   **Budget Impact:** ₹{rp['budget_impact']:,}")
                    st.markdown("---")


# ════════════════════════════════════════════════════════════════════════════
# PAGE: Budget
# ════════════════════════════════════════════════════════════════════════════
elif st.session_state.active_tab == "💰 Budget":
    if not st.session_state.itinerary:
        st.info("No budget yet. Plan your trip first!")
    else:
        itinerary = st.session_state.itinerary
        prefs = itinerary.preferences
        budget = itinerary.budget_breakdown

        st.markdown("## 💰 Budget Breakdown")

        # Summary stats
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="stat-box"><div class="stat-value">₹{prefs.total_budget_inr:,.0f}</div><div class="stat-label">Total Budget</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="stat-box"><div class="stat-value">₹{itinerary.total_estimated_cost_inr:,.0f}</div><div class="stat-label">Estimated Total</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="stat-box"><div class="stat-value" style="color:#22c55e">₹{itinerary.remaining_budget_inr:,.0f}</div><div class="stat-label">Remaining Buffer</div></div>', unsafe_allow_html=True)
        with c4:
            pct = int(itinerary.total_estimated_cost_inr / prefs.total_budget_inr * 100)
            st.markdown(f'<div class="stat-box"><div class="stat-value">{pct}%</div><div class="stat-label">Budget Used</div></div>', unsafe_allow_html=True)

        st.markdown("---")

        chart_col, table_col = st.columns([1, 1])

        with chart_col:
            st.markdown("### 🍩 Budget Distribution")
            fig = px.pie(
                names=[c.category for c in budget.categories],
                values=[c.amount_inr for c in budget.categories],
                color_discrete_sequence=px.colors.qualitative.Set3,
                hole=0.45,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(
                showlegend=False, margin=dict(t=10, b=10, l=10, r=10),
                height=350,
            )
            st.plotly_chart(fig, use_container_width=True)

        with table_col:
            st.markdown("### 📋 Category Breakdown")
            fig2 = go.Figure(go.Bar(
                x=[c.amount_inr for c in budget.categories],
                y=[c.category for c in budget.categories],
                orientation="h",
                marker_color="#2563eb",
                text=[f"₹{c.amount_inr:,.0f}" for c in budget.categories],
                textposition="outside",
            ))
            fig2.update_layout(
                xaxis_title="Amount (₹)", height=350,
                margin=dict(t=10, b=10, l=10, r=80),
                xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
            )
            st.plotly_chart(fig2, use_container_width=True)

        # Day-wise cost breakdown
        st.markdown("### 📅 Day-wise Cost")
        day_labels = [d.title for d in itinerary.days]
        day_costs = [d.total_cost_inr for d in itinerary.days]
        fig3 = px.bar(x=day_labels, y=day_costs,
                      color=day_costs, color_continuous_scale="Blues",
                      labels={"x": "Day", "y": "Cost (₹)"})
        fig3.update_layout(height=280, coloraxis_showscale=False,
                           margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig3, use_container_width=True)

        # Table
        st.markdown("### 📊 Full Budget Table")
        table_rows = ""
        for cat in budget.categories:
            table_rows += f"""
            <tr>
                <td><b>{cat.category}</b></td>
                <td style="text-align:right">₹{cat.amount_inr:,.0f}</td>
                <td>{cat.description}</td>
            </tr>"""
        st.markdown(f"""
        <table class="budget-table">
            <thead><tr><th>Category</th><th>Amount</th><th>Details</th></tr></thead>
            <tbody>{table_rows}</tbody>
            <tr class="budget-total">
                <td><b>Total</b></td>
                <td><b>₹{budget.projected_total_inr:,.0f}</b></td>
                <td>Buffer: ₹{budget.remaining_buffer_inr:,.0f}</td>
            </tr>
        </table>
        """, unsafe_allow_html=True)

        st.markdown(f"**💡 Optimization Notes:** {budget.optimization_notes}")


# ════════════════════════════════════════════════════════════════════════════
# PAGE: Sample Plans
# ════════════════════════════════════════════════════════════════════════════
elif st.session_state.active_tab == "📋 Sample Plans":
    st.markdown("## 📋 Sample Trip Plans")
    st.markdown("Load a pre-built sample plan to see the full system in action.")

    SAMPLES = {
        "🏕️ Solo Backpacking — Rishikesh (4 days, ₹15,000)": "samples/rishikesh_solo.json",
        "🌴 Family Vacation — Goa (5 days, ₹60,000)": "samples/goa_family.json",
        "🌿 Weekend Getaway — Coorg (2 days, ₹8,000)": "samples/coorg_weekend.json",
    }

    for label, path in SAMPLES.items():
        with st.expander(label):
            full_path = os.path.join(os.path.dirname(__file__), path)
            if os.path.exists(full_path):
                with open(full_path) as f:
                    data = json.load(f)
                st.json(data, expanded=False)
                if st.button(f"Load this plan", key=label):
                    try:
                        from models.schemas import ItineraryPlan
                        itinerary = ItineraryPlan(**data)
                        st.session_state.itinerary = itinerary
                        st.session_state.stage = 4
                        st.session_state.active_tab = "🗺️ Itinerary & Map"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to load: {e}")
            else:
                st.info("Sample file will be available after first run.")

    # Architecture diagram
    st.markdown("---")
    st.markdown("## 🏗️ System Architecture")
    st.markdown("""
    ```
    User Input (Natural Language)
         │
         ▼
    ┌─────────────────────────────────────────────────────┐
    │              ORCHESTRATOR AGENT                      │
    │         (LangGraph State Machine)                   │
    └─────┬──────────────────────────────────┬────────────┘
          │                                  │
          ▼                                  ▼
    ┌──────────────┐                  ┌──────────────────┐
    │ Intent Parser│                  │  Research Agent  │
    │   (Gemini)   │                  │ (Tavily + OWM)   │
    └──────┬───────┘                  └────────┬─────────┘
           │                                   │
           └──────────────┬────────────────────┘
                          │
               ┌──────────▼───────────┐
               │  CHECKPOINT 1: HITL  │◄── User picks A/B/C plan
               │  Plan Options (A/B/C)│
               └──────────┬───────────┘
                          │
               ┌──────────▼───────────┐
               │  Budget Optimizer    │
               │  (Gemini + rules)    │
               └──────────┬───────────┘
                          │
               ┌──────────▼───────────┐
               │  CHECKPOINT 2: HITL  │◄── User approves budget
               │  Budget Allocation   │
               └──────────┬───────────┘
                          │
               ┌──────────▼───────────┐
               │   Booking Agent      │
               │ (Tavily + real URLs) │
               └──────────┬───────────┘
                          │
               ┌──────────▼───────────┐
               │  CHECKPOINT 3: HITL  │◄── User confirms bookings
               │  Booking Cart        │
               └──────────┬───────────┘
                          │
               ┌──────────▼───────────┐
               │  Itinerary Planner   │
               │  (Gemini + Tavily)   │
               └──────────┬───────────┘
                          │
               ┌──────────▼───────────┐
               │  Trip Execution Pkg  │
               │  PDF + Map + JSON    │
               └──────────┬───────────┘
                          │
               ┌──────────▼───────────┐
               │   Replanning Agent   │◄── Dynamic changes anytime
               │   (Natural language) │
               └──────────────────────┘
    ```
    """)

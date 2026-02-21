"""
Interactive map view using Folium.
Renders a day-wise color-coded route map with markers and popups.
"""
import folium
from models.schemas import ItineraryPlan

# Day color palette
DAY_COLORS = ["red", "blue", "green", "purple", "orange", "darkred", "cadetblue", "darkgreen", "darkpurple"]

# Known destination coordinates (fallback when geocoding unavailable)
KNOWN_COORDS = {
    "Rishikesh": (30.0869, 78.2676),
    "Goa": (15.2993, 74.1240),
    "Coorg": (12.3375, 75.8069),
    "Delhi": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777),
    "Jaipur": (26.9124, 75.7873),
    "Agra": (27.1767, 78.0081),
    "Manali": (32.2432, 77.1892),
    "Shimla": (31.1048, 77.1734),
    "Kerala": (10.8505, 76.2711),
    "Varanasi": (25.3176, 82.9739),
    "Udaipur": (24.5854, 73.7125),
    "Darjeeling": (27.0360, 88.2627),
    "Andaman": (11.7401, 92.6586),
}


def _jitter(lat: float, lon: float, amount: float = 0.003) -> tuple:
    import random
    return (lat + random.uniform(-amount, amount), lon + random.uniform(-amount, amount))


def build_map(itinerary: ItineraryPlan) -> folium.Map:
    """Build a folium map with day-wise color-coded route markers."""
    dest = itinerary.preferences.destination

    # Get base coordinates
    base_lat, base_lon = None, None
    for key, coords in KNOWN_COORDS.items():
        if key.lower() in dest.lower():
            base_lat, base_lon = coords
            break

    if base_lat is None:
        # Try geocoding
        try:
            from geopy.geocoders import Nominatim
            geolocator = Nominatim(user_agent="travel_agent_app")
            location = geolocator.geocode(f"{dest}, India", timeout=5)
            if location:
                base_lat, base_lon = location.latitude, location.longitude
        except Exception:
            pass

    if base_lat is None:
        base_lat, base_lon = 20.5937, 78.9629  # Center of India fallback

    m = folium.Map(
        location=[base_lat, base_lon],
        zoom_start=12,
        tiles="CartoDB positron",
    )

    # Add a title
    title_html = f"""
    <div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%);
                z-index: 1000; background: white; padding: 8px 16px;
                border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                font-family: sans-serif; font-weight: bold; font-size: 14px;">
        🗺️ {dest} Trip — {itinerary.preferences.duration_days} Days
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    prev_coords = None
    for day in itinerary.days:
        color = DAY_COLORS[(day.day_number - 1) % len(DAY_COLORS)]
        day_coords = []

        for block in day.blocks:
            if not block.location:
                continue

            # Get coords for this block's location
            lat, lon = _jitter(base_lat, base_lon)
            try:
                for key, coords in KNOWN_COORDS.items():
                    if key.lower() in (block.location or "").lower():
                        lat, lon = _jitter(coords[0], coords[1])
                        break
            except Exception:
                pass

            day_coords.append([lat, lon])

            # Icon: numbered marker
            icon = folium.DivIcon(
                html=f"""
                <div style="background:{color}; color:white; border-radius:50%;
                            width:24px; height:24px; text-align:center; line-height:24px;
                            font-weight:bold; font-size:11px; box-shadow:0 1px 4px rgba(0,0,0,0.4);">
                    D{day.day_number}
                </div>
                """,
                icon_size=(24, 24),
                icon_anchor=(12, 12),
            )

            popup_html = f"""
            <div style="width:220px; font-family:sans-serif;">
                <b style="color:{color}">Day {day.day_number}: {block.activity}</b><br/>
                <small>⏰ {block.time}</small><br/>
                <p style="margin:4px 0">{block.description}</p>
                {'<b>💰 ₹' + str(int(block.cost_inr)) + '</b><br/>' if block.cost_inr else '💰 Free<br/>'}
                {f'<a href="{block.booking_url}" target="_blank">📌 Book Now</a>' if block.booking_url else ''}
            </div>
            """
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"Day {day.day_number}: {block.activity}",
                icon=icon,
            ).add_to(m)

        # Draw route line for this day
        if len(day_coords) > 1:
            folium.PolyLine(
                day_coords,
                color=color,
                weight=2.5,
                opacity=0.7,
                tooltip=f"{day.title}",
            ).add_to(m)

    # Add legend
    legend_items = ""
    for day in itinerary.days:
        color = DAY_COLORS[(day.day_number - 1) % len(DAY_COLORS)]
        legend_items += f'<div><span style="background:{color}; display:inline-block; width:12px; height:12px; border-radius:2px; margin-right:6px;"></span>{day.title}</div>'

    legend_html = f"""
    <div style="position: fixed; bottom: 30px; right: 10px; z-index: 1000;
                background: white; padding: 10px 14px; border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.2); font-family: sans-serif; font-size: 12px;">
        <b>📅 Day Legend</b><br/>{legend_items}
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m

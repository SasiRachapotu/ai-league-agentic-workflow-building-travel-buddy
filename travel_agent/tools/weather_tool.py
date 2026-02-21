"""
OpenWeatherMap weather tool.
Falls back to LLM-generated weather estimate if key is missing.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5"


def get_weather(city: str) -> dict:
    """
    Fetch current weather for a city.
    Returns a dict with temp, condition, humidity, description.
    Falls back to None if API key missing or error.
    """
    api_key = os.getenv("OPENWEATHERMAP_API_KEY", "")
    if not api_key or api_key == "your_openweathermap_api_key_here":
        return None

    try:
        url = f"{OPENWEATHER_BASE}/weather"
        params = {"q": city, "appid": api_key, "units": "metric"}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return {
            "temp_c": data["main"]["temp"],
            "feels_like_c": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "condition": data["weather"][0]["main"],
            "description": data["weather"][0]["description"].title(),
            "wind_kmh": round(data["wind"]["speed"] * 3.6, 1),
        }
    except Exception as e:
        print(f"[Weather] Failed for {city}: {e}")
        return None


def get_weather_summary(city: str, travel_dates: str = "next weekend") -> str:
    """Return a human-readable weather summary string for use in prompts/UI."""
    weather = get_weather(city)
    if weather:
        return (
            f"{weather['description']}, {weather['temp_c']}°C "
            f"(feels like {weather['feels_like_c']}°C), "
            f"Humidity {weather['humidity']}%, Wind {weather['wind_kmh']} km/h"
        )
    return f"Weather data unavailable — expect typical conditions for {city} in the travel period."

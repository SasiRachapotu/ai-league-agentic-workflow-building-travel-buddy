"""
OpenAI LLM client setup.
Falls back gracefully if API key is missing.
"""
import os
from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI

_client = None
DEFAULT_MODEL = "gpt-4o-mini"  # Fast & cheap; swap to "gpt-4o" for higher quality


def get_client() -> OpenAI:
    global _client
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key == "your_openai_api_key_here":
        raise ValueError(
            "OPENAI_API_KEY is not set. Please add it to your .env file.\n"
            "Get your key at: https://platform.openai.com/api-keys"
        )
    if _client is None:
        _client = OpenAI(api_key=api_key)
    return _client


def generate(prompt: str, temperature: float = 0.7, model: str = DEFAULT_MODEL) -> str:
    """Call OpenAI and return text response."""
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()

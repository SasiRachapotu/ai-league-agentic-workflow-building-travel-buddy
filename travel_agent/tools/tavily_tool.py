"""
Tavily web search tool.
Falls back to empty results if API key is missing — LLM generates estimates instead.
"""
import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()


def tavily_search(query: str, max_results: int = 5) -> List[Dict]:
    """
    Search the web using Tavily and return a list of results.
    Each result: {title, url, content}
    Returns empty list if Tavily is not configured.
    """
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key or api_key == "your_tavily_api_key_here":
        return []

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, max_results=max_results)
        results = []
        for r in response.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", "")[:500],
            })
        return results
    except Exception as e:
        print(f"[Tavily] Search failed: {e}")
        return []


def search_to_context(query: str, max_results: int = 5) -> str:
    """Return search results as a formatted string for LLM prompts."""
    results = tavily_search(query, max_results)
    if not results:
        return "(No live web data available — using LLM knowledge)"
    lines = []
    for r in results:
        lines.append(f"- [{r['title']}]({r['url']})\n  {r['content']}")
    return "\n".join(lines)

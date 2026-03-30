from __future__ import annotations

from typing import Any

try:
    from duckduckgo_search import DDGS
except Exception:  # noqa: BLE001
    DDGS = None  # type: ignore


class WebSearchService:
    def __init__(self, enabled: bool = True, max_results: int = 5) -> None:
        self.enabled = enabled
        self.max_results = max_results

    def search(self, query: str) -> list[dict[str, Any]]:
        if not self.enabled or DDGS is None:
            return []
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=self.max_results))
            normalized = []
            for item in results:
                normalized.append(
                    {
                        "title": item.get("title", "Web result"),
                        "source_path": item.get("href", "web"),
                        "text": item.get("body", ""),
                        "score": 0.5,
                        "metadata": {"source_type": "web", "url": item.get("href", "")},
                    }
                )
            return normalized
        except Exception:
            return []

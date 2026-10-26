"""Alibaba Cloud DashScope (Qwen) with native web search enabled.

Uses the OpenAI-compatible endpoint; `enable_search` + `search_options`
force a live web search and return `search_info.search_results`.
"""

from .base import SEARCH_SYSTEM_PROMPT, ProviderResult, SearchProvider, Source

DASHSCOPE_CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"


class QwenProvider(SearchProvider):
    name = "qwen"
    display_name = "Qwen (DashScope)"

    def is_configured(self) -> bool:
        return bool(self.settings.dashscope_api_key)

    async def search(self, query: str) -> ProviderResult:
        payload = {
            "model": self.settings.qwen_model,
            "messages": [
                {"role": "system", "content": SEARCH_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            "enable_search": True,
            "search_options": {
                "forced_search": True,
                "search_mode": "performance_first",
            },
        }
        data = await self.post_json(
            DASHSCOPE_CHAT_URL,
            headers={
                "Authorization": f"Bearer {self.settings.dashscope_api_key}",
                "Content-Type": "application/json",
            },
            payload=payload,
        )

        choice = data["choices"][0]
        content = (choice.get("message") or {}).get("content", "") or ""

        sources: list[Source] = []
        info = data.get("search_info") or {}
        results = info.get("search_results") or []
        if isinstance(results, list):
            for item in _flatten(results):
                sources.append(
                    Source(
                        title=str(item.get("title") or item.get("site_name") or "untitled"),
                        url=str(item.get("url") or ""),
                        snippet=str(item.get("content") or "")[:300],
                    )
                )
        return ProviderResult(
            provider=self.name,
            display_name=self.display_name,
            query=query,
            content=content,
            sources=sources,
        )


def _flatten(items: list) -> list[dict]:
    """DashScope may nest search_results as list-of-lists (one per generation)."""
    out: list[dict] = []
    for item in items:
        if isinstance(item, list):
            out.extend(x for x in item if isinstance(x, dict))
        elif isinstance(item, dict):
            out.append(item)
    return out

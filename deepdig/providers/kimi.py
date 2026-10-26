"""Moonshot AI (Kimi) fallback via the `$web_search` builtin function.

Flow: first call asks the model with the builtin tool; if it emits a
`$web_search` tool_call, the arguments are echoed back as the tool result
(the search itself runs server-side), then a second call produces the
grounded answer. The whole exchange stays under the global timeout via
`safe_search()`.
"""

from .base import SEARCH_SYSTEM_PROMPT, ProviderResult, SearchProvider, Source

MOONSHOT_CHAT_URL = "https://api.moonshot.cn/v1/chat/completions"

_WEB_SEARCH_TOOL = {"type": "builtin_function", "function": {"name": "$web_search"}}


class KimiProvider(SearchProvider):
    name = "kimi"
    display_name = "Kimi (Moonshot)"

    def is_configured(self) -> bool:
        return bool(self.settings.moonshot_api_key)

    async def search(self, query: str) -> ProviderResult:
        messages = [
            {"role": "system", "content": SEARCH_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]
        payload = {
            "model": self.settings.kimi_model,
            "messages": messages,
            "tools": [_WEB_SEARCH_TOOL],
        }
        data = await self.post_json(MOONSHOT_CHAT_URL, headers=self._headers(), payload=payload)

        choice = data["choices"][0]
        message = choice.get("message") or {}
        if choice.get("finish_reason") == "tool_calls" and message.get("tool_calls"):
            tool_call = message["tool_calls"][0]
            messages.append(message)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "name": tool_call.get("function", {}).get("name", "$web_search"),
                    "content": tool_call.get("function", {}).get("arguments", "{}"),
                }
            )
            data = await self.post_json(
                MOONSHOT_CHAT_URL, headers=self._headers(), payload=payload
            )
            message = data["choices"][0].get("message") or {}

        content = message.get("content", "") or ""
        sources = self._extract_sources(message, data)
        return ProviderResult(
            provider=self.name,
            display_name=self.display_name,
            query=query,
            content=content,
            sources=sources,
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.moonshot_api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _extract_sources(message: dict, data: dict) -> list[Source]:
        sources: list[Source] = []
        for hit in message.get("search_results") or []:
            if isinstance(hit, dict):
                sources.append(
                    Source(
                        title=str(hit.get("title") or hit.get("site_name") or "untitled"),
                        url=str(hit.get("url") or ""),
                        snippet=str(hit.get("snippet") or hit.get("date") or "")[:300],
                    )
                )
        if not sources:
            for url in data.get("citations") or []:
                if isinstance(url, str):
                    sources.append(Source(title=url, url=url))
        return sources

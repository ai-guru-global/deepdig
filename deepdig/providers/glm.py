"""Zhipu AI (GLM) with the `web_search` tool attached to chat completions.

The response carries retrieved web pages in `web_search` (or the newer
`search_result` field), separate from the generated answer text.
"""

from .base import SEARCH_SYSTEM_PROMPT, ProviderResult, SearchProvider, Source

ZHIPU_CHAT_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"


class GlmProvider(SearchProvider):
    name = "glm"
    display_name = "GLM (Zhipu)"

    def is_configured(self) -> bool:
        return bool(self.settings.zhipu_api_key)

    async def search(self, query: str) -> ProviderResult:
        payload = {
            "model": self.settings.glm_model,
            "messages": [
                {"role": "system", "content": SEARCH_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            "tools": [{"type": "web_search", "web_search": {"enable": True}}],
            "stream": False,
        }
        data = await self.post_json(
            ZHIPU_CHAT_URL,
            headers={
                "Authorization": f"Bearer {self.settings.zhipu_api_key}",
                "Content-Type": "application/json",
            },
            payload=payload,
        )

        choice = data["choices"][0]
        message = choice.get("message") or {}
        content = message.get("content", "") or ""

        raw_hits = (
            data.get("web_search")
            or data.get("search_result")
            or message.get("web_search")
            or message.get("search_result")
            or []
        )
        sources = [
            Source(
                title=str(hit.get("title") or hit.get("media_name") or "untitled"),
                url=str(hit.get("link") or hit.get("url") or ""),
                snippet=str(hit.get("content") or "")[:300],
            )
            for hit in raw_hits
            if isinstance(hit, dict)
        ]
        return ProviderResult(
            provider=self.name,
            display_name=self.display_name,
            query=query,
            content=content,
            sources=sources,
        )

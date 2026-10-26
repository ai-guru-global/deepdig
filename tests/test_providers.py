"""Unit tests: provider parsing, fault tolerance, and output rendering.

All HTTP is faked by monkeypatching `SearchProvider.post_json`, so the suite
runs offline and fast.
"""

import asyncio

from deepdig.config import Settings
from deepdig.providers import build_providers
from deepdig.providers.base import ProviderResult, SearchProvider, Source
from deepdig.providers.glm import GlmProvider
from deepdig.providers.kimi import KimiProvider
from deepdig.providers.qwen import QwenProvider
from deepdig.server import _render, run_deepdig


def make_settings(**overrides) -> Settings:
    kwargs = {
        "dashscope_api_key": "sk-test",
        "zhipu_api_key": "zhipu-test",
        "moonshot_api_key": "sk-moon-test",
        "timeout": 0.5,
        **overrides,
    }
    return Settings(**kwargs)


# ---------------------------------------------------------------------------
# safe_search fault tolerance
# ---------------------------------------------------------------------------

class ExplodingProvider(SearchProvider):
    name = "boom"
    display_name = "Boom"

    async def search(self, query: str) -> ProviderResult:
        raise RuntimeError("kaboom")


class SlowProvider(SearchProvider):
    name = "slow"
    display_name = "Slow"

    async def search(self, query: str) -> ProviderResult:
        await asyncio.sleep(5)
        return ProviderResult(provider=self.name, display_name=self.display_name)


class EmptyProvider(SearchProvider):
    name = "empty"
    display_name = "Empty"

    async def search(self, query: str) -> ProviderResult:
        return ProviderResult(provider=self.name, display_name=self.display_name, content="  ")


async def test_safe_search_captures_exceptions():
    result = await ExplodingProvider(make_settings()).safe_search("q")
    assert not result.ok
    assert "RuntimeError" in result.error
    assert "kaboom" in result.error


async def test_safe_search_enforces_timeout():
    result = await SlowProvider(make_settings(timeout=0.1)).safe_search("q")
    assert not result.ok
    assert "timeout" in result.error


async def test_safe_search_flags_empty_content():
    result = await EmptyProvider(make_settings()).safe_search("q")
    assert not result.ok
    assert result.error == "empty response"


# ---------------------------------------------------------------------------
# Provider response parsing
# ---------------------------------------------------------------------------

async def test_qwen_parses_content_and_search_info(monkeypatch):
    async def fake_post(self, url, headers, payload):
        assert payload["enable_search"] is True
        assert headers["Authorization"] == "Bearer sk-test"
        return {
            "choices": [{"message": {"content": "Qwen says hi"}}],
            "search_info": {
                "search_results": [
                    [
                        {"title": "Doc A", "url": "https://a.example", "content": "snip"},
                        {"site_name": "Example", "url": "https://b.example"},
                    ]
                ]
            },
        }

    monkeypatch.setattr(SearchProvider, "post_json", fake_post)
    result = await QwenProvider(make_settings()).search("q")
    assert result.ok
    assert result.content == "Qwen says hi"
    assert [s.url for s in result.sources] == ["https://a.example", "https://b.example"]


async def test_glm_parses_web_search_hits(monkeypatch):
    async def fake_post(self, url, headers, payload):
        assert payload["tools"][0]["type"] == "web_search"
        return {
            "choices": [{"message": {"content": "GLM says hi"}}],
            "web_search": [
                {"title": "News", "link": "https://news.example", "content": "body"},
            ],
        }

    monkeypatch.setattr(SearchProvider, "post_json", fake_post)
    result = await GlmProvider(make_settings()).search("q")
    assert result.ok
    assert result.sources[0].url == "https://news.example"


async def test_glm_falls_back_to_search_result_key(monkeypatch):
    async def fake_post(self, url, headers, payload):
        return {
            "choices": [{"message": {"content": "hi"}}],
            "search_result": [{"title": "R", "url": "https://r.example"}],
        }

    monkeypatch.setattr(SearchProvider, "post_json", fake_post)
    result = await GlmProvider(make_settings()).search("q")
    assert result.sources[0].url == "https://r.example"


async def test_kimi_two_turn_builtin_search(monkeypatch):
    calls: list[dict] = []

    async def fake_post(self, url, headers, payload):
        calls.append(payload)
        if len(calls) == 1:
            return {
                "choices": [{
                    "finish_reason": "tool_calls",
                    "message": {
                        "tool_calls": [{
                            "id": "call-1",
                            "function": {
                                "name": "$web_search",
                                "arguments": '{"search_query":"q"}',
                            },
                        }]
                    },
                }]
            }
        return {
            "choices": [{
                "finish_reason": "stop",
                "message": {
                    "content": "Kimi says hi",
                    "search_results": [{"title": "K", "url": "https://k.example", "snippet": "s"}],
                },
            }]
        }

    monkeypatch.setattr(SearchProvider, "post_json", fake_post)
    result = await KimiProvider(make_settings()).search("q")
    assert result.ok
    assert result.content == "Kimi says hi"
    assert result.sources[0].url == "https://k.example"
    # second request must echo the tool_call back as a tool message
    assert any(m.get("role") == "tool" for m in calls[1]["messages"])


# ---------------------------------------------------------------------------
# build_providers & rendering
# ---------------------------------------------------------------------------

def test_build_providers_activates_only_configured_keys(monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("ZHIPU_API_KEY", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    monkeypatch.delenv("DEEPDIG_DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("DEEPDIG_ZHIPU_API_KEY", raising=False)
    monkeypatch.delenv("DEEPDIG_MOONSHOT_API_KEY", raising=False)
    from deepdig.config import get_settings

    get_settings.cache_clear()
    assert build_providers() == []

    monkeypatch.setenv("ZHIPU_API_KEY", "only-zhipu")
    get_settings.cache_clear()
    names = [p.name for p in build_providers()]
    assert names == ["glm"]
    get_settings.cache_clear()


def test_render_marks_cross_verified_sources():
    shared = Source(title="Shared", url="https://x.example", snippet="")
    ok_a = ProviderResult(provider="qwen", display_name="Qwen", content="a",
                          sources=[shared], elapsed_ms=10)
    ok_b = ProviderResult(provider="glm", display_name="GLM", content="b",
                          sources=[shared], elapsed_ms=20)
    bad = ProviderResult(provider="kimi", display_name="Kimi", error="timeout after 8.0s")
    out = _render([ok_a, ok_b, bad], "test query", 3)
    assert "✦cross-verified" in out
    assert "Cross-verified URLs (1)" in out
    assert "Failed engines" in out
    assert "timeout" in out


async def test_run_deepdig_without_keys_returns_hint(monkeypatch):
    for var in ("DASHSCOPE_API_KEY", "ZHIPU_API_KEY", "MOONSHOT_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    from deepdig.config import get_settings

    get_settings.cache_clear()
    out = await run_deepdig("hello")
    assert "no search providers configured" in out
    get_settings.cache_clear()

"""Tests for P1/P2 server features: URL dedup, truncation, cache, health, token gate."""

from deepdig.config import get_settings
from deepdig.providers.base import health_summary, record_health
from deepdig.server import (
    _cache_get,
    _cache_put,
    _domain_of,
    _normalize_url,
    _truncate,
    run_deepdig,
)


def test_normalize_url_strips_tracking_and_unifies_host():
    a = _normalize_url("https://www.Example.com/a/?utm_source=x&utm_medium=y&id=2")
    b = _normalize_url("http://example.com/a")
    assert a == "https://example.com/a?id=2"
    assert a.split("?")[0] == b
    assert _normalize_url("https://example.com/x#section") == "https://example.com/x"


def test_domain_of():
    assert _domain_of("https://www.News.Example.com/a?b=c") == "news.example.com"
    assert _domain_of("not-a-url") == "not-a-url"


def test_truncate_respects_budget_and_boundaries():
    text = "这是一个完整的句子。" * 100
    out = _truncate(text, 300)
    assert "truncated" in out
    assert len(out) < 450
    assert _truncate("short answer", 300) == "short answer"
    assert _truncate("no clean boundary" + "x" * 400, 100).startswith("no clean boundary")


def test_cache_roundtrip(monkeypatch):
    monkeypatch.setenv("DEEPDIG_CACHE_TTL", "300")
    get_settings.cache_clear()
    assert _cache_get("k1") is None
    _cache_put("k1", "value")
    assert _cache_get("k1") == "value"

    monkeypatch.setenv("DEEPDIG_CACHE_TTL", "0")
    get_settings.cache_clear()
    assert _cache_get("k1") is None
    _cache_put("k2", "ignored")
    assert _cache_get("k2") is None
    get_settings.cache_clear()


def test_health_summary_window():
    record_health("unittest-engine", True, 1200)
    record_health("unittest-engine", False, 3000)
    s = health_summary("unittest-engine")
    assert "50% ok" in s
    assert "last 2" in s
    assert health_summary("never-seen-engine") == ""


async def test_access_token_gate(monkeypatch):
    monkeypatch.setenv("DEEPDIG_ACCESS_TOKEN", "sekrit")
    get_settings.cache_clear()

    out = await run_deepdig("hello", token="wrong")
    assert "unauthorized" in out
    out = await run_deepdig("hello")
    assert "unauthorized" in out
    out = await run_deepdig("hello", token="sekrit")
    assert "no search providers configured" in out

    monkeypatch.delenv("DEEPDIG_ACCESS_TOKEN")
    get_settings.cache_clear()
    out = await run_deepdig("hello", token="")
    assert "unauthorized" not in out
    get_settings.cache_clear()

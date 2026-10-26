"""FastMCP server exposing the `deepdig` concurrent web-retrieval tool."""

import asyncio
import hashlib
import re
import sys
import time
from urllib.parse import parse_qsl, urlparse

from mcp.server.fastmcp import FastMCP

from . import __version__
from .config import get_settings
from .providers import ProviderResult, build_providers
from .providers.base import health_summary

mcp = FastMCP(
    "deepdig",
    instructions=(
        "deepdig fans a query out to multiple native LLM web-search backends "
        "(Qwen/DashScope, GLM/Zhipu, Kimi/Moonshot) concurrently and returns "
        "deduplicated, cross-verified markdown with sources. Use it whenever "
        "you need real-time web facts, news, or fact-checking."
    ),
)

TOOL_DESCRIPTION = (
    "Concurrent multi-engine web retrieval & real-time fact-checking. "
    "Queries every configured native search backend (Qwen/DashScope, GLM/Zhipu, "
    "Kimi/Moonshot) in parallel, then returns deduplicated, cross-verified "
    "markdown: one section per provider plus a merged source list where URLs "
    "confirmed by 2+ engines are flagged. Failed or timed-out engines are "
    "reported inline and never fail the call. Optional `token` is only checked "
    "when the server runs with DEEPDIG_ACCESS_TOKEN (remote gateway mode)."
)

_TRACKING_PARAM = re.compile(
    r"^(utm_\w+|fbclid|gclid|msclkid|dclid|twclid|ref|ref_src|ref_url|spm|from|vd|share_token|_hsenc|_hsmi)$",
    re.IGNORECASE,
)

_CACHE_MAX_ENTRIES = 128
_CACHE: dict[str, tuple[float, str]] = {}
_SEM: asyncio.Semaphore | None = None


def _normalize_url(url: str) -> str:
    """Canonical form for cross-engine matching: lowercase host, drop www/scheme/
    fragment/trailing slash and common tracking params."""
    try:
        parts = urlparse(url.strip())
        if not parts.netloc:
            return url.strip()
        host = parts.netloc.lower().removeprefix("www.")
        path = parts.path.rstrip("/") or "/"
        pairs = [
            (k, v)
            for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if not _TRACKING_PARAM.match(k)
        ]
        query = "&".join(f"{k}={v}" for k, v in sorted(pairs))
        return f"https://{host}{path}" + (f"?{query}" if query else "")
    except ValueError:
        return url.strip()


def _domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.") or url
    except ValueError:
        return url


def _truncate(text: str, limit: int) -> str:
    """Trim provider prose to the context budget, preferring clean boundaries."""
    text = text.strip()
    if limit <= 0 or len(text) <= limit:
        return text
    cut = text[:limit]
    for sep in ("\n\n", "。", "! ", "? ", ". ", "；", "; "):
        idx = cut.rfind(sep)
        if idx >= limit // 2:
            kept = cut[: idx + len(sep)]
            return (
                f"{kept}\n\n"
                f"*[deepdig: truncated {len(text) - len(kept)} chars to fit context budget]*"
            )
    return f"{cut}…*[deepdig: truncated {len(text) - limit} chars]*"


def _cache_key(query: str, max_sources: int) -> str:
    return hashlib.sha1(f"{query}|{max_sources}".encode()).hexdigest()


def _cache_get(key: str) -> str | None:
    ttl = get_settings().cache_ttl
    if ttl <= 0:
        return None
    hit = _CACHE.get(key)
    if hit is None:
        return None
    if time.monotonic() - hit[0] > ttl:
        _CACHE.pop(key, None)
        return None
    return hit[1]


def _cache_put(key: str, value: str) -> None:
    if get_settings().cache_ttl <= 0:
        return
    if len(_CACHE) >= _CACHE_MAX_ENTRIES:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = (time.monotonic(), value)


def _semaphore() -> asyncio.Semaphore:
    global _SEM
    if _SEM is None:
        _SEM = asyncio.Semaphore(get_settings().max_concurrency)
    return _SEM


def _render(results: list[ProviderResult], query: str, max_sources: int) -> str:
    lines: list[str] = []
    ok = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]
    lines.append(f"# deepdig report — “{query}”")
    lines.append(
        f"> {len(ok)}/{len(results)} engines answered · "
        f"{', '.join(r.provider for r in ok) or 'none'}"
    )

    url_seen: dict[str, tuple[str, set[str]]] = {}
    for r in ok:
        for s in r.sources:
            if not s.url:
                continue
            key = _normalize_url(s.url)
            if key in url_seen:
                url_seen[key][1].add(r.provider)
            else:
                url_seen[key] = (s.url, {r.provider})

    if ok:
        lines.append("")
        for r in ok:
            health = health_summary(r.provider)
            suffix = f" · {health}" if health else ""
            lines.append(f"## ◆ {r.display_name} (`{r.provider}`) — {r.elapsed_ms} ms{suffix}")
            lines.append("")
            lines.append(r.content.strip())
            if r.sources:
                lines.append("")
                lines.append("**Sources:**")
                for s in r.sources[:max_sources]:
                    engines = url_seen.get(_normalize_url(s.url), (s.url, {r.provider}))[1]
                    badge = " ✦cross-verified" if len(engines) > 1 else ""
                    title = s.title or s.url
                    line = f"- [{title}]({s.url}){badge}"
                    if s.snippet:
                        line += f" — {s.snippet}"
                    lines.append(line)

    if url_seen:
        verified = sorted(
            (key for key, (_, provs) in url_seen.items() if len(provs) > 1),
            key=lambda key: -len(url_seen[key][1]),
        )
        lines.append("")
        lines.append(f"## ✦ Cross-verified URLs ({len(verified)})")
        for key in verified:
            display_url = url_seen[key][0]
            lines.append(f"- {len(url_seen[key][1])}× {display_url}")

    if failed:
        lines.append("")
        lines.append("## ⚠ Failed engines")
        for r in failed:
            health = health_summary(r.provider)
            suffix = f" · {health}" if health else ""
            lines.append(f"- `{r.provider}`: {r.error}{suffix}")

    lines.append("")
    domains = {_domain_of(display_url) for display_url, _ in url_seen.values()}
    lines.append(f"---\ndeepdig v{__version__} · {len(domains)} domains · {len(url_seen)} URLs")
    return "\n".join(lines)


async def run_deepdig(query: str, max_sources: int = 3, token: str = "") -> str:
    settings = get_settings()
    query = query.strip()
    if not query:
        return "deepdig: empty query."
    if settings.access_token and token != settings.access_token:
        return "deepdig: unauthorized — missing or invalid access token."
    max_sources = max(1, min(int(max_sources or 3), 10))

    key = _cache_key(query, max_sources)
    cached = _cache_get(key)
    if cached is not None:
        return f"{cached}\n\n*[deepdig: served from cache, TTL {settings.cache_ttl}s]*"

    providers = build_providers()
    if not providers:
        return (
            "deepdig: no search providers configured. "
            "Set DASHSCOPE_API_KEY / ZHIPU_API_KEY / MOONSHOT_API_KEY "
            "in the MCP server env or a .env file."
        )

    sem = _semaphore()

    async def _bounded(p):
        async with sem:
            return await p.safe_search(query)

    results = await asyncio.gather(
        *(_bounded(p) for p in providers),
        return_exceptions=True,
    )
    # return_exceptions=True + safe_search should make this unreachable,
    # but keep the tool call itself unbreakable.
    safe: list[ProviderResult] = [
        r if isinstance(r, ProviderResult) else ProviderResult(
            provider="unknown", display_name="unknown", query=query,
            error=str(r),
        )
        for r in results
    ]
    for r in safe:
        if r.ok:
            r.content = _truncate(r.content, settings.max_content_chars)
    rendered = _render(safe, query, max_sources)
    if any(r.ok for r in safe):
        _cache_put(key, rendered)
    return rendered


@mcp.tool(name="deepdig", description=TOOL_DESCRIPTION)
async def deepdig(query: str, max_sources: int = 3, token: str = "") -> str:
    return await run_deepdig(query, max_sources, token)


@mcp.tool(name="deep_dig", description="Alias of `deepdig` — same tool, snake_case name.")
async def deep_dig(query: str, max_sources: int = 3, token: str = "") -> str:
    return await run_deepdig(query, max_sources, token)


_VALID_TRANSPORTS = {"stdio", "sse", "streamable-http"}


def _gate_middleware(inner_app, token: str):
    """Pure-ASGI bearer gate for gateway mode: accepts `Authorization: Bearer
    <token>` header or `?token=` query param, rejects everything else."""
    from urllib.parse import parse_qs

    async def app(scope, receive, send):
        if scope["type"] == "http":
            headers = {k.lower(): v for k, v in scope.get("headers", [])}
            provided = (
                headers.get(b"authorization", b"").decode().removeprefix("Bearer ").strip()
            )
            if not provided:
                query = scope.get("query_string", b"").decode()
                provided = (parse_qs(query).get("token") or [""])[0]
            if provided != token:
                await send({
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [(b"content-type", b"text/plain; charset=utf-8")],
                })
                await send({"type": "http.response.body", "body": b"deepdig: unauthorized"})
                return
        await inner_app(scope, receive, send)

    return app


def main() -> None:
    settings = get_settings()
    active = [
        n
        for n, k in (
            ("qwen", settings.dashscope_api_key),
            ("glm", settings.zhipu_api_key),
            ("kimi", settings.moonshot_api_key),
        )
        if k
    ]
    print(
        f"deepdig v{__version__} starting · engines: {active or 'NONE (no API keys)'}",
        file=sys.stderr,
    )
    if settings.transport not in _VALID_TRANSPORTS:
        if settings.transport != "stdio":
            print(
                f"deepdig: unknown DEEPDIG_TRANSPORT={settings.transport!r}, falling back to stdio",
                file=sys.stderr,
            )
        mcp.run(transport="stdio")
        return
    if settings.transport == "stdio":
        mcp.run(transport="stdio")
        return

    mcp.settings.host = settings.host
    mcp.settings.port = settings.port
    inner = (
        mcp.sse_app() if settings.transport == "sse" else mcp.streamable_http_app()
    )
    app = (
        _gate_middleware(inner, settings.access_token)
        if settings.access_token
        else inner
    )
    gate = "token-gated" if settings.access_token else "OPEN (set DEEPDIG_ACCESS_TOKEN!)"
    print(
        f"deepdig gateway on http://{settings.host}:{settings.port} "
        f"[{settings.transport}] · {gate}",
        file=sys.stderr,
    )
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port, log_level="warning")


if __name__ == "__main__":
    main()

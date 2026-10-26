"""Abstract search provider with a fault-tolerant execution wrapper."""

import asyncio
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field

import httpx

from ..config import Settings, get_settings

SEARCH_SYSTEM_PROMPT = (
    "You are a web research assistant with live search access. "
    "Answer the user's query using up-to-date web information. "
    "State key facts with dates and cite sources inline as [title](url). "
    "Be factual and concise."
)

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_RETRY_DELAY_S = 0.8

_HEALTH_WINDOW = 20
_HEALTH: dict[str, deque[tuple[bool, int]]] = defaultdict(
    lambda: deque(maxlen=_HEALTH_WINDOW)
)


def record_health(name: str, ok: bool, elapsed_ms: int) -> None:
    _HEALTH[name].append((ok, elapsed_ms))


def health_summary(name: str) -> str:
    window = _HEALTH.get(name)
    if not window:
        return ""
    n = len(window)
    ok_rate = sum(1 for ok, _ in window if ok) / n
    avg_s = sum(ms for _, ms in window) / n / 1000
    return f"{ok_rate:.0%} ok · avg {avg_s:.1f}s (last {n})"


@dataclass
class Source:
    title: str
    url: str
    snippet: str = ""


@dataclass
class ProviderResult:
    provider: str
    display_name: str
    query: str = ""
    content: str = ""
    sources: list[Source] = field(default_factory=list)
    elapsed_ms: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.content.strip())


class SearchProvider(ABC):
    """A single native web-search backend.

    Subclasses implement `search()`, which should perform plain HTTP calls.
    All lifecycle concerns (timeout, timing, exception capture, health stats)
    are handled by `safe_search()` so one broken provider can never break
    the fan-out.
    """

    name: str
    display_name: str

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def is_configured(self) -> bool:
        """Whether this provider should join the fan-out with current settings.

        Defaults to True so third-party plugins surface auth errors honestly
        in the report; built-ins override to check their API key.
        """
        return True

    @abstractmethod
    async def search(self, query: str) -> ProviderResult: ...

    async def safe_search(self, query: str) -> ProviderResult:
        """Run `search()` under the global per-provider timeout, never raising."""
        start = time.monotonic()
        result = ProviderResult(
            provider=self.name,
            display_name=self.display_name,
            query=query,
        )
        try:
            result = await asyncio.wait_for(
                self.search(query), timeout=self.settings.timeout
            )
            if not result.content.strip() and result.error is None:
                result.error = "empty response"
        except TimeoutError:
            result.error = f"timeout after {self.settings.timeout:.1f}s"
        except httpx.HTTPStatusError as exc:
            result.error = f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
        except httpx.HTTPError as exc:
            result.error = f"network error: {type(exc).__name__}: {exc}"
        except Exception as exc:  # noqa: BLE001 — provider isolation is the whole point
            result.error = f"{type(exc).__name__}: {exc}"
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        record_health(self.name, result.ok, result.elapsed_ms)
        return result

    async def post_json(self, url: str, headers: dict[str, str], payload: dict) -> dict:
        """Shared POST helper: strict per-request timeout + one retry on
        429/5xx/transport errors with a short backoff (still bounded by the
        outer `safe_search` timeout)."""
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=self.settings.timeout) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code in _RETRYABLE_STATUS and attempt == 0:
                    await asyncio.sleep(_RETRY_DELAY_S)
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.TransportError:
                if attempt == 0:
                    await asyncio.sleep(_RETRY_DELAY_S)
                    continue
                raise
        raise RuntimeError("post_json: retries exhausted")

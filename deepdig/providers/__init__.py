"""Provider registry — built-ins plus third-party entry-point plugins.

Third-party packages can register additional engines by declaring an entry
point in the `deepdig.providers` group:

    [project.entry-points."deepdig.providers"]
    tavily = "tavily_deepdig:TavilyProvider"

The loaded class must subclass `deepdig.providers.SearchProvider` and set a
unique `name`; it should override `is_configured()` to report whether its
credentials (env vars etc.) are present.
"""

import sys
from importlib.metadata import entry_points

from ..config import get_settings
from .base import ProviderResult, SearchProvider, Source
from .glm import GlmProvider
from .kimi import KimiProvider
from .qwen import QwenProvider

ENTRY_POINT_GROUP = "deepdig.providers"

__all__ = [
    "ENTRY_POINT_GROUP",
    "ProviderResult",
    "SearchProvider",
    "Source",
    "build_providers",
]


def _builtin_providers(settings) -> list[SearchProvider]:
    providers: list[SearchProvider] = []
    for cls in (QwenProvider, GlmProvider, KimiProvider):
        p = cls(settings)
        if p.is_configured():
            providers.append(p)
    return providers


def _load_entry_point_classes() -> list[type[SearchProvider]]:
    try:
        eps = entry_points(group=ENTRY_POINT_GROUP)
    except Exception as exc:  # noqa: BLE001 — plugin discovery must never break startup
        print(f"deepdig: entry-point discovery failed: {exc}", file=sys.stderr)
        return []
    classes: list[type[SearchProvider]] = []
    for ep in eps:
        try:
            cls = ep.load()
            if not (isinstance(cls, type) and issubclass(cls, SearchProvider)):
                raise TypeError(f"{ep.value} is not a SearchProvider subclass")
            classes.append(cls)
        except Exception as exc:  # noqa: BLE001
            print(f"deepdig: skipping plugin '{ep.name}': {exc}", file=sys.stderr)
    return classes


def build_providers() -> list[SearchProvider]:
    settings = get_settings()
    providers = _builtin_providers(settings)
    names = {p.name for p in providers}

    for cls in _load_entry_point_classes():
        try:
            p = cls(settings)
        except Exception as exc:  # noqa: BLE001
            print(f"deepdig: plugin '{cls.__name__}' init failed: {exc}", file=sys.stderr)
            continue
        if not cls.name or cls.name in names:
            print(
                f"deepdig: skipping plugin '{cls.__name__}' "
                f"(missing or duplicate name '{cls.name}')",
                file=sys.stderr,
            )
            continue
        if p.is_configured():
            providers.append(p)
            names.add(cls.name)
    return providers

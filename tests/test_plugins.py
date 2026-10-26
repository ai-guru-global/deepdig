"""Tests for the provider plugin (entry-point) mechanism."""

from deepdig.config import Settings
from deepdig.providers import (
    SearchProvider,
    _builtin_providers,
    _load_entry_point_classes,
    build_providers,
)
from deepdig.providers.base import ProviderResult


class DummyOk(SearchProvider):
    name = "dummy"
    display_name = "Dummy Engine"

    async def search(self, query: str) -> ProviderResult:
        return ProviderResult(provider=self.name, display_name=self.display_name, content="hi")


class DummyUnconfigured(DummyOk):
    name = "dummy-unconfigured"

    def is_configured(self) -> bool:
        return False


class FakeEntryPoint:
    def __init__(self, name: str, cls) -> None:
        self._name = name
        self._cls = cls

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> str:
        return f"{self._cls.__module__}:{self._cls.__name__}"

    def load(self):
        return self._cls


def _settings() -> Settings:
    return Settings(dashscope_api_key="sk-test")


def test_builtin_filtering_uses_is_configured(monkeypatch):
    for var in ("DASHSCOPE_API_KEY", "ZHIPU_API_KEY", "MOONSHOT_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    assert [p.name for p in _builtin_providers(_settings())] == ["qwen"]


def test_entry_point_plugins_are_loaded_and_name_guarded(monkeypatch, capsys):
    class QwenClone(DummyOk):
        name = "qwen"

    monkeypatch.setattr("deepdig.providers.get_settings", lambda: _settings())
    monkeypatch.setattr(
        "deepdig.providers.entry_points",
        lambda group: [
            FakeEntryPoint("dummy", DummyOk),
            FakeEntryPoint("qwen_clone", QwenClone),  # collides with built-in "qwen"
            FakeEntryPoint("broken", object),         # not a SearchProvider subclass
            FakeEntryPoint("unconfigured", DummyUnconfigured),
        ],
    )
    assert [cls.name for cls in _load_entry_point_classes()] == [
        "dummy",
        "qwen",
        "dummy-unconfigured",
    ]

    providers = build_providers()
    names = [p.name for p in providers]
    assert "dummy" in names
    assert "qwen" in names
    assert "qwen_clone" not in names          # duplicate name rejected
    assert "unconfigured" not in names        # is_configured() == False skipped
    warnings = capsys.readouterr().err
    assert "not a SearchProvider" in warnings
    assert "duplicate name" in warnings


def test_entry_point_discovery_failure_is_swallowed(monkeypatch):
    def boom(group):
        raise RuntimeError("metadata unavailable")

    monkeypatch.setattr("deepdig.providers.entry_points", boom)
    assert _load_entry_point_classes() == []


def test_plugin_init_failure_is_swallowed(monkeypatch, capsys):
    class ExplodingInit(DummyOk):
        name = "explodes"

        def __init__(self, settings=None):
            raise ValueError("bad plugin config")

    monkeypatch.setattr("deepdig.providers.get_settings", lambda: _settings())
    monkeypatch.setattr(
        "deepdig.providers.entry_points",
        lambda group: [FakeEntryPoint("explodes", ExplodingInit)],
    )
    providers = build_providers()
    assert [p.name for p in providers] == ["qwen"]
    assert "init failed" in capsys.readouterr().err

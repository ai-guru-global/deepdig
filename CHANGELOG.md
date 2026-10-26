# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-26

### Added

- Core FastMCP server (`stdio` / `sse` / `streamable-http`) exposing the `deepdig` tool (alias `deep_dig`).
- Built-in providers: Qwen (DashScope `enable_search`), GLM (Zhipu `web_search`), Kimi (Moonshot `$web_search`).
- Third-party provider plugins via the `deepdig.providers` entry-point group.
- Fault tolerance: strict 8s per-engine circuit breaker, one-shot retry on 429/5xx/transport errors, sliding-window health stats rendered in reports.
- Result quality: tracking-param URL normalization, cross-engine `✦cross-verified` source flagging, per-engine context budget truncation, TTL result cache.
- Deployment: BYOK local mode and remote gateway mode with bearer-token gate + concurrency semaphore.
- Benchmark harness (`bench/`) measuring source recall lift, latency percentiles and cross-verification.
- CI (ruff + pytest, Python 3.11/3.12 matrix) and PyPI trusted publishing workflow.
- IDE skill spec (`skill/deepdig.md`) for trigger and arbitration rules.

[Unreleased]: https://github.com/ai-guru-global/deepdig/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ai-guru-global/deepdig/releases/tag/v0.1.0

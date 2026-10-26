# Contributing to DeepDig

Thanks for your interest in improving DeepDig! This document covers the
development setup and the conventions we follow.

## Development setup

Requirements: Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/ai-guru-global/deepdig.git
cd deepdig
uv sync            # install deps (incl. dev tools)
uv run pytest -q   # offline unit tests — no API keys needed
uv run ruff check .
```

To exercise real engines, export at least one of `DASHSCOPE_API_KEY`,
`ZHIPU_API_KEY`, `MOONSHOT_API_KEY`, then `uv run deepdig`.

## Project layout

```
deepdig/            server, config, providers (see README)
skill/              IDE skill spec
bench/              benchmark harness
tests/              offline unit tests (HTTP fully mocked)
```

## Ground rules

- **Keep the positioning**: DeepDig is a cognition/retrieval layer that
  consumes model-preheated web search. Don't turn providers into crawlers —
  that's Firecrawl's job.
- **Provider isolation**: `safe_search()` must stay the only execution path;
  a broken provider can never break the fan-out or the tool call.
- **Tests are mandatory** for bug fixes and new features. All HTTP is mocked;
  keep the suite offline and fast.
- **No secrets in code**: keys come from env/.env only. Never commit a `.env`.

## Writing a new provider

Third-party engines plug in via entry points — see the “扩展 Provider”
section in the README. For a built-in provider, subclass `SearchProvider`,
set a unique `name`, override `is_configured()`, implement `search()`, and
add parsing tests with canned payloads.

## Commit & PR conventions

- Commits follow [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `ci:`, `bench:`).
- Keep PRs focused; update `CHANGELOG.md` under `[Unreleased]` when the change
  is user-visible.
- CI must be green (ruff + pytest on Python 3.11/3.12) before review.

## Reporting bugs & security issues

- Bugs and feature requests: GitHub Issues with the provided templates.
- Security vulnerabilities: **do not open a public issue** — see
  [SECURITY.md](./SECURITY.md).

## License

By contributing, you agree that your contributions will be licensed under
the [MIT License](./LICENSE).

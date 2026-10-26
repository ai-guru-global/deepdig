"""DeepDig benchmark harness.

Runs a fixed query set against all configured engines, measures per-engine
latency and source recall, and reports merged cross-verified recall — the
three dimensions from the README benchmark table. Fact-accuracy scoring is
left to manual/LLM review: the report embeds full source lists for auditing.

Usage (requires at least one provider API key):
    uv run python bench/run_bench.py
    uv run python bench/run_bench.py --full              # embed full reports
    uv run python bench/run_bench.py --queries my.json --out bench/reports
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deepdig.config import get_settings  # noqa: E402
from deepdig.providers import build_providers  # noqa: E402
from deepdig.providers.base import ProviderResult  # noqa: E402
from deepdig.server import _domain_of, _normalize_url, _render  # noqa: E402

DEFAULT_QUERIES = Path(__file__).parent / "queries.json"


def pct(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    data = sorted(values)
    idx = min(len(data) - 1, max(0, round(q / 100 * (len(data) - 1))))
    return data[idx]


def unique_domains(results: list[ProviderResult]) -> set[str]:
    return {
        _domain_of(s.url)
        for r in results
        if r.ok
        for s in r.sources
        if s.url
    }


def cross_verified_urls(results: list[ProviderResult]) -> set[str]:
    seen: dict[str, set[str]] = {}
    for r in results:
        if not r.ok:
            continue
        for s in r.sources:
            if s.url:
                seen.setdefault(_normalize_url(s.url), set()).add(r.provider)
    return {u for u, provs in seen.items() if len(provs) > 1}


def pct_str(values: list[float]) -> str:
    if not values:
        return "n/a"
    return f"p50 {pct(values, 50) / 1000:.1f}s / p95 {pct(values, 95) / 1000:.1f}s"


def main() -> int:
    parser = argparse.ArgumentParser(description="deepdig benchmark")
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERIES)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "reports")
    parser.add_argument("--full", action="store_true", help="embed full deepdig report per query")
    args = parser.parse_args()

    get_settings().cache_ttl = 0  # benchmark must measure the cold path
    providers = build_providers()
    if not providers:
        print(
            "deepdig-bench: no providers configured — "
            "set DASHSCOPE_API_KEY / ZHIPU_API_KEY / MOONSHOT_API_KEY first.",
            file=sys.stderr,
        )
        return 1

    items = json.loads(args.queries.read_text(encoding="utf-8"))
    print(f"deepdig-bench: {len(items)} queries × {len(providers)} engines "
          f"({', '.join(p.name for p in providers)})", file=sys.stderr)

    engine_names = [p.name for p in providers]
    per_engine_ms: dict[str, list[float]] = {name: [] for name in engine_names}
    per_engine_domains: dict[str, set[str]] = {name: set() for name in engine_names}
    merged_domains_total = 0
    cross_total = 0
    walls: list[float] = []
    rows: list[dict] = []
    full_reports: list[str] = []

    for item in items:
        query = item["query"]
        t0 = time.monotonic()
        results: list[ProviderResult] = asyncio.run(
            asyncio.gather(*(p.safe_search(query) for p in providers))
        )
        wall_ms = (time.monotonic() - t0) * 1000
        walls.append(wall_ms)

        for r in results:
            if r.ok:
                per_engine_ms[r.provider].append(float(r.elapsed_ms))
                per_engine_domains[r.provider].update(
                    _domain_of(s.url) for s in r.sources if s.url
                )

        merged = unique_domains(results)
        cross = cross_verified_urls(results)
        merged_domains_total += len(merged)
        cross_total += len(cross)
        rows.append({
            "category": item.get("category", "?"),
            "query": query,
            "wall_ms": wall_ms,
            "merged": len(merged),
            "cross": len(cross),
            "ok": "/".join(str(int(r.ok)) for r in results),
        })
        print(f"  [{item.get('category', '?')}] {query} → {wall_ms:.0f} ms, "
              f"{len(merged)} domains, {len(cross)} cross-verified", file=sys.stderr)
        if args.full:
            full_reports.append(_render(results, query, 3))

    n = len(rows)
    # Aggregate recall comparison: merged unique domains across the whole set
    # vs each engine alone.
    engine_totals = {name: len(per_engine_domains[name]) for name in engine_names}
    best_single = max(engine_totals.values()) if engine_totals else 0
    lift_pct = (merged_domains_total / best_single - 1) * 100 if best_single else float("nan")

    lines = [
        "# deepdig benchmark report",
        "",
        f"- Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"- Query set: `{args.queries}` ({n} queries)",
        f"- Engines: {', '.join(engine_names)}",
        f"- Timeout: {get_settings().timeout}s per engine",
        "",
        "## Latency (end-to-end wall clock)",
        "",
        f"- Merged fan-out: {pct_str(walls)}",
    ]
    for name in engine_names:
        ok_n = len(per_engine_ms[name])
        lines.append(f"- `{name}`: ok {ok_n}/{n} · {pct_str(per_engine_ms[name])}")

    lines += [
        "",
        "## Source recall (unique domains)",
        "",
        f"- Merged total unique domains across set: **{merged_domains_total}**",
    ]
    for name in engine_names:
        lines.append(f"- `{name}` alone: {engine_totals[name]}")
    lines += [
        f"- Recall lift vs best single engine: **+{lift_pct:.0f}%** (target: 40%~70%)",
        f"- Cross-verified URLs per query (avg): **{cross_total / n:.1f}**",
        "",
        "## Per-query detail",
        "",
        "| category | query | wall ms | domains | verified | ok |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['category']} | {row['query']} | {row['wall_ms']:.0f} "
            f"| {row['merged']} | {row['cross']} | {row['ok']} |"
        )
    lines += [
        "",
        "## Fact accuracy (manual/LLM review)",
        "",
        "Traceability of individual claims is not auto-scored. Re-run with "
        "`--full` and audit each embedded report: every assertion in the "
        "arbiter's final answer should map to a listed source.",
    ]
    if full_reports:
        lines.append("")
        for report in full_reports:
            lines.append("<details><summary>full report</summary>")
            lines.append("")
            lines.append(report)
            lines.append("")
            lines.append("</details>")
            lines.append("")

    args.out.mkdir(parents=True, exist_ok=True)
    report_path = args.out / f"report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\ndeepdig-bench: merged recall +{lift_pct:.0f}% vs best single engine · "
          f"latency {pct_str(walls)}", file=sys.stderr)
    print(f"deepdig-bench: report written to {report_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

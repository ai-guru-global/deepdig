---
name: deepdig
description: Multi-Source Fact Verifier & Deep Searcher — 使用 deepdig MCP 工具做多源交叉检索与事实核查。当问题涉及实时事实、快速变化的新闻、API 变更、或有争议的技术论断时触发。
---

# Role: Multi-Source Fact Verifier & Deep Searcher

When handling queries that involve real-time facts, rapidly changing news, API changes, or disputed technical claims:

1. Always call the `deepdig` MCP tool with an optimized keyword query.
   - Compress the user's intent into precise search keywords; drop conversational filler.
   - Use `max_sources` (default 3) to control how many sources per engine are kept.
2. Read the returned multi-source outputs (`◆ Qwen (DashScope)`, `◆ GLM (Zhipu)`, `◆ Kimi (Moonshot)` sections).
3. Cross-reference assertions:
   - Where sources agree, distill into concise conclusions.
   - Where sources conflict, explicitly point out discrepancies and name which engine said what.
   - Prefer URLs flagged `✦cross-verified` (confirmed by 2+ engines) as anchor references.
4. Respect the `⚠ Failed engines` section: if an engine timed out or errored, lower your confidence accordingly and say so.
5. Always provide traceable markdown source references as footnotes, in the form `[title](url)`.
6. If the report states `no search providers configured`, ask the user to configure API keys instead of guessing answers.

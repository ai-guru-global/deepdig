# DeepDig (深掘)

[![CI](https://github.com/ai-guru-global/deepdig/actions/workflows/ci.yml/badge.svg)](https://github.com/ai-guru-global/deepdig/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/deepdig)](https://pypi.org/project/deepdig/)
[![Python](https://img.shields.io/pypi/pyversions/deepdig)](https://pypi.org/project/deepdig/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Code style: ruff](https://img.shields.io/badge/style-ruff-261230.svg)](https://docs.astral.sh/ruff/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](https://github.com/ai-guru-global/deepdig/actions/workflows/ci.yml)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./CONTRIBUTING.md)

> **High-Performance Multi-Agent Web Search & Fact-Checking MCP Server**
> *A project by [ai-guru-global](https://github.com/ai-guru-global), created and maintained by [@allengaller](https://github.com/allengaller).*

`deepdig` 是一个面向现代 AI IDE（如 Qoder、CodeBuddy、Cursor、Windsurf）和 Agent 环境的高性能 MCP（Model Context Protocol）服务。它通过异步并发调度主流大模型与搜索引擎的底层原生检索能力（Qwen 百炼、智谱 GLM、Moonshot Kimi 等），提供低延迟、防幻觉的多源交叉检索与事实核查管道。

---

## 核心定位：与抓取工具的区别

很多开发者容易混淆“网页爬取”与“Agent 检索”：

- **Firecrawl 等爬虫基建**：定位在 **Scraper / Crawler 基础设施层**，专注解决反爬、JS 动态渲染、代理轮换，并将特定站点转为 Clean Markdown。
- **DeepDig**：定位在 **认知与综合检索层（Agentic Search & RAG Gateway）**。它不重复造爬虫轮子，而是直接消费经过各家大模型深度预热、提炼与索引后的 Web Search 结果，做多源事实交叉验证与信源比对。

---

## 架构原理

```text
[用户 Query (Qoder / CodeBuddy / Cursor)]
                    │
                    ▼
          [Skill / Prompt 规范]
                    │
                    ▼
     [DeepDig MCP Server (FastMCP)]
                    │
    ┌───────────────┼───────────────┐  asyncio.gather (8s 严格熔断)
    ▼               ▼               ▼
[Qwen 百炼]     [智谱 GLM]     [Moonshot Kimi]
(广度事实/新闻)  (学术/科技资讯)  (长文研报蒸馏)
    │               │               │
    └───────────────┼───────────────┘
                    ▼
      [结构化 Markdown 上下文聚合]
                    │
                    ▼
      [宿主 IDE 仲裁模型 (Arbiter)] ──> 输出可信、带信源注脚的最终答案
```

1. **分层分工**：
   - **Qwen (阿里百炼)**：利用 `enable_search: true`，覆盖广度事实、即时新闻与国内生态。
   - **GLM (智谱 AI)**：调用 `web_search` 工具能力，提供高结构化、中文科技与学术资讯的交叉信源。
   - **Kimi (Moonshot)**：承接长文档与深度长文分析需求。

2. **轻量与隔离**：
   - 采用 **`Skill (.md)` + `MCP Server (Python 脚本)`** 解耦架构。
   - `.md` 仅作为大脑指令定义调用时机；MCP 负责网络 I/O、凭据管理、并发请求与熔断。
   - 本地模式下，用户凭据仅存在本地环境，绝不暴露在 Prompt 或网络传输中。

---

## 核心特性

- **跨源事实交叉核查（Fact-Checking）**：并发拉取不同引擎的检索结果，大幅降低单一模型的幻觉率与死链率。
- **高容错异步并发（Fork-Join 管道）**：使用 `asyncio.gather` 并发请求各源，单请求严格设定 **8 秒熔断超时**，任意单点失败不阻断整体流程。
- **两套部署形态**：
  - **BYOK 本地模式**：开发者直接读取本地环境变量，零成本随 IDE 启动。
  - **远端 Gateway 模式（可选）**：通过 SSE 服务端集中管理底层 Token，客户端开箱即用。
- **全平台协议兼容**：遵循标准 MCP 规范，无缝挂载至 Qoder、CodeBuddy、Cursor、Windsurf 及 Claude Desktop。

---

## 竞品对比与项目评估

> 对比数据基于 2026-09/10 公开资料（见文末来源），竞品功能以官方文档为准。

### 生态位：检索分层中的“多源仲裁层”

| 产品 | 层级定位 | 检索机制 | 多源交叉验证 | 中文生态 | 部署形态 | 计费模式 |
| --- | --- | --- | --- | --- | --- | --- |
| **DeepDig** | **认知/仲裁层** | 消费三家原生 LLM 联网检索的**预综合结果**并仲裁 | ✅ 内建（URL 归并 + ✦ 标记） | ✅ 原生（Qwen/GLM/Kimi） | BYOK 本地 / 自托管 Gateway | 自付模型 API（无中间商加价） |
| Tavily | 通用检索 API | 自建 RAG 索引 + 结构化结果 | ❌ 单源 | 一般（海外服务） | 云托管 SaaS | 按调用计费（信用点） |
| Firecrawl | 爬取基建层 | 搜索 + 反爬 + 页面清洗为 Markdown | ❌ 单源 | 一般 | 云托管 / 可自部署 | 按额度计费 |
| Exa | 语义检索层 | 神经/语义索引，学术内容见长 | ❌ 单源 | 一般 | 云托管 SaaS | 按调用计费 |
| Brave Search | 独立索引层 | 自建 300 亿+ 网页索引，隐私友好 | ❌ 单源 | 一般 | 云托管 API | 免费额度 + 按量 |
| AnySearch | 国内垂直基建 | 20+ 自建垂类索引 + 意图路由 | ❌ 单源 | ✅ 原生 | 云托管 / 私有化 | 免费额度 + 按量 |
| 官方单引擎 MCP（百炼/智谱/千帆） | 单引擎包装 | 仅自家模型联网检索 | ❌ 单源 | ✅ | 云托管 Streamable HTTP | 按量（如百炼 29 元/千次） |
| SearXNG / DuckDuckGo MCP | 聚合 SERP 层 | 元搜索返回原始结果列表 | ⚠️ 多引擎但无仲裁 | 一般 | 本地自部署 | 免费 |

**一句话定位**：Tavily 们回答“搜到了什么”，DeepDig 回答“**哪些信息彼此印证、哪些存在冲突**”。多源仲裁 + 中文生态 + 零中间商，是目前检索分层中的空位。

### 项目质量自评

| 维度 | 现状 | 评估 |
| --- | --- | --- |
| 架构设计 | Fork-Join 管道、8s 熔断、Provider 完全隔离、entry-point 插件机制 | ✅ 清晰、可扩展 |
| 工程质量 | ruff 全绿、20 个离线单测（HTTP 全 mock）、CI 3.11/3.12 矩阵 | ✅ 达标 |
| 容错与韧性 | 重试 + 滑动窗口健康统计 + 单点失败不阻断 | ✅ 生产可用基线 |
| 上下文效率 | 单引擎预算截断、去重、TTL 缓存 | ✅ 对 IDE 场景友好 |
| 生态成熟度 | v0.1.0 早期，社区与插件生态待建设 | ⚠️ 早期阶段 |
| Benchmark | 评测工具已就位，公开数据集结果待发布 | ⚠️ 待补数据 |

### 客观局限（选型须知）

- **成本结构**：每次查询消耗三家 LLM API token；对比免费方案（SearXNG/DuckDuckGo）无成本优势，换取的是可信度。
- **延迟**：LLM 综合检索需 3~6s，慢于直接 SERP API（<1s）；已用 8s 熔断 + 缓存约束上界。
- **结果形态**：返回的是各引擎**综合后的结论**而非原始 SERP 列表——适合事实核查，不适合需要原始结果自己重排的场景（那请用 Tavily/Brave）。
- **成熟度**：v0.1.0，API 可能随版本调整。

**选型建议**：实时事实核查、技术调研、中文场景、不想被单一搜索商锁定 → DeepDig；英文深度研究 → Tavily/Exa；批量抓取建库 → Firecrawl；零成本兜底 → SearXNG。

<sub>来源：[搜索类 MCP Server 选型全解析（2026）](https://www.ithome.com/1/008/767.htm) · [AI Agent 搜索 MCP 选型推荐](https://www.ithome.com/1/008/153.htm) · [阿里云百炼联网搜索 MCP](https://help.aliyun.com/zh/model-studio/web-search-for-coding-plan) · [智谱搜索 MCP Server](https://www.iai88.com/go/?url=aHR0cHM6Ly9kb2NzLmJpZ21vZGVsLmNuL2NuL2NvZGluZy1wbGFuL21jcC9zZWFyY2gtbWNwLXNlcnZlcg==)</sub>

---

## 目录结构

```text
deepdig/
├── pyproject.toml              # 项目依赖与 CLI 入口声明
├── README.md                   # 项目工程文档与规范说明
├── LICENSE                     # MIT 开源协议
├── .env.example                # 环境变量配置模板
├── .github/workflows/ci.yml    # CI：ruff + pytest（Python 3.11/3.12 矩阵）
├── skill/
│   └── deepdig.md              # 配套 IDE Skill 规范（调用时机与仲裁规则）
├── bench/
│   ├── queries.json            # 基准评测 query 集（新闻/技术/争议论断）
│   └── run_bench.py            # Benchmark 评测脚本（信源/延迟/交叉验证）
├── deepdig/
│   ├── __init__.py
│   ├── server.py               # FastMCP 入口、工具注册、缓存、去重与网关
│   ├── config.py               # 环境变量加载与超时参数控制
│   └── providers/
│       ├── __init__.py
│       ├── base.py             # 抽象基类：超时熔断、重试与健康统计
│       ├── qwen.py             # DashScope (Qwen 联网接口)
│       ├── glm.py              # Zhipu AI (GLM web_search)
│       └── kimi.py             # Moonshot (Kimi 研报提取)
└── tests/
    ├── test_providers.py       # 并发与熔断单元测试
    └── test_server.py          # 去重/缓存/截断/门禁单元测试
```

---

## 快速上手

### 1. 安装依赖

需要 Python 3.11 及以上环境：

```bash
git clone https://github.com/ai-guru-global/deepdig.git
cd deepdig

# 方式一：uv（推荐）
uv sync && uv run deepdig

# 方式二：pip
pip install -e .
python -m deepdig.server
```

### 2. 配置环境变量

复制环境变量模板并填入对应平台的 API Key：

```bash
cp .env.example .env
```

```ini
# .env
DASHSCOPE_API_KEY="sk-xxxx"       # 阿里百炼
ZHIPU_API_KEY="xxxx.xxxx"         # 智谱开放平台
MOONSHOT_API_KEY="sk-xxxx"        # Moonshot Kimi (可选)
```

**可选调优参数**（均有默认值，统一前缀 `DEEPDIG_`）：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DEEPDIG_TIMEOUT` | `8.0` | 单引擎熔断超时（秒） |
| `DEEPDIG_MAX_CONTENT_CHARS` | `2000` | 单引擎正文上下文预算（字符，超出智能截断） |
| `DEEPDIG_CACHE_TTL` | `300` | 查询结果缓存 TTL（秒，`0` 关闭） |
| `DEEPDIG_MAX_CONCURRENCY` | `4` | 跨引擎并发请求上限 |
| `DEEPDIG_QWEN_MODEL` / `DEEPDIG_GLM_MODEL` / `DEEPDIG_KIMI_MODEL` | 见 `config.py` | 各引擎模型覆盖 |

---

## IDE 配置接入指南

### 1. 配置 MCP Server

在 **Qoder** 或 **CodeBuddy** 的 MCP 配置文件（如 `mcp_settings.json`）中添加本地运行项：

```json
{
  "mcpServers": {
    "deepdig": {
      "command": "python",
      "args": ["-m", "deepdig.server"],
      "env": {
        "DASHSCOPE_API_KEY": "你的百炼Key",
        "ZHIPU_API_KEY": "你的智谱Key",
        "MOONSHOT_API_KEY": "你的KimiKey"
      }
    }
  }
}
```

### 2. 配置配套 IDE Skill 规则 (`deepdig.md`)

仓库已内置 Skill 规范 [`skill/deepdig.md`](./skill/deepdig.md)，将其复制/链接到 IDE 的 Skills 目录即可。核心内容：

```markdown
# Role: Multi-Source Fact Verifier & Deep Searcher

When handling queries that involve real-time facts, rapidly changing news, API changes, or disputed technical claims:
1. Always call the `deepdig` MCP tool with an optimized keyword query.
2. Read the returned multi-source outputs ([Qwen Source], [GLM Source], etc.).
3. Cross-reference assertions:
   - Where sources agree, distill into concise conclusions.
   - Where sources conflict, explicitly point out discrepancies.
4. Always provide traceable markdown source references.
```

---

## 部署形态

### BYOK 本地模式（默认）

stdio 传输，随 IDE 启动，凭据仅存在于本地环境变量，即上文"快速上手"路径。

### 远端 Gateway 模式（可选）

服务端集中托管 API Key，客户端零配置、不接触底层 Token：

```bash
# 服务端启动（默认监听 127.0.0.1:8000，可用 DEEPDIG_HOST / DEEPDIG_PORT 调整）
DEEPDIG_TRANSPORT=sse DEEPDIG_ACCESS_TOKEN="团队共享令牌" uv run deepdig
```

```json
{
  "mcpServers": {
    "deepdig": {
      "url": "http://your-host:8000/sse",
      "headers": { "Authorization": "Bearer 团队共享令牌" }
    }
  }
}
```

- 支持 `sse` 与 `streamable-http` 两种传输。
- 设置 `DEEPDIG_ACCESS_TOKEN` 后启用 Bearer 门禁（HTTP Header 或 `?token=` 均可），并同步校验工具调用的 `token` 参数；公网部署务必开启。
- 跨引擎并发由 `DEEPDIG_MAX_CONCURRENCY` 信号量统一限流。

---

## 扩展 Provider

DeepDig 通过 Python entry-points 支持第三方检索源插件（坚守"认知层"定位：插件应接入模型预热的检索结果或正规搜索 API，而非自建爬虫）。

在你的包中声明 entry-point：

```toml
[project.entry-points."deepdig.providers"]
tavily = "tavily_deepdig:TavilyProvider"
```

实现类需继承 `deepdig.providers.SearchProvider`，设置全局唯一的 `name`，并覆写 `is_configured()` 报告凭据是否就绪：

```python
from deepdig.providers import SearchProvider, ProviderResult

class TavilyProvider(SearchProvider):
    name = "tavily"
    display_name = "Tavily Search"

    def is_configured(self) -> bool:
        return bool(self.settings.tavily_api_key)

    async def search(self, query: str) -> ProviderResult:
        ...
```

插件加载失败、名字冲突或未配置的插件会被安全跳过并在 stderr 告警，绝不影响服务器启动与其余引擎。

---

## 发布与分发

- **发布流程**：GitHub Release 发布时，`publish.yml` 自动 lint + test → `uv build` → 通过 [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) 发布（无需本地凭证）。
- **一次性配置**：在 PyPI 上为 `deepdig` 项目登记 Trusted Publisher（GitHub 仓库 + workflow 名 `publish.yml` + environment `pypi`）。
- **发布后安装**：

```bash
uvx deepdig                # 零安装直接运行 stdio 服务
pip install deepdig
```

---

## Benchmark 评估维度

评估 `deepdig` 对比单一模型直搜的收益基准：

| 评估维度 | 指标定义 | 目标表现 |
| --- | --- | --- |
| **信源覆盖度 (Source Recall)** | 单次回答中有效独立域名/信源总数 | 相比单模型直搜提升 40%~70% |
| **真实性与抗幻觉 (Fact Accuracy)** | 核心事实论点在原文中的可溯源比例 | 错误与臆造事实率显著降低 |
| **端到端耗时 (Latency Control)** | 并发请求并完成结果聚合的耗时 | 依靠异步非阻塞严格控制在 3~6 秒内 |

运行方式（需至少配置一个引擎 Key）：

```bash
uv run python bench/run_bench.py          # 使用内置 query 集，报告写入 bench/reports/
uv run python bench/run_bench.py --full   # 报告内嵌完整聚合结果，便于人工溯源审计
```

---

## 参与贡献

欢迎 PR！开发环境搭建、约定与 Provider 插件指南见 [CONTRIBUTING.md](./CONTRIBUTING.md)。Issue 请使用模板提交；安全漏洞请勿公开 Issue，走 [SECURITY.md](./SECURITY.md) 的私密渠道。

## 更新日志

见 [CHANGELOG.md](./CHANGELOG.md)（遵循 Keep a Changelog + SemVer）。

---

## 许可证 & 维护者

- **开源协议**：[MIT License](./LICENSE)
- **维护组织**：[ai-guru-global](https://github.com/ai-guru-global)
- **作者**：[Allen Galler (@allengaller)](https://github.com/allengaller)

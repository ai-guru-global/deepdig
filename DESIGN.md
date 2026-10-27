# DESIGN.md — DeepDig 文档与工具的视觉世界

> Established by the Carbon-white redesign of `gtm/index.html` (2026-10-27) and
> inherited by `config/index.html`. Brief-pinned direction: 企业级 · 白底 · IBM Carbon.

## World

Enterprise precision-document, in the grammar of IBM Carbon: white ground,
1px hairlines, flat gray layers, one interactive blue. Depth comes from
structure (rules, tiles, the black masthead) — never from shadows or radius.
Zero border-radius everywhere; pills are banned except nothing currently
needs one.

## Tokens

### Color

| Role | Value |
| --- | --- |
| Ground | `#ffffff` |
| Layer / tile | `#f4f4f4` (hover `#e8e8e8`) |
| Text primary / secondary / tertiary | `#161616` / `#525252` / `#6f6f6f` |
| Interactive (link, primary button, active) | `#0f62fe` (hover `#0353e9`, tint `#edf5ff`) |
| Success | `#24a148` (tag `#a7f0ba`/`#0e6027`) |
| Warning | `#f1c21b` family (tag `#fdd13a`/`#493d00`) |
| Danger | `#da1e28` (tag `#ffd7d9`/`#a2191f`) |
| Info tag | `#d0e2ff`/`#003a6d` |
| Borders | `#e0e0e0` (subtle) / `#8d8d8d` (strong) |
| Inverse (masthead, code panels, footer) | `#161616` bg, `#f4f4f4`/`#c6c6c6` ink, `#78a9ff` links, `#8d8d8d`→`#a8a8a8` dim |

### Type

- **IBM Plex Sans** (400/500/600/700) + Noto Sans SC fallback — UI and reading.
- **IBM Plex Mono** (400/500/600) — document numbers, tags, data, code, breadcrumbs.
- Scale: display `clamp(30–50px)/700` (GTM lead) · h1 `24–32/700` (tools) ·
  h2 `19–27/700` · h3 `16–17/600` · body `15/1.7` · tables `13.5` ·
  helpers/labels `12–13` · tags `12`. Heading letter-spacing `-0.01em` to `-0.015em`.
- Tabular numerals (`font-variant-numeric: tabular-nums`) on all data figures.

### Space & structure

- 8px base; page padding `clamp(16px, 4vw, 40px)`; content max 1200px.
- Separation = 1px `#e0e0e0` rules and `#f4f4f4` layers; **no shadows** except
  the map's active chip (`0 2px 6px rgba(22,22,22,.25)`) and toast.
- Tiles: flat `#f4f4f4`, 1px gap grids; data tables: `#f4f4f4` header row,
  12px secondary header text, 1px row rules, hover `#f4f4f4`.
- Notifications: 3px colored left edge on `#edf5ff`/`#fff1f1`/`#fcf4d6` (Carbon
  inline-notification pattern — the sanctioned use of a left border).

### Components

Tag (squared, 12px) · data table · tile/stat · breadcrumb bar · black 48px
masthead · TOC rail with 2px active rule · progress-style phase timeline ·
flat bar funnel · quadrant chart (the one grid-line canvas) · text input
(`#f4f4f4` bg, blue inset focus ring, red invalid state) · primary/tertiary/
ghost-danger buttons (40px, squared) · dark code preview with tabs.

### Motion

Carbon productive easing `cubic-bezier(0.2,0,0.38,0.9)`, 110–450ms. One
authored pattern per surface: hero/section reveal (fade-up, IntersectionObserver,
`.in-view`), disabled under `prefers-reduced-motion`. Hover states are plain
background steps — no transforms on text.

### Voice

zh-CN, factual, declarative; controls name their action (复制当前预览 /
下载 .env); errors name problem + recovery. English reserved for product
terms and mono metadata (DEEPDIG · BYOK · LOCAL-ONLY).

## Non-negotiables

1. No dark-mode remnant of the previous dossier world (no stamps, grain, glow).
2. No rounded corners, no gradient text, no decorative left borders outside
   notifications.
3. Blue `#0f62fe` is the only accent on white; green/yellow/red carry state
   semantics only.
4. New surfaces inherit this world; changes to tokens require updating this
   file and `.impeccable/design.json` together.

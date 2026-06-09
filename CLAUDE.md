# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository is two things in one:

1. **A global cuisine menu dataset** ("环球美食菜单") with a derived AI knowledge base — primarily Chinese content with English translations, prices in CNY.
2. **A Claude Code / multi-agent plugin** (`menus-recommender`) that exposes the dataset as a recommendation skill triggered by phrases like "推荐晚餐" / "不知道吃什么".

## Data Scale

- 396 dishes across 10 regions, 40+ cuisines, 67 sub-styles
- Price range: ¥6 ~ ¥388

## Repository Layout

### Data (source of truth + derived indexes)

- `menu.json` — the single source of truth. Hierarchical: regions → cuisines → sub_styles → dishes. Each dish has `id`, `name`, `name_en`, `price`, `description`.
- `knowledge_base/` — derived indexes:
  - `kb_dish_index.json` — flat array of all dishes with denormalized fields
  - `kb_hierarchy.json` — region → cuisine → sub_style → dish ID tree
  - `kb_cuisine_index.json` — cuisine name → dishes
  - `kb_keyword_index.json` — keyword → dish IDs (taste/ingredient/type)
  - `kb_price_index.json` — price-tiered: 经济(≤20) / 实惠(21-50) / 中档(51-100) / 高档(101-200) / 奢华(>200)
  - `by_region/` — human-readable Markdown per region

### Plugin

- `.claude-plugin/plugin.json` — Claude Code plugin manifest
- `.claude-plugin/marketplace.json` — marketplace index (lets users `/plugin install`)
- `skills/recommend-dish/SKILL.md` — auto-triggered skill definition
- `skills/recommend-dish/references/` — extended docs (e.g., fallback chain)
- `scripts/recommender.py` — weighted-random recommendation engine (Python 3, stdlib only)
- `GEMINI.md` — Gemini CLI adapter (same workflow)
- `mcp-server/` — MCP server package (`menus-mcp`), publishable to PyPI. `menus_mcp/recommender.py` and `menus_mcp/knowledge_base` are symlinks to the source-of-truth files at the repo root.

## Dish ID Convention

`{cuisine_prefix}{category}{sequence}`. Examples:
- `cn_ch_001` — China / Chuan (川菜) / hot dishes / 001
- `cn_y_101` — China / Yue (粤菜) / sub-category 1xx
- `jp_403` — Japan / category 4 / 03

## Data Consistency

`menu.json` is the source of truth. When modifying it, the `knowledge_base/` files must be re-derived to stay in sync. The recommender script reads only from `knowledge_base/`, never from `menu.json`.

## Running the Recommender Locally

```bash
python3 scripts/recommender.py --count 3 --keywords "辣,牛肉" --price-tier "实惠"
```

Output is a single line of JSON. See `scripts/recommender.py --help` for full parameter list. Zero dependencies (Python 3 standard library only).

## Algorithm Notes

The recommender does three non-obvious things:

1. **Hard-filters by keyword union when keywords are provided** — a dish must match at least one keyword. This prevents the LLM from getting back unrelated dishes when the user expresses a clear preference.
2. **Inverse-frequency cuisine weighting** (`1/sqrt(cuisine_count)`) — prevents large cuisines (中餐 ~35%) from dominating draws, without over-correcting toward 3-dish micro-cuisines.
3. **Diversity greedy** — caps same-cuisine picks at `ceil(count/3)`, so a 3-dish recommendation isn't all 川菜.

Keyword multi-hit boost is mild (`2^(hits-1)`) because the hard filter already enforces relevance.

## Plugin Architecture Decisions

- Skill (not just SKILL.md prose) because data is too large to inline and weighted random is deterministic logic.
- Plugin (not standalone skill) because skills can only be distributed inside plugins.
- Python stdlib (not Node/Rust) for zero-install portability.
- Reused by the MCP server variant under `mcp-server/` via symlinks (one source of truth for both the script and the knowledge base).

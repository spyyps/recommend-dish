"""menus-mcp: 全球美食推荐 MCP server。

通过 stdio 暴露 recommend_dishes / list_keywords 两个工具。
"""
from __future__ import annotations

import importlib.util
import json
import os
import random
import sys
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent


def _load_recommender():
    """从 package 内的 recommender.py 加载，支持 pip install 和源码运行两种场景。"""
    rec_path = PKG_DIR / "recommender.py"
    if not rec_path.exists():
        raise RuntimeError(f"找不到 recommender.py: {rec_path}")
    spec = importlib.util.spec_from_file_location("_menus_recommender", rec_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _resolve_kb_dir() -> Path:
    """优先环境变量 MENUS_KB_DIR，否则用 package 内的 knowledge_base/。"""
    env = os.environ.get("MENUS_KB_DIR", "")
    if env:
        p = Path(env).expanduser().resolve()
        if p.exists():
            return p
    candidate = PKG_DIR / "knowledge_base"
    if candidate.exists():
        return candidate
    raise RuntimeError(
        f"找不到 knowledge_base 目录（尝试过 MENUS_KB_DIR 与 {candidate}）"
    )


def main() -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        print("错误：缺少 mcp 依赖。请 `pip install mcp` 或 `pip install menus-mcp`", file=sys.stderr)
        sys.exit(1)

    recommender = _load_recommender()
    kb_dir = _resolve_kb_dir()
    kb_cache = {"loaded": None}

    def get_kb():
        if kb_cache["loaded"] is None:
            kb_cache["loaded"] = recommender.load_kb(kb_dir)
        return kb_cache["loaded"]

    mcp = FastMCP("menus-recommender")

    @mcp.tool()
    def recommend_dishes(
        count: int = 1,
        keywords: str = "",
        price_tier: str = "",
        max_price: int = 0,
        cuisine: str = "",
        region: str = "",
        geo: str = "",
        exclude_ids: str = "",
        seed: int = 0,
        alternates: int = 3,
    ) -> str:
        """基于全球美食知识库做加权随机推荐：1 道主选 + N 道备选，互不重复。

        当用户表达就餐意向（推荐晚餐、不知道吃什么、想吃点辣的等）时调用。

        Args:
            count: 主选数量，默认 1。
            alternates: 备选数量，默认 3（与主选互不重复，供「不喜欢可换」）。
            keywords: 逗号分隔的关键词（OR 语义）。白名单：
                口味 麻辣/辣/甜/酸/咸/鲜
                食材 海鲜/牛肉/羊肉/猪肉/鸡肉/素食
                类型 面食/米饭类/汤/甜品/烧烤/火锅/咖喱/汉堡披萨/饮品
                否定意图（如「不要太辣」）不要传入。
            price_tier: 经济(≤20)/实惠(21-50)/中档(51-100)/高档(101-200)/奢华(>200)
            max_price: 价格上限（CNY）
            cuisine: 菜系名（如「川菜」「日本料理」）或 cuisine_id
            region: 地区名（如「中华料理」）或 region_id
            geo: 地理大类（如「亚洲」「欧洲」）
            exclude_ids: 逗号分隔的菜品 ID，用于「换一批」时去重
            seed: 随机种子，0 表示用系统时间

        Returns:
            JSON 字符串：{main, alternates, dishes, exhausted, filters, candidate_pool_size, returned}
            - main: 主选菜品（对象）
            - alternates: 备选菜品数组（默认 3 个，与主选互不重复）
            - dishes: 向后兼容字段 = [main, *alternates]
            exhausted=true 时应触发兜底链（重试放宽、网络搜索、LLM 常识）。
        """
        kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
        exclude_set = {k.strip() for k in exclude_ids.split(",") if k.strip()}
        rng = random.Random(seed if seed else None)

        result = recommender.recommend(
            get_kb(),
            count=max(1, count),
            alternates=max(0, alternates),
            keywords=kw_list,
            price_tier=price_tier,
            max_price=max_price,
            cuisine=cuisine,
            region=region,
            geo=geo,
            exclude_ids=exclude_set,
            relax=True,
            rng=rng,
        )
        return json.dumps(result, ensure_ascii=False)

    @mcp.tool()
    def list_keywords() -> str:
        """列出推荐器支持的全部关键词与价格档。"""
        return json.dumps(
            {
                "taste": ["麻辣", "辣", "甜", "酸", "咸", "鲜"],
                "ingredient": ["海鲜", "牛肉", "羊肉", "猪肉", "鸡肉", "素食"],
                "type": [
                    "面食", "米饭类", "汤", "甜品", "烧烤",
                    "火锅", "咖喱", "汉堡披萨", "饮品",
                ],
                "price_tiers": ["经济", "实惠", "中档", "高档", "奢华"],
                "note": "不在白名单内的关键词会被忽略，可能导致候选池为空。",
            },
            ensure_ascii=False,
        )

    mcp.run()


if __name__ == "__main__":
    main()

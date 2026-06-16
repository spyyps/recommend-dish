#!/usr/bin/env python3
"""
环球美食菜单加权随机推荐引擎

零依赖（仅 Python 3 标准库）。读取 knowledge_base/ 下的索引文件，
按用户偏好做加权随机采样，输出 JSON 到 stdout。

输出结构：1 道主选（main）+ N 道备选（alternates），互不重复。
为向后兼容，dishes = [main, *alternates]。

调用约定见 --help 或仓库内 SKILL.md。
"""
from __future__ import annotations

import argparse
import bisect
import json
import math
import os
import random
import sys
from collections import Counter
from itertools import accumulate
from pathlib import Path

PRICE_TIERS = ["经济", "实惠", "中档", "高档", "奢华"]
PRICE_TIER_KEYS = {
    "经济": "经济(<=20)",
    "实惠": "实惠(21-50)",
    "中档": "中档(51-100)",
    "高档": "高档(101-200)",
    "奢华": "奢华(>200)",
}
KEYWORD_HIT_MULTIPLIER = 2.0

# 默认推荐配置：1 道主选 + 3 道备选
DEFAULT_COUNT = 1
DEFAULT_ALTERNATES = 3


def load_kb(kb_dir: Path) -> dict:
    def _read(name: str):
        with open(kb_dir / name, "r", encoding="utf-8") as f:
            return json.load(f)

    dishes = _read("kb_dish_index.json")
    # 预计算：dish_id -> dish 字典 + 菜系计数，避免 recommend() 每次重算
    dish_map = {d["id"]: d for d in dishes}
    cuisine_counter = Counter(d.get("cuisine", "") for d in dishes)
    return {
        "dishes": dishes,
        "dish_map": dish_map,
        "cuisine_counter": cuisine_counter,
        "keywords": _read("kb_keyword_index.json"),
        "prices": _read("kb_price_index.json"),
    }


def build_dish_map(dishes: list) -> dict:
    """向后兼容：外部可能直接调用此函数。"""
    return {d["id"]: d for d in dishes}


def filter_candidates(
    dishes: list,
    *,
    cuisine: str,
    region: str,
    geo: str,
    price_tier: str,
    max_price: int,
    exclude_ids: set,
    keywords: list,
    keyword_index: dict,
    price_index: dict,
) -> list:
    tier_ids = None
    if price_tier and price_tier in PRICE_TIER_KEYS:
        tier_ids = set(price_index.get(PRICE_TIER_KEYS[price_tier], []))

    # 关键词硬过滤：用户传了关键词，则菜品必须至少命中一个
    # 注意：即使所有传入关键词在索引里都没匹配（空集 union），也要执行硬过滤，避免返回与用户意图无关的全集
    keyword_union: set | None = None
    if keywords:
        keyword_union = set()
        for kw in keywords:
            keyword_union.update(keyword_index.get(kw, []))

    # 性能优化：当有关键词命中时，从命中的 ID 集合出发遍历，
    # 通常远小于全库（如"牛肉"命中 ~30 道而非 462 道），省去无效遍历。
    # 命中集合为空时仍需遍历全库（结果是空，符合硬过滤语义）。
    if keyword_union is not None and keyword_union:
        iterable = (d for d in dishes if d["id"] in keyword_union)
    else:
        iterable = dishes

    candidates = []
    for d in iterable:
        if d["id"] in exclude_ids:
            continue
        if cuisine and d.get("cuisine") != cuisine and d.get("cuisine_id") != cuisine:
            continue
        if region and d.get("region") != region and d.get("region_id") != region:
            continue
        if geo and d.get("geo") != geo:
            continue
        if max_price > 0 and d.get("price", 0) > max_price:
            continue
        if tier_ids is not None and d["id"] not in tier_ids:
            continue
        if keyword_union is not None and d["id"] not in keyword_union:
            continue
        candidates.append(d)
    return candidates


def relax_price(price_tier: str) -> str:
    if not price_tier or price_tier not in PRICE_TIERS:
        return ""
    idx = PRICE_TIERS.index(price_tier)
    # 优先放宽到更便宜的档（用户通常能接受），否则向上
    if idx > 0:
        return ""  # 直接去掉档位约束
    return ""


def compute_weights(
    candidates: list,
    keywords: list,
    keyword_index: dict,
    cuisine_counter: Counter,
) -> list:
    keyword_id_sets = {kw: set(keyword_index.get(kw, [])) for kw in keywords}

    weights = []
    for d in candidates:
        hits = sum(1 for kw in keywords if d["id"] in keyword_id_sets[kw])
        # 候选已经过关键词硬过滤；这里只用命中数加权（命中越多越偏向）
        kw_weight = (KEYWORD_HIT_MULTIPLIER ** max(hits - 1, 0)) if keywords else 1.0

        cuisine_count = max(1, cuisine_counter.get(d.get("cuisine"), 1))
        cuisine_weight = 1.0 / math.sqrt(cuisine_count)

        weights.append(kw_weight * cuisine_weight)
    return weights


def weighted_sample_with_diversity(
    candidates: list,
    weights: list,
    count: int,
    rng: random.Random,
) -> list:
    """无放回加权采样 + 同菜系多样性约束。

    性能：使用累积权重数组 + 二分查找，单次抽取 O(log n)，
    总体 O(k log n)（k = 实际抽取数），优于原先每次重算 sum 的 O(k·n)。
    """
    if not candidates:
        return []
    if len(candidates) <= count:
        return list(candidates)

    # 多采样几倍，再贪心去重
    pool_size = min(len(candidates), count * 6)
    picked: list = []
    picked_ids = set()
    # 维护剩余候选的 (候选, 权重) 并用累积权重做二分
    remaining = list(zip(candidates, weights))

    while remaining and len(picked) < pool_size:
        # 构造累积权重前缀和（仅对剩余项）
        w_only = [w for _, w in remaining]
        total = w_only[-1] if w_only else 0.0
        # accumulate 比 each step sum 快且清晰
        cum = list(accumulate(w_only))
        if cum[-1] <= 0:
            break
        r = rng.uniform(0, cum[-1])
        # bisect 找到第一个 cum[i] >= r 的下标
        i = bisect.bisect_left(cum, r)
        if i >= len(remaining):
            i = len(remaining) - 1
        d = remaining[i][0]
        if d["id"] not in picked_ids:
            picked.append(d)
            picked_ids.add(d["id"])
        remaining.pop(i)

    # 多样性贪心：同 cuisine 上限
    max_per_cuisine = max(1, math.ceil(count / 3))
    cuisine_seen: Counter = Counter()
    result = []
    for d in picked:
        c = d.get("cuisine", "")
        if cuisine_seen[c] >= max_per_cuisine:
            continue
        result.append(d)
        cuisine_seen[c] += 1
        if len(result) >= count:
            break

    # 兜底：若多样性约束导致不足，从剩余 picked 补足
    if len(result) < count:
        for d in picked:
            if d in result:
                continue
            result.append(d)
            if len(result) >= count:
                break

    return result


def format_dish(d: dict) -> dict:
    return {
        "id": d["id"],
        "name": d.get("name", ""),
        "name_en": d.get("name_en", ""),
        "price": d.get("price"),
        "cuisine": d.get("cuisine", ""),
        "region": d.get("region", ""),
        "description": d.get("description", ""),
    }


def recommend(
    kb: dict,
    *,
    count: int,
    keywords: list,
    price_tier: str,
    max_price: int,
    cuisine: str,
    region: str,
    geo: str,
    exclude_ids: set,
    relax: bool,
    rng: random.Random,
    alternates: int = DEFAULT_ALTERNATES,
) -> dict:
    dishes = kb["dishes"]
    cuisine_counter = kb.get("cuisine_counter")
    if cuisine_counter is None:
        cuisine_counter = Counter(d.get("cuisine", "") for d in dishes)

    # 总采样数 = 主选 + 备选
    total = max(1, count) + max(0, alternates)

    applied_filters = {
        "count": count,
        "alternates": alternates,
        "keywords": keywords,
        "price_tier": price_tier,
        "max_price": max_price if max_price > 0 else None,
        "cuisine": cuisine or None,
        "region": region or None,
        "geo": geo or None,
        "exclude_count": len(exclude_ids),
        "relaxed": False,
    }

    candidates = filter_candidates(
        dishes,
        cuisine=cuisine,
        region=region,
        geo=geo,
        price_tier=price_tier,
        max_price=max_price,
        exclude_ids=exclude_ids,
        keywords=keywords,
        keyword_index=kb["keywords"],
        price_index=kb["prices"],
    )

    # 自动松弛一次
    if relax and len(candidates) < total and price_tier:
        applied_filters["relaxed"] = True
        applied_filters["relax_note"] = f"价格档 [{price_tier}] 候选不足，已去除价格约束"
        candidates = filter_candidates(
            dishes,
            cuisine=cuisine,
            region=region,
            geo=geo,
            price_tier="",
            max_price=max_price,
            exclude_ids=exclude_ids,
            keywords=keywords,
            keyword_index=kb["keywords"],
            price_index=kb["prices"],
        )

    if not candidates:
        return {
            "main": None,
            "alternates": [],
            "dishes": [],
            "exhausted": True,
            "reason": "no_candidates",
            "filters": applied_filters,
            "candidate_pool_size": 0,
        }

    weights = compute_weights(
        candidates,
        keywords,
        kb["keywords"],
        cuisine_counter,
    )

    picked = weighted_sample_with_diversity(candidates, weights, total, rng)

    # 拆分主选与备选：第 1 个为 main，其后 alternates 个为备选
    picked_list = [format_dish(d) for d in picked]
    main = picked_list[0] if picked_list else None
    # 备选数量以参数 alternates 为准（当 count>1 时，多余的主选并入 dishes 兼容字段）
    n_main = max(1, count)
    alt = picked_list[n_main:n_main + max(0, alternates)]

    exhausted = len(picked_list) < total

    return {
        "main": main,
        "alternates": alt,
        # 向后兼容：dishes = [main, *alternates]
        "dishes": picked_list,
        "exhausted": exhausted,
        "filters": applied_filters,
        "candidate_pool_size": len(candidates),
        "returned": len(picked_list),
    }


def parse_args(argv: list) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="环球美食加权随机推荐（1 主选 + N 备选）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help=f"主选数量（默认 {DEFAULT_COUNT}）")
    parser.add_argument(
        "--alternates",
        type=int,
        default=DEFAULT_ALTERNATES,
        help=f"备选数量（默认 {DEFAULT_ALTERNATES}，与主选互不重复）",
    )
    parser.add_argument(
        "--keywords",
        type=str,
        default="",
        help="逗号分隔的关键词。支持：麻辣/辣/甜/酸/咸/鲜、海鲜/牛肉/羊肉/猪肉/鸡肉/素食、面食/米饭类/汤/甜品/烧烤/火锅/咖喱/汉堡披萨/饮品",
    )
    parser.add_argument(
        "--price-tier",
        type=str,
        default="",
        choices=["", *PRICE_TIERS],
        help="价格档位：经济(≤20)/实惠(21-50)/中档(51-100)/高档(101-200)/奢华(>200)",
    )
    parser.add_argument("--max-price", type=int, default=0, help="价格上限（CNY）")
    parser.add_argument("--cuisine", type=str, default="", help="菜系名或 cuisine_id，如 川菜 / cn_chuan")
    parser.add_argument("--region", type=str, default="", help="地区名或 region_id，如 中华料理 / asia_china")
    parser.add_argument("--geo", type=str, default="", help="地理大类，如 亚洲 / 欧洲")
    parser.add_argument("--exclude-ids", type=str, default="", help="逗号分隔的已推荐菜品 ID，用于换一批")
    parser.add_argument("--relax", action="store_true", default=True, help="候选不足时自动放宽价格档（默认开）")
    parser.add_argument("--no-relax", dest="relax", action="store_false", help="禁止自动放宽")
    parser.add_argument("--seed", type=int, default=0, help="随机种子（0=系统时间）")
    parser.add_argument(
        "--kb-dir",
        type=str,
        default="",
        help="知识库目录。默认查找脚本同级 ../knowledge_base 或环境变量 MENUS_KB_DIR",
    )
    return parser.parse_args(argv)


def resolve_kb_dir(arg_dir: str) -> Path:
    if arg_dir:
        return Path(arg_dir).expanduser().resolve()
    env_dir = os.environ.get("MENUS_KB_DIR", "")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    here = Path(__file__).resolve().parent
    candidate = here.parent / "knowledge_base"
    if candidate.exists():
        return candidate
    raise SystemExit(
        "找不到 knowledge_base 目录，请用 --kb-dir 指定或设置 MENUS_KB_DIR 环境变量"
    )


def main(argv: list) -> int:
    args = parse_args(argv)

    kb_dir = resolve_kb_dir(args.kb_dir)
    if not kb_dir.exists():
        print(f"错误：知识库目录不存在: {kb_dir}", file=sys.stderr)
        return 2

    try:
        kb = load_kb(kb_dir)
    except (OSError, json.JSONDecodeError) as e:
        print(f"错误：读取知识库失败: {e}", file=sys.stderr)
        return 2

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    exclude_ids = {k.strip() for k in args.exclude_ids.split(",") if k.strip()}

    rng = random.Random(args.seed if args.seed else None)

    result = recommend(
        kb,
        count=max(1, args.count),
        alternates=max(0, args.alternates),
        keywords=keywords,
        price_tier=args.price_tier,
        max_price=args.max_price,
        cuisine=args.cuisine,
        region=args.region,
        geo=args.geo,
        exclude_ids=exclude_ids,
        relax=args.relax,
        rng=rng,
    )

    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

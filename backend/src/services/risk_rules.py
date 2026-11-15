"""算法 B｜僵尸与钓鱼挂牌识别。

簇内价格离散度 ``(p90-p10)/median``；最低价相对簇中位偏离 > 10% 的挂牌标 ``bait``；
挂牌 > 180 天且带看数为 0 的挂牌标 ``stale``；离散度 > 10% 打 ``spread``；
风险分 0-100 = ``45*钓鱼 + 35*僵尸 + min(20, 离散度*200)``，供复核队列分诊。
"""
from __future__ import annotations

from collections.abc import Sequence

from src.constants.limits import (
    BAIT_DEVIATION,
    RISK_BAIT_POINTS,
    RISK_HIGH_THRESHOLD,
    RISK_MEDIUM_THRESHOLD,
    RISK_SPREAD_CAP,
    RISK_STALE_POINTS,
    SPREAD_TAG_THRESHOLD,
    STALE_DAYS,
)


def risk_level_of(score: int) -> str:
    if score >= RISK_HIGH_THRESHOLD:
        return "high"
    if score >= RISK_MEDIUM_THRESHOLD:
        return "medium"
    if score > 0:
        return "low"
    return "none"


def scan_cluster(members: Sequence[dict], golden: dict) -> dict:
    """``members``：``[{"id", "lid", "price_num", "listed_days", "views", "status"}]``。"""
    median = int(golden.get("price_median") or 0)
    dispersion = float(golden.get("dispersion") or 0.0)
    tags: list[str] = []
    bait_ids: list[str] = []
    stale_ids: list[str] = []
    if median > 0:
        for member in members:
            price = member.get("price_num")
            if not price:
                continue
            deviation = (median - int(price)) / median
            if deviation > BAIT_DEVIATION:
                bait_ids.append(str(member.get("lid")))
    for member in members:
        listed_days = int(member.get("listed_days") or 0)
        views = int(member.get("views") or 0)
        if listed_days > STALE_DAYS and views == 0:
            stale_ids.append(str(member.get("lid")))
    if bait_ids:
        tags.append("bait")
    if stale_ids:
        tags.append("stale")
    if dispersion > SPREAD_TAG_THRESHOLD:
        tags.append("spread")

    spread_points = int(round(min(RISK_SPREAD_CAP, dispersion * 200)))
    score = 0
    if bait_ids:
        score += RISK_BAIT_POINTS
    if stale_ids:
        score += RISK_STALE_POINTS
    score += spread_points
    score = max(0, min(100, score))
    return {
        "risk_score": score,
        "risk_level": risk_level_of(score),
        "risk_tags": tags,
        "risk_detail": {
            "dispersion": round(dispersion, 4),
            "spread_points": spread_points,
            "bait_lids": sorted(bait_ids),
            "stale_lids": sorted(stale_ids),
            "price_median": median,
            "price_min": int(golden.get("price_min") or 0),
            "price_max": int(golden.get("price_max") or 0),
            "thresholds": {
                "bait_deviation": BAIT_DEVIATION,
                "stale_days": STALE_DAYS,
                "spread": SPREAD_TAG_THRESHOLD,
            },
        },
    }

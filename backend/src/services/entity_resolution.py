"""算法 A｜实体解析：blocking + 相似度 + 并查集 + golden record。

blocking：``community + layout + area_bucket``（面积 ±5㎡）；
相似度：``0.35*面积接近 + 0.25*价格接近 + 0.20*楼层匹配 + 0.10*朝向 + 0.10*标题 token``；
阈值 0.80 连边，并查集 + 传递闭包，簇置信取簇内最大成对分；
golden record：价格取簇内中位、面积取众数、中介数去重计数。
纯函数、确定性，不访问数据库与网络。
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from src.constants.limits import (
    AREA_BUCKET_M2,
    AREA_CLOSE_SPAN_M2,
    AREA_TOLERANCE_M2,
    FLOOR_BAND_MATCH,
    PRICE_CLOSE_SPAN,
    SIMILARITY_THRESHOLD,
    WEIGHT_AREA,
    WEIGHT_FLOOR,
    WEIGHT_ORIENTATION,
    WEIGHT_PRICE,
    WEIGHT_TITLE,
)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def area_close(left: float | None, right: float | None) -> float:
    if left is None or right is None:
        return 0.0
    return _clamp(1.0 - abs(left - right) / AREA_CLOSE_SPAN_M2)


def price_close(left: int | None, right: int | None) -> float:
    if not left or not right:
        return 0.0
    base = (abs(left) + abs(right)) / 2.0
    if base <= 0:
        return 0.0
    return _clamp(1.0 - abs(left - right) / base / PRICE_CLOSE_SPAN)


def floor_match(left: dict, right: dict) -> float:
    left_floor, right_floor = left.get("floor_num"), right.get("floor_num")
    if left_floor is not None and right_floor is not None:
        return 1.0 if left_floor == right_floor else 0.0
    left_band, right_band = left.get("floor_band") or "", right.get("floor_band") or ""
    if left_band and left_band == right_band:
        return FLOOR_BAND_MATCH
    return 0.0


def orientation_match(left: dict, right: dict) -> float:
    left_orientation = left.get("orientation_norm") or ""
    right_orientation = right.get("orientation_norm") or ""
    if not left_orientation or not right_orientation:
        return 0.0
    return 1.0 if left_orientation == right_orientation else 0.0


def title_jaccard(left: dict, right: dict) -> float:
    left_tokens = set(left.get("title_tokens") or [])
    right_tokens = set(right.get("title_tokens") or [])
    if not left_tokens or not right_tokens:
        return 0.0
    union = left_tokens | right_tokens
    if not union:
        return 0.0
    return len(left_tokens & right_tokens) / len(union)


def similarity(left: dict, right: dict) -> dict:
    """返回分项得分与加权总分（0..1，四位小数）。"""
    parts = {
        "area": round(area_close(left.get("area_num"), right.get("area_num")), 4),
        "price": round(price_close(left.get("price_num"), right.get("price_num")), 4),
        "floor": round(floor_match(left, right), 4),
        "orientation": round(orientation_match(left, right), 4),
        "title": round(title_jaccard(left, right), 4),
    }
    score = (
        WEIGHT_AREA * parts["area"]
        + WEIGHT_PRICE * parts["price"]
        + WEIGHT_FLOOR * parts["floor"]
        + WEIGHT_ORIENTATION * parts["orientation"]
        + WEIGHT_TITLE * parts["title"]
    )
    parts["score"] = round(score, 4)
    return parts


def block_key(normalized: dict) -> tuple[str, str, int] | None:
    bucket = None
    area = normalized.get("area_num")
    if area is not None:
        bucket = int(area // AREA_BUCKET_M2)
    community = normalized.get("community_norm") or ""
    layout = normalized.get("layout_norm") or ""
    if bucket is None or not community:
        return None
    return community, layout, bucket


def candidate_pairs(normalized: Sequence[dict]) -> list[tuple[int, int]]:
    """blocking 候选对：同 community + 同 layout + 相邻面积桶且 |Δ面积| ≤ 5㎡。"""
    buckets: dict[tuple[str, str, int], list[int]] = {}
    for index, norm in enumerate(normalized):
        key = block_key(norm)
        if key is None:
            continue
        buckets.setdefault(key, []).append(index)

    pairs: set[tuple[int, int]] = set()

    def _collect(left_indexes: list[int], right_indexes: list[int]) -> None:
        for left in left_indexes:
            left_area = normalized[left].get("area_num")
            for right in right_indexes:
                if left == right:
                    continue
                right_area = normalized[right].get("area_num")
                if left_area is None or right_area is None:
                    continue
                if abs(float(left_area) - float(right_area)) > AREA_TOLERANCE_M2 + 1e-9:
                    continue
                pairs.add((left, right) if left < right else (right, left))

    for (community, layout, bucket), indexes in buckets.items():
        _collect(indexes, indexes)
        neighbour = buckets.get((community, layout, bucket + 1))
        if neighbour:
            _collect(indexes, neighbour)
    return sorted(pairs)


class UnionFind:
    """并查集：支持路径压缩，按索引合并。"""

    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, node: int) -> int:
        while self.parent[node] != node:
            self.parent[node] = self.parent[self.parent[node]]
            node = self.parent[node]
        return node

    def union(self, left: int, right: int) -> bool:
        left_root, right_root = self.find(left), self.find(right)
        if left_root == right_root:
            return False
        if left_root < right_root:
            self.parent[right_root] = left_root
        else:
            self.parent[left_root] = right_root
        return True


def _percentile(sorted_values: Sequence[int], ratio: float) -> int:
    if not sorted_values:
        return 0
    index = int(round((len(sorted_values) - 1) * ratio))
    return int(sorted_values[index])


def _median(values: Sequence[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return int(ordered[middle])
    return int(round((ordered[middle - 1] + ordered[middle]) / 2.0))


def golden_record(normalized: Sequence[dict], members: Sequence[int], agency_ids: Sequence[int]) -> dict:
    """簇内聚合出 golden record。"""
    areas = [float(normalized[i]["area_num"]) for i in members if normalized[i].get("area_num") is not None]
    prices = [int(normalized[i]["price_num"]) for i in members if normalized[i].get("price_num")]
    area_counter = Counter(round(value, 1) for value in areas)
    if area_counter:
        area_mode = sorted(area_counter.items(), key=lambda item: (-item[1], item[0]))[0][0]
    else:
        area_mode = 0.0
    ordered_prices = sorted(prices)
    median_price = _median(prices)
    p10 = _percentile(ordered_prices, 0.10)
    p90 = _percentile(ordered_prices, 0.90)
    communities = Counter(normalized[i].get("community_norm") or "" for i in members)
    layouts = Counter(normalized[i].get("layout_norm") or "" for i in members)
    return {
        "community": sorted(communities.items(), key=lambda item: (-item[1], item[0]))[0][0] if communities else "",
        "layout": sorted(layouts.items(), key=lambda item: (-item[1], item[0]))[0][0] if layouts else "",
        "area_mode": round(float(area_mode), 2),
        "area_min": round(min(areas), 2) if areas else 0.0,
        "area_max": round(max(areas), 2) if areas else 0.0,
        "price_median": median_price,
        "price_min": min(prices) if prices else 0,
        "price_max": max(prices) if prices else 0,
        "price_p10": p10,
        "price_p90": p90,
        "spread": p90 - p10,
        "dispersion": round((p90 - p10) / median_price, 4) if median_price else 0.0,
        "agency_count": len(set(agency_ids[i] for i in members)),
        "member_count": len(members),
    }


def resolve(
    normalized: Sequence[dict],
    agency_ids: Sequence[int],
    threshold: float = SIMILARITY_THRESHOLD,
) -> dict:
    """跑完整算法 A：返回簇、边、指标。"""
    pairs = candidate_pairs(normalized)
    union_find = UnionFind(len(normalized))
    edges: list[dict] = []
    linked = 0
    for left, right in pairs:
        detail = similarity(normalized[left], normalized[right])
        if detail["score"] >= threshold:
            linked += 1
            union_find.union(left, right)
            edges.append({"left": left, "right": right, **detail})

    groups: dict[int, list[int]] = {}
    for index in range(len(normalized)):
        groups.setdefault(union_find.find(index), []).append(index)

    clusters: list[dict] = []
    for members in sorted(groups.values(), key=lambda item: min(item)):
        member_set = set(members)
        member_scores = [edge["score"] for edge in edges if edge["left"] in member_set and edge["right"] in member_set]
        confidence = max(member_scores) if member_scores else 1.0
        clusters.append(
            {
                "members": members,
                "confidence": round(confidence, 4),
                "golden": golden_record(normalized, members, agency_ids),
            }
        )

    multi = [cluster for cluster in clusters if len(cluster["members"]) > 1]
    metrics = {
        "listings": len(normalized),
        "clusters": len(clusters),
        "multi_clusters": len(multi),
        "pairs_scored": len(pairs),
        "pairs_linked": linked,
        "threshold": threshold,
        "dedup_rate": round(1 - len(clusters) / len(normalized), 4) if normalized else 0.0,
    }
    return {"clusters": clusters, "edges": edges, "metrics": metrics}

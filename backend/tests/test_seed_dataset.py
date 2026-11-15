"""业务验收：seed 数据集经算法 A/B 之后的口径必须与 batch-plan 一致。"""
from __future__ import annotations

from collections import Counter

from scripts.demo_config import AGENCIES, build_listings
from src.services import entity_resolution, normalizer, risk_rules


def _resolve():
    clusters, listings = build_listings()
    true_cluster = {}
    for cluster in clusters:
        for member in cluster["members"]:
            true_cluster[member["lid"]] = cluster["index"]
    norms = [normalizer.normalize_listing(row) for row in listings]
    agency_ids = [AGENCIES.index(next(a for a in AGENCIES if a["code"] == row["agency_code"])) for row in listings]
    return clusters, listings, norms, entity_resolution.resolve(norms, agency_ids), true_cluster


def test_dataset_shape():
    _clusters, listings, _norms, _result, _truth = _resolve()
    assert len(listings) == 540
    assert sorted(Counter(row["agency_code"] for row in listings).values()) == [60] * 9


def test_seed_dataset_clusters():
    _clusters, listings, _norms, result, truth = _resolve()
    assert result["metrics"]["listings"] == 540
    assert result["metrics"]["clusters"] == 386
    assert result["metrics"]["multi_clusters"] == 41
    # 每个预测簇都只含同一套真值房源（没有过度合并）
    for cluster in result["clusters"]:
        assert len({truth[listings[index]["lid"]] for index in cluster["members"]}) == 1
    # 真值簇数量与预测一致（没有漏并）
    assert len({truth[row["lid"]] for row in listings}) == 386


def test_special_cluster_cross_agency():
    _clusters, _listings, _norms, result, _truth = _resolve()
    matched = [
        cluster
        for cluster in result["clusters"]
        if cluster["golden"]["layout"] == "3-2-1" and abs(cluster["golden"]["area_mode"] - 89.5) < 1e-9
    ]
    assert matched, "应有 89.5㎡ 的 3-2-1 簇"
    golden = matched[0]["golden"]
    assert golden["community"] == "翠湖名邸"
    assert golden["member_count"] == 4
    assert golden["agency_count"] == 4
    assert golden["spread"] == 120_000
    assert golden["price_median"] == 6_040_000


def test_seed_dataset_risk_profile():
    clusters, listings, norms, result, _truth = _resolve()
    risky = []
    baits = stales = 0
    for cluster in result["clusters"]:
        members = [
            {
                "id": index,
                "lid": listings[index]["lid"],
                "price_num": norms[index]["price_num"],
                "listed_days": listings[index]["listed_days"],
                "views": listings[index]["views"],
                "status": listings[index]["status"],
            }
            for index in cluster["members"]
        ]
        risk = risk_rules.scan_cluster(members, cluster["golden"])
        if risk["risk_level"] in {"high", "medium"}:
            risky.append(risk)
        baits += len(risk["risk_detail"]["bait_lids"])
        stales += len(risk["risk_detail"]["stale_lids"])
    assert len(risky) == 6, len(risky)
    assert sum(1 for risk in risky if "bait" in risk["risk_tags"]) == 1
    assert baits == 2
    assert stales == 5
    assert max(risk["risk_score"] for risk in risky) == 65

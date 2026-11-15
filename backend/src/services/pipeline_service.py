"""归并流水线：归一（②）→ 实体解析（③④）→ 风险识别（⑤）→ 落库。

纯后端计算，确定性；同一批原始挂牌两次执行得到完全相同的簇集合与 golden record。
"""
from __future__ import annotations

import hashlib
import time

from sqlalchemy import func, select

from src.constants.limits import SIMILARITY_THRESHOLD
from src.models.agency import Agency
from src.models.listing import Listing
from src.models.match_run import MatchRun
from src.models.property import Property
from src.models.review import Review
from src.services import entity_resolution, normalizer, risk_rules
from src.utils.timeutil import iso_utc, utcnow

LISTING_FIELDS = (
    "community_raw",
    "layout_raw",
    "area_raw",
    "price_raw",
    "floor_raw",
    "orientation_raw",
    "title",
)


def cluster_key_of(agency_code: str, lid: str) -> str:
    return f"{agency_code}:{lid}"


def _apply_normalized(listing: Listing, norm: dict) -> None:
    listing.community_norm = norm["community_norm"]
    listing.layout_norm = norm["layout_norm"]
    listing.area_num = norm["area_num"]
    listing.price_num = norm["price_num"]
    listing.floor_num = norm["floor_num"]
    listing.floor_total = norm["floor_total"]
    listing.floor_band = norm["floor_band"]
    listing.orientation_norm = norm["orientation_norm"]
    listing.title_tokens = norm["title_tokens"]
    listing.parse_flags = norm["parse_flags"]


def run_pipeline(db, run: MatchRun, threshold: float = SIMILARITY_THRESHOLD) -> dict:
    started = time.perf_counter()
    listings = list(db.scalars(select(Listing).order_by(Listing.id)).all())
    agencies = {agency.id: agency for agency in db.scalars(select(Agency)).all()}
    if not listings:
        return {
            "metrics": {"listings": 0, "clusters": 0, "multi_clusters": 0, "pairs_scored": 0, "pairs_linked": 0},
            "log": "没有可归并的挂牌：请先采集入库。",
            "status": "partial",
        }

    raw_rows = [{field: getattr(listing, field) for field in LISTING_FIELDS} for listing in listings]
    normalized = [normalizer.normalize_listing(raw) for raw in raw_rows]
    for listing, norm in zip(listings, normalized, strict=True):
        _apply_normalized(listing, norm)

    agency_ids = [listing.agency_id for listing in listings]
    result = entity_resolution.resolve(normalized, agency_ids, threshold=threshold)

    existing = {prop.cluster_key: prop for prop in db.scalars(select(Property)).all()}
    seen_keys: set[str] = set()
    baits = stales = risk_high = risk_medium = 0

    for cluster in result["clusters"]:
        members = cluster["members"]
        member_lids = sorted(
            cluster_key_of(agencies[listings[index].agency_id].code, listings[index].lid) for index in members
        )
        key = hashlib.sha256("|".join(member_lids).encode("utf-8")).hexdigest()[:40]
        seen_keys.add(key)
        golden = cluster["golden"]
        member_rows = [
            {
                "id": listings[index].id,
                "lid": listings[index].lid,
                "price_num": normalized[index]["price_num"],
                "listed_days": listings[index].listed_days,
                "views": listings[index].views,
                "status": listings[index].status,
            }
            for index in members
        ]
        risk = risk_rules.scan_cluster(member_rows, golden)

        prop = existing.get(key)
        if prop is None:
            prop = Property(cluster_key=key)
            db.add(prop)
        prop.community = golden["community"]
        prop.layout = golden["layout"]
        prop.area_mode = golden["area_mode"]
        prop.area_min = golden["area_min"]
        prop.area_max = golden["area_max"]
        prop.price_median = golden["price_median"]
        prop.price_min = golden["price_min"]
        prop.price_max = golden["price_max"]
        prop.price_p10 = golden["price_p10"]
        prop.price_p90 = golden["price_p90"]
        prop.spread = golden["spread"]
        prop.dispersion = golden["dispersion"]
        prop.agency_count = golden["agency_count"]
        prop.member_count = golden["member_count"]
        prop.confidence = cluster["confidence"]
        prop.risk_score = risk["risk_score"]
        prop.risk_level = risk["risk_level"]
        prop.risk_tags = risk["risk_tags"]
        prop.risk_detail = risk["risk_detail"]
        prop.run_id = run.id
        prop.updated_at = utcnow()
        db.flush()

        bait_lids = set(risk["risk_detail"]["bait_lids"])
        stale_lids = set(risk["risk_detail"]["stale_lids"])
        for index in members:
            listing = listings[index]
            tags: list[str] = []
            if listing.lid in bait_lids:
                tags.append("bait")
            if listing.lid in stale_lids:
                tags.append("stale")
            listing.property_id = prop.id
            listing.risk_tags = tags
        baits += len(bait_lids)
        stales += len(stale_lids)
        if prop.risk_level == "high":
            risk_high += 1
        elif prop.risk_level == "medium":
            risk_medium += 1

    pruned = _prune_orphans(db, seen_keys)

    metrics = dict(result["metrics"])
    metrics.update(
        {
            "baits": baits,
            "stales": stales,
            "risk_high": risk_high,
            "risk_medium": risk_medium,
            "risk_total": risk_high + risk_medium,
            "pruned_clusters": pruned,
            "duration_ms": int((time.perf_counter() - started) * 1000),
        }
    )
    log_lines = [
        f"输入挂牌 {metrics['listings']} 条，面积归一失败 {sum(1 for n in normalized if n['area_num'] is None)} 条",
        f"blocking 候选对 {metrics['pairs_scored']} 组，阈值 {threshold:.2f} 连边 {metrics['pairs_linked']} 条",
        f"并查集 + 传递闭包得到 {metrics['clusters']} 个簇，其中多成员簇 {metrics['multi_clusters']} 个，去重率 {metrics['dedup_rate']:.2%}",
        f"算法 B：钓鱼价 {baits} 条、僵尸挂牌 {stales} 条，高风险簇 {risk_high} 个、中风险簇 {risk_medium} 个",
        f"淘汰旧簇 {pruned} 个；耗时 {metrics['duration_ms']} ms",
    ]
    return {"metrics": metrics, "log": "\n".join(log_lines), "status": "success"}


def _prune_orphans(db, seen_keys: set[str]) -> int:
    """删掉本次重算不再产生、且没有复核单的旧簇（有复核单的保留，避免丢历史结论）。"""
    removed = 0
    for prop in db.scalars(select(Property)).all():
        if prop.cluster_key in seen_keys:
            continue
        reviews = db.scalar(select(func.count()).select_from(Review).where(Review.property_id == prop.id)) or 0
        if reviews:
            continue
        for listing in db.scalars(select(Listing).where(Listing.property_id == prop.id)).all():
            listing.property_id = None
        db.delete(prop)
        removed += 1
    db.flush()
    return removed


def last_run_stamp(db) -> str | None:
    run = db.scalar(select(MatchRun).order_by(MatchRun.id.desc()).limit(1))
    return iso_utc(run.finished_at) if run else None

"""总览：挂牌数 / 簇数 / 去重率 / 风险数 + 中介覆盖 + 趋势 + worker 心跳。"""
from __future__ import annotations

from collections import Counter
from datetime import timedelta
from statistics import median

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.constants.enums import (
    RISK_LEVEL_LABELS,
    RISK_LEVEL_ORDER,
    RISK_TAG_LABELS,
    RISK_TAG_ORDER,
    RUN_STATUS_LABELS,
)
from src.models.agency import Agency
from src.models.listing import Listing
from src.models.match_run import MatchRun
from src.models.property import Property
from src.models.review import Review
from src.utils.timeutil import local_now, utcnow


def worker_alive() -> bool:
    try:
        import time

        import redis

        client = redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
        value = client.get(f"{settings.app_name}:worker:heartbeat")
        return bool(value) and (time.time() - float(value)) < 120
    except Exception:
        return False


def _unit_price_median(properties: list[Property]) -> int:
    values = [
        prop.price_median / prop.area_mode
        for prop in properties
        if prop.area_mode and prop.price_median and prop.area_mode > 0
    ]
    return int(round(median(values))) if values else 0


def overview(db: Session) -> dict:
    listing_total = db.scalar(select(func.count()).select_from(Listing)) or 0
    cluster_total = db.scalar(select(func.count()).select_from(Property)) or 0
    multi_total = db.scalar(select(func.count()).select_from(Property).where(Property.member_count > 1)) or 0
    risk_total = (
        db.scalar(
            select(func.count())
            .select_from(Property)
            .where(Property.risk_level.in_(["high", "medium"]))
        )
        or 0
    )
    agency_total = db.scalar(select(func.count()).select_from(Agency)) or 0
    pending_total = db.scalar(select(func.count()).select_from(Review).where(Review.status == "pending")) or 0
    properties = list(db.scalars(select(Property)).all())

    level_rows = db.execute(select(Property.risk_level, func.count()).group_by(Property.risk_level)).all()
    level_counts = {key: count for key, count in level_rows}
    tag_counter: Counter[str] = Counter()
    for prop in properties:
        for tag in prop.risk_tags or []:
            tag_counter[tag] += 1

    agency_rows = db.execute(
        select(Agency.code, Agency.name, Agency.kind, func.count(Listing.id))
        .join(Listing, Listing.agency_id == Agency.id, isouter=True)
        .group_by(Agency.code, Agency.name, Agency.kind, Agency.id)
        .order_by(Agency.id)
    ).all()

    latest_run = db.scalar(select(MatchRun).order_by(MatchRun.id.desc()).limit(1))
    since = utcnow() - timedelta(days=7)
    recent_runs = list(db.scalars(select(MatchRun).where(MatchRun.started_at >= since)).all())
    today = local_now().date()
    trend = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        count = sum(
            1
            for run in recent_runs
            if run.started_at
            and (run.started_at + timedelta(minutes=settings.app_timezone_offset_minutes)).date() == day
        )
        trend.append({"date": day.isoformat(), "runs": count})

    return {
        "listing_total": listing_total,
        "cluster_total": cluster_total,
        "multi_cluster_total": multi_total,
        "dedup_rate": round(1 - cluster_total / listing_total, 4) if listing_total else 0.0,
        "risk_total": risk_total,
        "pending_total": pending_total,
        "agency_total": agency_total,
        "unit_price_median": _unit_price_median(properties),
        "worker_alive": worker_alive(),
        "risk_levels": [
            {
                "key": key,
                "label": RISK_LEVEL_LABELS.get(key, key),
                "count": level_counts.get(key, 0),
            }
            for key in RISK_LEVEL_ORDER
            if level_counts.get(key)
        ],
        "risk_tags": [
            {"key": tag, "label": RISK_TAG_LABELS.get(tag, tag), "count": tag_counter.get(tag, 0)}
            for tag in RISK_TAG_ORDER
            if tag_counter.get(tag)
        ],
        "agencies": [
            {"code": code, "name": name, "kind": kind, "listing_count": count}
            for code, name, kind, count in agency_rows
        ],
        "latest_run": {
            "id": latest_run.id,
            "run_no": latest_run.run_no,
            "status": latest_run.status,
            "status_label": RUN_STATUS_LABELS.get(latest_run.status, latest_run.status),
            "cluster_count": latest_run.cluster_count,
            "multi_count": latest_run.multi_count,
            "dedup_rate": latest_run.dedup_rate,
            "risk_count": latest_run.risk_count,
            "threshold": latest_run.threshold,
            "finished_at": latest_run.finished_at.isoformat(timespec="seconds") + "Z"
            if latest_run.finished_at
            else None,
        }
        if latest_run
        else None,
        "trend": trend,
    }

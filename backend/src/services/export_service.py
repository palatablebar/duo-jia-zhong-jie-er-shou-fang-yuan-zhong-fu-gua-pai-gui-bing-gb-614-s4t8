"""导出服务：归并簇 / 挂牌明细 / 复核单 CSV（含两个算法的结果列）。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.constants.enums import (
    LISTING_STATUS_LABELS,
    REVIEW_REASON_LABELS,
    REVIEW_STATUS_LABELS,
    RISK_LEVEL_LABELS,
    RISK_TAG_LABELS,
)
from src.models.agency import Agency
from src.models.listing import Listing
from src.models.property import Property
from src.models.review import Review
from src.utils.csv_export import to_csv
from src.utils.timeutil import local_stamp


def _tags(tags: list[str] | None) -> str:
    return " / ".join(RISK_TAG_LABELS.get(tag, tag) for tag in (tags or []))


def clusters_csv(db: Session) -> bytes:
    props = db.scalars(select(Property).order_by(Property.risk_score.desc(), Property.id)).all()
    headers = [
        "簇编号",
        "小区",
        "户型",
        "面积众数(㎡)",
        "价格中位(元)",
        "簇置信",
        "成员挂牌数",
        "中介数",
        "价格极差(万元)",
        "离散度",
        "风险分",
        "风险等级",
        "风险标签",
        "钓鱼价挂牌",
        "僵尸挂牌",
        "更新时间",
    ]
    rows = []
    for prop in props:
        detail = prop.risk_detail or {}
        rows.append(
            [
                prop.id,
                prop.community,
                prop.layout,
                f"{prop.area_mode:g}",
                prop.price_median,
                f"{prop.confidence:.3f}",
                prop.member_count,
                prop.agency_count,
                f"{prop.spread / 10000:.1f}",
                f"{prop.dispersion:.4f}",
                prop.risk_score,
                RISK_LEVEL_LABELS.get(prop.risk_level, prop.risk_level),
                _tags(prop.risk_tags),
                " / ".join(detail.get("bait_lids") or []) or "-",
                " / ".join(detail.get("stale_lids") or []) or "-",
                local_stamp(prop.updated_at),
            ]
        )
    return to_csv(headers, rows)


def listings_csv(db: Session, agency_id: int | None = None) -> bytes:
    stmt = select(Listing)
    if agency_id:
        stmt = stmt.where(Listing.agency_id == agency_id)
    listings = db.scalars(stmt.order_by(Listing.id)).all()
    agencies = {agency.id: agency for agency in db.scalars(select(Agency)).all()}
    props = {prop.id: prop for prop in db.scalars(select(Property)).all()}
    headers = [
        "挂牌编号",
        "中介",
        "小区(原文)",
        "小区(归一)",
        "面积(原文)",
        "面积(㎡)",
        "价格(原文)",
        "价格(元)",
        "楼层(原文)",
        "楼层",
        "朝向(归一)",
        "户型(归一)",
        "状态",
        "挂牌天数",
        "带看次数",
        "所属簇",
        "簇风险分",
        "风险标签",
        "归一标记",
    ]
    rows = []
    for listing in listings:
        prop = props.get(listing.property_id)
        rows.append(
            [
                listing.lid,
                agencies.get(listing.agency_id).name if agencies.get(listing.agency_id) else "",
                listing.community_raw,
                listing.community_norm,
                listing.area_raw,
                f"{listing.area_num:g}" if listing.area_num is not None else "",
                listing.price_raw,
                listing.price_num or "",
                listing.floor_raw,
                listing.floor_num or "",
                listing.orientation_norm,
                listing.layout_norm,
                LISTING_STATUS_LABELS.get(listing.status, listing.status),
                listing.listed_days,
                listing.views,
                prop.id if prop else "",
                prop.risk_score if prop else "",
                _tags(listing.risk_tags),
                " / ".join(listing.parse_flags or []),
            ]
        )
    return to_csv(headers, rows)


def reviews_csv(db: Session, status: str | None = None) -> bytes:
    stmt = select(Review)
    if status:
        stmt = stmt.where(Review.status == status)
    reviews = db.scalars(stmt.order_by(Review.id)).all()
    props = {prop.id: prop for prop in db.scalars(select(Property)).all()}
    headers = ["复核号", "小区", "户型", "风险分", "风险等级", "复核原因", "状态", "复核人", "结论备注", "创建时间"]
    rows = []
    for review in reviews:
        prop = props.get(review.property_id)
        rows.append(
            [
                review.id,
                prop.community if prop else "",
                prop.layout if prop else "",
                review.risk_score,
                RISK_LEVEL_LABELS.get(review.severity, review.severity),
                REVIEW_REASON_LABELS.get(review.reason, review.reason),
                REVIEW_STATUS_LABELS.get(review.status, review.status),
                review.reviewer or "",
                review.note or "",
                local_stamp(review.created_at),
            ]
        )
    return to_csv(headers, rows)

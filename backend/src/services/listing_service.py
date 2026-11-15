"""挂牌明细服务：原文与归一结果同时返回，供「挂牌明细」页面对照。"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.constants.enums import LISTING_STATUS_LABELS, RISK_TAG_LABELS
from src.models.agency import Agency
from src.models.listing import Listing
from src.models.property import Property
from src.utils.errors import not_found
from src.utils.timeutil import iso_utc


def serialize(listing: Listing, agency: Agency | None = None, prop: Property | None = None) -> dict:
    return {
        "id": listing.id,
        "lid": listing.lid,
        "agency_id": listing.agency_id,
        "agency_name": agency.name if agency else "",
        "agency_code": agency.code if agency else "",
        "community_raw": listing.community_raw,
        "layout_raw": listing.layout_raw,
        "area_raw": listing.area_raw,
        "price_raw": listing.price_raw,
        "floor_raw": listing.floor_raw,
        "orientation_raw": listing.orientation_raw,
        "title": listing.title,
        "status": listing.status,
        "status_label": LISTING_STATUS_LABELS.get(listing.status, listing.status),
        "listed_days": listing.listed_days,
        "views": listing.views,
        "captured_at": iso_utc(listing.captured_at),
        "norm": {
            "community": listing.community_norm,
            "layout": listing.layout_norm,
            "area": listing.area_num,
            "price": listing.price_num,
            "floor": listing.floor_num,
            "floor_total": listing.floor_total,
            "floor_band": listing.floor_band,
            "orientation": listing.orientation_norm,
            "title_tokens": listing.title_tokens or [],
        },
        "parse_flags": listing.parse_flags or [],
        "risk_tags": listing.risk_tags or [],
        "risk_labels": [RISK_TAG_LABELS.get(tag, tag) for tag in (listing.risk_tags or [])],
        "property_id": listing.property_id,
        "property_community": prop.community if prop else None,
        "property_layout": prop.layout if prop else None,
        "property_risk_level": prop.risk_level if prop else None,
    }


def _context(db: Session) -> tuple[dict[int, Agency], dict[int, Property]]:
    agencies = {agency.id: agency for agency in db.scalars(select(Agency)).all()}
    props = {prop.id: prop for prop in db.scalars(select(Property)).all()}
    return agencies, props


def list_listings(
    db: Session,
    *,
    q: str | None = None,
    agency_id: int | None = None,
    status: str | None = None,
    risk: str | None = None,
    property_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    stmt = select(Listing)
    count_stmt = select(func.count()).select_from(Listing)
    if q:
        like = f"%{q.strip()}%"
        condition = or_(Listing.community_raw.like(like), Listing.title.like(like), Listing.lid.like(like))
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)
    if agency_id:
        stmt = stmt.where(Listing.agency_id == agency_id)
        count_stmt = count_stmt.where(Listing.agency_id == agency_id)
    if status:
        stmt = stmt.where(Listing.status == status)
        count_stmt = count_stmt.where(Listing.status == status)
    if risk == "bait":
        stmt = stmt.where(Listing.risk_tags.like('%"bait"%'))
        count_stmt = count_stmt.where(Listing.risk_tags.like('%"bait"%'))
    elif risk == "stale":
        stmt = stmt.where(Listing.risk_tags.like('%"stale"%'))
        count_stmt = count_stmt.where(Listing.risk_tags.like('%"stale"%'))
    elif risk == "none":
        stmt = stmt.where(Listing.risk_tags == "[]")
        count_stmt = count_stmt.where(Listing.risk_tags == "[]")
    if property_id:
        stmt = stmt.where(Listing.property_id == property_id)
        count_stmt = count_stmt.where(Listing.property_id == property_id)
    total = db.scalar(count_stmt) or 0
    rows = db.scalars(stmt.order_by(Listing.id).limit(limit).offset(offset)).all()
    agencies, props = _context(db)
    return {
        "items": [serialize(row, agencies.get(row.agency_id), props.get(row.property_id)) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_listing(db: Session, listing_id: int) -> dict:
    listing = db.get(Listing, listing_id)
    if listing is None:
        raise not_found("listing", listing_id)
    agencies, props = _context(db)
    payload = serialize(listing, agencies.get(listing.agency_id), props.get(listing.property_id))
    prop = props.get(listing.property_id)
    payload["cluster"] = (
        {
            "id": prop.id,
            "community": prop.community,
            "layout": prop.layout,
            "member_count": prop.member_count,
            "agency_count": prop.agency_count,
            "price_median": prop.price_median,
            "risk_score": prop.risk_score,
            "risk_level": prop.risk_level,
            "risk_tags": prop.risk_tags or [],
        }
        if prop
        else None
    )
    return payload

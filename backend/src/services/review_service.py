"""复核服务：风险簇复核队列与结论。"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.constants.enums import (
    REVIEW_REASON_LABELS,
    REVIEW_STATUS_LABELS,
    RISK_LEVEL_LABELS,
    RISK_TAG_LABELS,
)
from src.models.property import Property
from src.models.review import Review
from src.utils.errors import not_found
from src.utils.timeutil import iso_utc, utcnow


def serialize(review: Review, prop: Property | None = None) -> dict:
    return {
        "id": review.id,
        "property_id": review.property_id,
        "run_id": review.run_id,
        "reason": review.reason,
        "reason_label": REVIEW_REASON_LABELS.get(review.reason, review.reason),
        "severity": review.severity,
        "severity_label": RISK_LEVEL_LABELS.get(review.severity, review.severity),
        "risk_score": review.risk_score,
        "status": review.status,
        "status_label": REVIEW_STATUS_LABELS.get(review.status, review.status),
        "reviewer": review.reviewer,
        "note": review.note,
        "created_at": iso_utc(review.created_at),
        "updated_at": iso_utc(review.updated_at),
        "property": {
            "id": prop.id,
            "community": prop.community,
            "layout": prop.layout,
            "area_mode": prop.area_mode,
            "price_median": prop.price_median,
            "spread": prop.spread,
            "member_count": prop.member_count,
            "agency_count": prop.agency_count,
            "risk_level": prop.risk_level,
            "risk_tags": prop.risk_tags or [],
            "risk_tag_labels": [RISK_TAG_LABELS.get(tag, tag) for tag in (prop.risk_tags or [])],
        }
        if prop
        else None,
    }


def list_reviews(
    db: Session,
    *,
    status: str | None = None,
    reason: str | None = None,
    severity: str | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    stmt = select(Review).join(Property, Property.id == Review.property_id)
    count_stmt = select(func.count()).select_from(Review)
    if status:
        stmt = stmt.where(Review.status == status)
        count_stmt = count_stmt.where(Review.status == status)
    if reason:
        stmt = stmt.where(Review.reason == reason)
        count_stmt = count_stmt.where(Review.reason == reason)
    if severity:
        stmt = stmt.where(Review.severity == severity)
        count_stmt = count_stmt.where(Review.severity == severity)
    if q:
        like = f"%{q.strip()}%"
        condition = or_(Property.community.like(like), Property.layout.like(like))
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)
    total = db.scalar(count_stmt) or 0
    rows = stmt.order_by(Review.status.asc(), Review.risk_score.desc(), Review.id.asc()).limit(limit).offset(offset)
    props = {prop.id: prop for prop in db.scalars(select(Property)).all()}
    return {
        "items": [serialize(review, props.get(review.property_id)) for review in db.scalars(rows).all()],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_review(db: Session, review_id: int) -> Review:
    review = db.get(Review, review_id)
    if review is None:
        raise not_found("review", review_id)
    return review


def submit(db: Session, review: Review, *, status: str, note: str | None, reviewer_str: str) -> Review:
    review.status = status
    review.note = note
    review.reviewer = reviewer_str
    review.updated_at = utcnow()
    db.flush()
    return review


def ensure_for_property(
    db: Session,
    *,
    prop: Property,
    run_id: int | None,
    seed_key: str,
    preferred_reason: str | None = None,
) -> Review | None:
    """为风险簇补一张复核单（自然键 seed_key，幂等，不覆盖已有复核结论）。"""
    existing = db.scalar(select(Review).where(Review.seed_key == seed_key))
    if existing is not None:
        return existing
    tags = prop.risk_tags or []
    reason = preferred_reason or ("bait" if "bait" in tags else "stale" if "stale" in tags else "spread")
    review = Review(
        property_id=prop.id,
        run_id=run_id,
        reason=reason,
        severity=prop.risk_level,
        risk_score=prop.risk_score,
        status="pending",
        seed_key=seed_key,
    )
    db.add(review)
    db.flush()
    return review

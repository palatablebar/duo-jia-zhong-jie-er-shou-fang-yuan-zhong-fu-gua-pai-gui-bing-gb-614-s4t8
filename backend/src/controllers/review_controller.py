"""复核控制器。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.services import audit_service, review_service
from src.utils.errors import not_found


def list_reviews(db: Session, **filters) -> dict:
    return review_service.list_reviews(db, **filters)


def get_review(db: Session, review_id: int) -> dict:
    from src.models.property import Property

    review = review_service.get_review(db, review_id)
    return review_service.serialize(review, db.get(Property, review.property_id))


def submit(db: Session, review_id: int, payload: dict, principal: dict, request: Request) -> dict:
    from src.models.property import Property

    review = review_service.get_review(db, review_id)
    review_service.submit(db, review, status=payload["status"], note=payload.get("note"), reviewer_str=principal["email"])
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="review.submit",
        entity="review",
        entity_id=review.id,
        detail={"status": review.status, "reason": review.reason, "risk_score": review.risk_score},
        ip=request.client.host if request.client else None,
    )
    db.commit()
    prop = db.get(Property, review.property_id)
    if prop is None:
        raise not_found("property", review.property_id)
    return review_service.serialize(review, prop)

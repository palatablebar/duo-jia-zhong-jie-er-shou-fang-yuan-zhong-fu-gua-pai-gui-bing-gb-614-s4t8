from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import REVIEW_ROLES
from src.controllers import review_controller
from src.middlewares.rbac import READ_ROLES, require_roles
from src.schemas.review import ReviewIn
from src.utils.pagination import page_params

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("")
def list_reviews(
    status: str | None = None,
    reason: str | None = None,
    severity: str | None = None,
    q: str | None = None,
    limit: int = Query(20),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*READ_ROLES)),
) -> dict:
    page = page_params(limit, offset)
    return review_controller.list_reviews(
        db, status=status, reason=reason, severity=severity, q=q, limit=page.limit, offset=page.offset
    )


@router.get("/{review_id}")
def get_review(
    review_id: int, db: Session = Depends(get_db), principal: dict = Depends(require_roles(*READ_ROLES))
) -> dict:
    return review_controller.get_review(db, review_id)


@router.patch("/{review_id}")
def submit_review(
    review_id: int,
    payload: ReviewIn,
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*REVIEW_ROLES)),
) -> dict:
    return review_controller.submit(db, review_id, payload.model_dump(), principal, request)

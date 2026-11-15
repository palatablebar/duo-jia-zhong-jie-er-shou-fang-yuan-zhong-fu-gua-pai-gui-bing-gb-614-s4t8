from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import REVIEW_ROLES
from src.controllers import finding_controller
from src.middlewares.rbac import READ_ROLES, require_roles
from src.schemas.finding import ReviewIn
from src.utils.pagination import page_params

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("")
def list_findings(
    run_id: int | None = None,
    status: str | None = None,
    severity: str | None = None,
    q: str | None = None,
    limit: int = Query(20),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*READ_ROLES)),
) -> dict:
    page = page_params(limit, offset)
    return finding_controller.list_findings(
        db, run_id=run_id, status=status, severity=severity, q=q, limit=page.limit, offset=page.offset
    )


@router.get("/{finding_id}")
def get_finding(
    finding_id: int, db: Session = Depends(get_db), principal: dict = Depends(require_roles(*READ_ROLES))
) -> dict:
    return finding_controller.get_finding(db, finding_id)


@router.patch("/{finding_id}/review")
def review(
    finding_id: int,
    payload: ReviewIn,
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*REVIEW_ROLES)),
) -> dict:
    return finding_controller.review(db, finding_id, payload.model_dump(), principal, request)

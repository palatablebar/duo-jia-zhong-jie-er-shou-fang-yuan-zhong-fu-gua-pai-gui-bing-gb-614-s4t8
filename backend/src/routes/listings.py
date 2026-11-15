from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import listing_controller
from src.middlewares.rbac import READ_ROLES, require_roles
from src.utils.pagination import page_params

router = APIRouter(prefix="/listings", tags=["listings"])


@router.get("")
def list_listings(
    q: str | None = None,
    agency_id: int | None = None,
    status: str | None = None,
    risk: str | None = None,
    property_id: int | None = None,
    limit: int = Query(20),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*READ_ROLES)),
) -> dict:
    page = page_params(limit, offset)
    return listing_controller.list_listings(
        db,
        q=q,
        agency_id=agency_id,
        status=status,
        risk=risk,
        property_id=property_id,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{listing_id}")
def get_listing(
    listing_id: int, db: Session = Depends(get_db), principal: dict = Depends(require_roles(*READ_ROLES))
) -> dict:
    return listing_controller.get_listing(db, listing_id)

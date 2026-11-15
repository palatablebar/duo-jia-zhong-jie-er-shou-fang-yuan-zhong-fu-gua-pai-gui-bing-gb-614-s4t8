from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import EXPORT_ROLES
from src.controllers import export_controller
from src.middlewares.rbac import require_roles

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/clusters.csv")
def clusters_csv(
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*EXPORT_ROLES)),
):
    return export_controller.clusters_csv(db, principal, request)


@router.get("/listings.csv")
def listings_csv(
    request: Request,
    agency_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*EXPORT_ROLES)),
):
    return export_controller.listings_csv(db, agency_id, principal, request)


@router.get("/reviews.csv")
def reviews_csv(
    request: Request,
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*EXPORT_ROLES)),
):
    return export_controller.reviews_csv(db, status, principal, request)

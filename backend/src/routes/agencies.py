from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import AGENCY_WRITE_ROLES
from src.controllers import agency_controller
from src.middlewares.rbac import READ_ROLES, require_roles
from src.schemas.agency import AgencyIn, AgencyPatch
from src.utils.pagination import page_params

router = APIRouter(prefix="/agencies", tags=["agencies"])


@router.get("")
def list_agencies(
    q: str | None = None,
    kind: str | None = None,
    enabled: bool | None = None,
    limit: int = Query(20),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*READ_ROLES)),
) -> dict:
    page = page_params(limit, offset)
    return agency_controller.list_agencies(db, q=q, kind=kind, enabled=enabled, limit=page.limit, offset=page.offset)


@router.get("/{agency_id}")
def get_agency(agency_id: int, db: Session = Depends(get_db), principal: dict = Depends(require_roles(*READ_ROLES))) -> dict:
    return agency_controller.get_agency(db, agency_id)


@router.post("", status_code=201)
def create_agency(
    payload: AgencyIn,
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*AGENCY_WRITE_ROLES)),
) -> dict:
    return agency_controller.create_agency(db, payload.model_dump(), principal, request)


@router.patch("/{agency_id}")
def update_agency(
    agency_id: int,
    payload: AgencyPatch,
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*AGENCY_WRITE_ROLES)),
) -> dict:
    return agency_controller.update_agency(db, agency_id, payload.model_dump(exclude_unset=True), principal, request)

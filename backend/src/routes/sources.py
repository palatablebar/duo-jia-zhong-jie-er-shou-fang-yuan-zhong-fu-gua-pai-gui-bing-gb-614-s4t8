from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.constants.roles import SOURCE_WRITE_ROLES
from src.controllers import source_controller
from src.middlewares.rbac import READ_ROLES, require_roles
from src.schemas.source import SourceIn, SourcePatch
from src.utils.pagination import page_params

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("")
def list_sources(
    q: str | None = None,
    kind: str | None = None,
    enabled: bool | None = None,
    limit: int = Query(20),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*READ_ROLES)),
) -> dict:
    page = page_params(limit, offset)
    return source_controller.list_sources(db, q=q, kind=kind, enabled=enabled, limit=page.limit, offset=page.offset)


@router.get("/{source_id}")
def get_source(source_id: int, db: Session = Depends(get_db), principal: dict = Depends(require_roles(*READ_ROLES))) -> dict:
    return source_controller.get_source(db, source_id)


@router.post("", status_code=201)
def create_source(
    payload: SourceIn,
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*SOURCE_WRITE_ROLES)),
) -> dict:
    return source_controller.create_source(db, payload.model_dump(), principal, request)


@router.patch("/{source_id}")
def update_source(
    source_id: int,
    payload: SourcePatch,
    request: Request,
    db: Session = Depends(get_db),
    principal: dict = Depends(require_roles(*SOURCE_WRITE_ROLES)),
) -> dict:
    return source_controller.update_source(db, source_id, payload.model_dump(exclude_unset=True), principal, request)

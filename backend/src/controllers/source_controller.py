"""数据源控制器：写操作记领域审计。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.services import audit_service, source_service


def list_sources(db: Session, **filters) -> dict:
    return source_service.list_sources(db, **filters)


def get_source(db: Session, source_id: int) -> dict:
    return source_service.serialize(source_service.get_source(db, source_id))


def create_source(db: Session, payload: dict, principal: dict, request: Request) -> dict:
    source = source_service.create_source(db, payload)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="source.create",
        entity="source",
        entity_id=source.id,
        detail={"code": source.code, "name": source.name},
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return source_service.serialize(source)


def update_source(db: Session, source_id: int, payload: dict, principal: dict, request: Request) -> dict:
    source = source_service.get_source(db, source_id)
    source_service.update_source(db, source, payload)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="source.update",
        entity="source",
        entity_id=source.id,
        detail={"fields": list(payload.keys())},
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return source_service.serialize(source)

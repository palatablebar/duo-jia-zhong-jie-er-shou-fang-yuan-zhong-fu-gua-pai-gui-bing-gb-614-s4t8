"""接入源服务：CRUD + 序列化。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.constants.enums import SOURCE_KIND_LABELS
from src.models.source import Source
from src.utils.errors import AppError, not_found
from src.utils.timeutil import iso_utc


def serialize(source: Source) -> dict:
    return {
        "id": source.id,
        "code": source.code,
        "name": source.name,
        "kind": source.kind,
        "kind_label": SOURCE_KIND_LABELS.get(source.kind, source.kind),
        "endpoint": source.endpoint,
        "owner": source.owner,
        "note": source.note,
        "config": source.config or {},
        "enabled": source.enabled,
        "last_synced_at": iso_utc(source.last_synced_at),
        "created_at": iso_utc(source.created_at),
    }


def list_sources(
    db: Session,
    q: str | None = None,
    kind: str | None = None,
    enabled: bool | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    stmt = select(Source)
    count_stmt = select(func.count()).select_from(Source)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(Source.name.ilike(like) | Source.code.ilike(like))
        count_stmt = count_stmt.where(Source.name.ilike(like) | Source.code.ilike(like))
    if kind:
        stmt = stmt.where(Source.kind == kind)
        count_stmt = count_stmt.where(Source.kind == kind)
    if enabled is not None:
        stmt = stmt.where(Source.enabled == enabled)
        count_stmt = count_stmt.where(Source.enabled == enabled)
    total = db.scalar(count_stmt) or 0
    rows = db.scalars(stmt.order_by(Source.id).limit(limit).offset(offset)).all()
    return {"items": [serialize(row) for row in rows], "total": total, "limit": limit, "offset": offset}


def get_source(db: Session, source_id: int) -> Source:
    source = db.get(Source, source_id)
    if source is None:
        raise not_found("source", source_id)
    return source


def create_source(db: Session, payload: dict) -> Source:
    exists = db.scalar(select(Source).where(Source.code == payload["code"]))
    if exists is not None:
        raise AppError("CONFLICT", 409, {"code": payload["code"]})
    source = Source(
        code=payload["code"],
        name=payload["name"],
        kind=payload.get("kind") or "manual",
        endpoint=payload.get("endpoint"),
        owner=payload.get("owner") or "安家数据 · 房源中台",
        note=payload.get("note"),
        config=payload.get("config") or {},
        enabled=payload.get("enabled", True),
    )
    db.add(source)
    db.flush()
    return source


def update_source(db: Session, source: Source, payload: dict) -> Source:
    for field in ("name", "kind", "endpoint", "owner", "note", "config", "enabled"):
        if field in payload and payload[field] is not None:
            setattr(source, field, payload[field])
    db.flush()
    return source

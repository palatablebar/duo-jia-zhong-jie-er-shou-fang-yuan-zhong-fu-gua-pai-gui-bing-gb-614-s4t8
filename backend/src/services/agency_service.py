"""中介渠道服务：登记、采集统计、启用状态。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.constants.enums import AGENCY_KIND_LABELS
from src.models.agency import Agency
from src.models.listing import Listing
from src.utils.errors import AppError, not_found
from src.utils.timeutil import iso_utc


def serialize(agency: Agency, listing_count: int = 0, last_listing_at=None) -> dict:
    return {
        "id": agency.id,
        "code": agency.code,
        "name": agency.name,
        "kind": agency.kind,
        "kind_label": AGENCY_KIND_LABELS.get(agency.kind, agency.kind),
        "endpoint": agency.endpoint,
        "owner": agency.owner,
        "note": agency.note,
        "config": agency.config or {},
        "enabled": agency.enabled,
        "listing_count": listing_count,
        "last_synced_at": iso_utc(agency.last_synced_at),
        "last_listing_at": iso_utc(last_listing_at),
        "created_at": iso_utc(agency.created_at),
    }


def listing_stats(db: Session) -> dict[int, dict]:
    rows = db.execute(
        select(Listing.agency_id, func.count(Listing.id), func.max(Listing.captured_at)).group_by(Listing.agency_id)
    ).all()
    return {agency_id: {"count": count, "last_at": last_at} for agency_id, count, last_at in rows}


def list_agencies(
    db: Session,
    q: str | None = None,
    kind: str | None = None,
    enabled: bool | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    stmt = select(Agency)
    count_stmt = select(func.count()).select_from(Agency)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(Agency.name.like(like) | Agency.code.like(like))
        count_stmt = count_stmt.where(Agency.name.like(like) | Agency.code.like(like))
    if kind:
        stmt = stmt.where(Agency.kind == kind)
        count_stmt = count_stmt.where(Agency.kind == kind)
    if enabled is not None:
        stmt = stmt.where(Agency.enabled == enabled)
        count_stmt = count_stmt.where(Agency.enabled == enabled)
    total = db.scalar(count_stmt) or 0
    rows = db.scalars(stmt.order_by(Agency.id).limit(limit).offset(offset)).all()
    stats = listing_stats(db)
    return {
        "items": [
            serialize(row, stats.get(row.id, {}).get("count", 0), stats.get(row.id, {}).get("last_at")) for row in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_agency(db: Session, agency_id: int) -> Agency:
    agency = db.get(Agency, agency_id)
    if agency is None:
        raise not_found("agency", agency_id)
    return agency


def create_agency(db: Session, payload: dict) -> Agency:
    if db.scalar(select(Agency).where(Agency.code == payload["code"])) is not None:
        raise AppError("CONFLICT", 409, {"code": payload["code"]})
    agency = Agency(
        code=payload["code"],
        name=payload["name"],
        kind=payload.get("kind") or "broker",
        endpoint=payload.get("endpoint"),
        owner=payload.get("owner") or "安家数据 · 房源中台",
        note=payload.get("note"),
        config=payload.get("config") or {},
        enabled=payload.get("enabled", True),
    )
    db.add(agency)
    db.flush()
    return agency


def update_agency(db: Session, agency: Agency, payload: dict) -> Agency:
    for field in ("name", "kind", "endpoint", "owner", "note", "config", "enabled"):
        if field in payload and payload[field] is not None:
            setattr(agency, field, payload[field])
    db.flush()
    return agency

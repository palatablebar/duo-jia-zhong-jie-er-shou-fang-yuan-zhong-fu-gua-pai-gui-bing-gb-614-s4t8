"""挂牌明细控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.services import listing_service


def list_listings(db: Session, **filters) -> dict:
    return listing_service.list_listings(db, **filters)


def get_listing(db: Session, listing_id: int) -> dict:
    return listing_service.get_listing(db, listing_id)

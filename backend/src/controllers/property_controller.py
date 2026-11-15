"""归并簇控制器。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.services import property_service


def list_properties(db: Session, **filters) -> dict:
    return property_service.list_properties(db, **filters)


def get_property(db: Session, property_id: int) -> dict:
    return property_service.get_property(db, property_id)

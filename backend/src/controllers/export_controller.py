"""导出控制器：CSV 响应 + 审计。"""
from __future__ import annotations

from fastapi import Request, Response
from sqlalchemy.orm import Session

from src.services import audit_service, export_service
from src.utils.csv_export import csv_response_headers


def clusters_csv(db: Session, principal: dict, request: Request) -> Response:
    content = export_service.clusters_csv(db)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="export.clusters",
        entity="property",
        entity_id=None,
        detail={"bytes": len(content)},
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return Response(content=content, media_type="text/csv; charset=utf-8", headers=csv_response_headers("clusters.csv"))


def listings_csv(db: Session, agency_id: int | None, principal: dict, request: Request) -> Response:
    content = export_service.listings_csv(db, agency_id)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="export.listings",
        entity="listing",
        entity_id=agency_id,
        detail={"bytes": len(content)},
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return Response(content=content, media_type="text/csv; charset=utf-8", headers=csv_response_headers("listings.csv"))


def reviews_csv(db: Session, status: str | None, principal: dict, request: Request) -> Response:
    content = export_service.reviews_csv(db, status)
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="export.clusters",
        entity="review",
        entity_id=None,
        detail={"bytes": len(content), "kind": "reviews"},
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return Response(content=content, media_type="text/csv; charset=utf-8", headers=csv_response_headers("reviews.csv"))

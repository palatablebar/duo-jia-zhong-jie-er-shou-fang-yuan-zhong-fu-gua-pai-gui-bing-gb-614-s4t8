"""结果控制器。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.services import audit_service, finding_service


def list_findings(db: Session, **filters) -> dict:
    return finding_service.list_findings(db, **filters)


def get_finding(db: Session, finding_id: int) -> dict:
    return finding_service.serialize(finding_service.get_finding(db, finding_id))


def review(db: Session, finding_id: int, payload: dict, principal: dict, request: Request) -> dict:
    finding = finding_service.get_finding(db, finding_id)
    finding_service.review(
        db,
        finding,
        status=payload["status"],
        note=payload.get("note"),
        reviewer=principal["email"],
    )
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="finding.review",
        entity="finding",
        entity_id=finding.id,
        detail={"status": finding.status, "score": finding.score},
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return finding_service.serialize(finding)

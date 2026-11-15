"""归并重算控制器。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.services import audit_service, match_run_service


def create_run(db: Session, payload: dict, principal: dict, request: Request) -> dict:
    run = match_run_service.create_and_execute(
        db,
        trigger=payload.get("trigger") or "manual",
        operator_email=principal["email"],
        threshold=float(payload.get("threshold") or 0.80),
    )
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="run.create",
        entity="match_run",
        entity_id=run.id,
        detail={"run_no": run.run_no, "threshold": run.threshold, "status": run.status},
        ip=request.client.host if request.client else None,
    )
    audit_service.record(
        db,
        actor_email=principal["email"],
        actor_role=principal["role"],
        action="run.complete",
        entity="match_run",
        entity_id=run.id,
        detail={
            "clusters": run.cluster_count,
            "multi": run.multi_count,
            "dedup_rate": run.dedup_rate,
            "risk": run.risk_count,
        },
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return match_run_service.serialize(run)


def list_runs(db: Session, **filters) -> dict:
    return match_run_service.list_runs(db, **filters)


def get_run(db: Session, run_id: int) -> dict:
    return match_run_service.serialize(match_run_service.get_run(db, run_id))

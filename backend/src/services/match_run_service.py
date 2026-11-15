"""归并重算服务：创建运行 → 执行流水线 → 汇总指标。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.constants.enums import TRIGGER_LABELS, RunStatus
from src.constants.limits import SIMILARITY_THRESHOLD
from src.models.agency import Agency
from src.models.match_run import MatchRun
from src.services import pipeline_service
from src.utils.errors import AppError
from src.utils.timeutil import iso_utc, local_now, utcnow


def serialize(run: MatchRun) -> dict:
    return {
        "id": run.id,
        "run_no": run.run_no,
        "trigger": run.trigger,
        "trigger_label": TRIGGER_LABELS.get(run.trigger, run.trigger),
        "status": run.status,
        "operator_email": run.operator_email,
        "listing_count": run.listing_count,
        "cluster_count": run.cluster_count,
        "multi_count": run.multi_count,
        "dedup_rate": run.dedup_rate,
        "risk_count": run.risk_count,
        "threshold": run.threshold,
        "metrics": run.metrics or {},
        "log_text": run.log_text,
        "started_at": iso_utc(run.started_at),
        "finished_at": iso_utc(run.finished_at),
    }


def next_run_no(db: Session) -> str:
    prefix = f"R{local_now():%Y%m%d}"
    count = db.scalar(select(func.count()).select_from(MatchRun).where(MatchRun.run_no.like(f"{prefix}%"))) or 0
    return f"{prefix}-{count + 1:04d}"


def execute(db: Session, run: MatchRun, threshold: float) -> MatchRun:
    run.status = RunStatus.RUNNING.value
    run.threshold = threshold
    try:
        result = pipeline_service.run_pipeline(db, run, threshold=threshold)
        metrics = result.get("metrics") or {}
        run.metrics = metrics
        run.log_text = result.get("log") or ""
        run.status = result.get("status") or RunStatus.SUCCESS.value
        run.listing_count = int(metrics.get("listings") or 0)
        run.cluster_count = int(metrics.get("clusters") or 0)
        run.multi_count = int(metrics.get("multi_clusters") or 0)
        run.dedup_rate = float(metrics.get("dedup_rate") or 0.0)
        run.risk_count = int(metrics.get("risk_total") or 0)
        for agency in db.scalars(select(Agency)).all():
            agency.last_synced_at = utcnow()
    except Exception as exc:  # noqa: BLE001 - 运行失败要留痕，不抛 500
        run.status = RunStatus.FAILED.value
        run.log_text = f"归并失败：{exc}"
        run.metrics = {"error": str(exc)[:300]}
    run.finished_at = utcnow()
    db.flush()
    return run


def create_and_execute(
    db: Session,
    *,
    trigger: str,
    operator_email: str,
    threshold: float = SIMILARITY_THRESHOLD,
    seed_key: str | None = None,
) -> MatchRun:
    if seed_key:
        existing = db.scalar(select(MatchRun).where(MatchRun.seed_key == seed_key))
        if existing is not None:
            return existing
    if not (0.5 <= threshold <= 1.0):
        raise AppError("VALIDATION", 422, {"threshold": threshold, "range": [0.5, 1.0]})
    run = MatchRun(
        run_no=next_run_no(db),
        trigger=trigger,
        status=RunStatus.RUNNING.value,
        operator_email=operator_email,
        threshold=threshold,
        seed_key=seed_key,
    )
    db.add(run)
    db.flush()
    return execute(db, run, threshold)


def list_runs(db: Session, status: str | None, limit: int, offset: int) -> dict:
    stmt = select(MatchRun)
    count_stmt = select(func.count()).select_from(MatchRun)
    if status:
        stmt = stmt.where(MatchRun.status == status)
        count_stmt = count_stmt.where(MatchRun.status == status)
    total = db.scalar(count_stmt) or 0
    rows = db.scalars(stmt.order_by(MatchRun.id.desc()).limit(limit).offset(offset)).all()
    return {"items": [serialize(row) for row in rows], "total": total, "limit": limit, "offset": offset}


def get_run(db: Session, run_id: int) -> MatchRun:
    run = db.get(MatchRun, run_id)
    if run is None:
        raise AppError("NOT_FOUND", 404, {"entity": "run", "id": run_id})
    return run


def latest(db: Session) -> MatchRun | None:
    return db.scalar(select(MatchRun).order_by(MatchRun.id.desc()).limit(1))

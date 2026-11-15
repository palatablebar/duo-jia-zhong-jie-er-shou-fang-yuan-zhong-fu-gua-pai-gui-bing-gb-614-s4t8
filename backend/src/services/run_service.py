"""运行服务：创建运行、执行算法、写入结果、更新统计。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.models.finding import Finding
from src.models.run import Run
from src.models.source import Source
from src.services import pipeline_service
from src.utils.errors import AppError
from src.utils.timeutil import iso_utc, local_now, utcnow


def serialize(run: Run, source_name: str | None = None) -> dict:
    return {
        "id": run.id,
        "run_no": run.run_no,
        "source_id": run.source_id,
        "source_name": source_name,
        "trigger": run.trigger,
        "status": run.status,
        "operator_email": run.operator_email,
        "input_count": run.input_count,
        "output_count": run.output_count,
        "metrics": run.metrics or {},
        "log_text": run.log_text,
        "started_at": iso_utc(run.started_at),
        "finished_at": iso_utc(run.finished_at),
    }


def next_run_no(db: Session) -> str:
    prefix = f"R{local_now():%Y%m%d}"
    count = db.scalar(select(func.count()).select_from(Run).where(Run.run_no.like(f"{prefix}%"))) or 0
    return f"{prefix}-{count + 1:04d}"


def _upsert_findings(db: Session, run: Run, findings: list[dict]) -> None:
    for item in findings:
        existing = db.scalar(select(Finding).where(Finding.run_id == run.id, Finding.key == item["key"]))
        if existing is None:
            db.add(
                Finding(
                    run_id=run.id,
                    source_id=run.source_id,
                    key=item["key"],
                    title=item["title"][:200],
                    summary=item.get("summary") or "",
                    severity=item.get("severity") or "medium",
                    score=float(item.get("score") or 0.0),
                    payload=item.get("payload") or {},
                )
            )
        else:
            existing.title = item["title"][:200]
            existing.summary = item.get("summary") or ""
            existing.severity = item.get("severity") or "medium"
            existing.score = float(item.get("score") or 0.0)
            existing.payload = item.get("payload") or {}


def execute_run(db: Session, run: Run, source: Source | None) -> Run:
    run.status = "running"
    try:
        result = pipeline_service.run_pipeline(db, run, source)
        _upsert_findings(db, run, result["findings"])
        run.metrics = result.get("metrics") or {}
        run.log_text = result.get("log") or ""
        run.status = result.get("status") or "success"
        run.output_count = len(result["findings"])
        run.input_count = int((result.get("metrics") or {}).get("rows") or 0)
        if source is not None:
            source.last_synced_at = utcnow()
    except Exception as exc:  # noqa: BLE001 - 运行失败要留痕，不抛出 500
        run.status = "failed"
        run.log_text = f"运行失败：{exc}"
        run.metrics = {"error": str(exc)[:300]}
    run.finished_at = utcnow()
    db.flush()
    return run


def create_and_execute(
    db: Session,
    *,
    source_id: int | None,
    trigger: str,
    operator_email: str,
    seed_key: str | None = None,
) -> Run:
    if seed_key:
        existing = db.scalar(select(Run).where(Run.seed_key == seed_key))
        if existing is not None:
            return existing
    source = db.get(Source, source_id) if source_id else None
    if source_id and source is None:
        raise AppError("NOT_FOUND", 404, {"entity": "source", "id": source_id})
    run = Run(
        run_no=next_run_no(db),
        source_id=source_id,
        trigger=trigger,
        status="running",
        operator_email=operator_email,
        seed_key=seed_key,
    )
    db.add(run)
    db.flush()
    return execute_run(db, run, source)


def list_runs(db: Session, source_id: int | None, status: str | None, limit: int, offset: int) -> dict:
    stmt = select(Run)
    count_stmt = select(func.count()).select_from(Run)
    if source_id:
        stmt = stmt.where(Run.source_id == source_id)
        count_stmt = count_stmt.where(Run.source_id == source_id)
    if status:
        stmt = stmt.where(Run.status == status)
        count_stmt = count_stmt.where(Run.status == status)
    total = db.scalar(count_stmt) or 0
    rows = db.scalars(stmt.order_by(Run.id.desc()).limit(limit).offset(offset)).all()
    source_names = {
        source.id: source.name for source in db.scalars(select(Source)).all()
    }
    return {
        "items": [serialize(row, source_names.get(row.source_id)) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_run(db: Session, run_id: int) -> Run:
    run = db.get(Run, run_id)
    if run is None:
        raise AppError("NOT_FOUND", 404, {"entity": "run", "id": run_id})
    return run


def app_name() -> str:
    return settings.app_name

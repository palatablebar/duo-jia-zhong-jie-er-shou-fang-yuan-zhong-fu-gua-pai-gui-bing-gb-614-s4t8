"""结果服务：列表、详情、复核。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.finding import Finding
from src.models.run import Run
from src.models.source import Source
from src.utils.errors import AppError
from src.utils.timeutil import iso_utc, utcnow


def serialize(finding: Finding, run_no: str | None = None, source_name: str | None = None) -> dict:
    return {
        "id": finding.id,
        "run_id": finding.run_id,
        "run_no": run_no,
        "source_id": finding.source_id,
        "source_name": source_name,
        "key": finding.key,
        "title": finding.title,
        "summary": finding.summary,
        "severity": finding.severity,
        "score": finding.score,
        "status": finding.status,
        "payload": finding.payload or {},
        "reviewer": finding.reviewer,
        "review_note": finding.review_note,
        "created_at": iso_utc(finding.created_at),
        "updated_at": iso_utc(finding.updated_at),
    }


def list_findings(
    db: Session,
    *,
    run_id: int | None = None,
    status: str | None = None,
    severity: str | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    stmt = select(Finding)
    count_stmt = select(func.count()).select_from(Finding)
    if run_id:
        stmt = stmt.where(Finding.run_id == run_id)
        count_stmt = count_stmt.where(Finding.run_id == run_id)
    if status:
        stmt = stmt.where(Finding.status == status)
        count_stmt = count_stmt.where(Finding.status == status)
    if severity:
        stmt = stmt.where(Finding.severity == severity)
        count_stmt = count_stmt.where(Finding.severity == severity)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(Finding.title.ilike(like) | Finding.key.ilike(like))
        count_stmt = count_stmt.where(Finding.title.ilike(like) | Finding.key.ilike(like))
    total = db.scalar(count_stmt) or 0
    rows = db.scalars(stmt.order_by(Finding.id.desc()).limit(limit).offset(offset)).all()
    run_nos = {run.id: run.run_no for run in db.scalars(select(Run)).all()}
    source_names = {source.id: source.name for source in db.scalars(select(Source)).all()}
    return {
        "items": [serialize(row, run_nos.get(row.run_id), source_names.get(row.source_id)) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_finding(db: Session, finding_id: int) -> Finding:
    finding = db.get(Finding, finding_id)
    if finding is None:
        raise AppError("NOT_FOUND", 404, {"entity": "finding", "id": finding_id})
    return finding


def review(db: Session, finding: Finding, *, status: str, note: str | None, reviewer: str) -> Finding:
    finding.status = status
    finding.review_note = note
    finding.reviewer = reviewer
    finding.updated_at = utcnow()
    db.flush()
    return finding

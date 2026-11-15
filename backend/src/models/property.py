"""房源簇（golden record）：同一套房的多次挂牌归并后的主记录。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base
from src.utils.timeutil import utcnow


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cluster_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    community: Mapped[str] = mapped_column(String(160), index=True)
    layout: Mapped[str] = mapped_column(String(40))
    area_mode: Mapped[float] = mapped_column(Float, default=0.0)
    area_min: Mapped[float] = mapped_column(Float, default=0.0)
    area_max: Mapped[float] = mapped_column(Float, default=0.0)
    price_median: Mapped[int] = mapped_column(Integer, default=0)
    price_min: Mapped[int] = mapped_column(Integer, default=0)
    price_max: Mapped[int] = mapped_column(Integer, default=0)
    price_p10: Mapped[int] = mapped_column(Integer, default=0)
    price_p90: Mapped[int] = mapped_column(Integer, default=0)
    spread: Mapped[int] = mapped_column(Integer, default=0)
    dispersion: Mapped[float] = mapped_column(Float, default=0.0)
    agency_count: Mapped[int] = mapped_column(Integer, default=0)
    member_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    risk_level: Mapped[str] = mapped_column(String(10), default="none", index=True)
    risk_tags: Mapped[list] = mapped_column(JSON, default=list)
    risk_detail: Mapped[dict] = mapped_column(JSON, default=dict)
    run_id: Mapped[int | None] = mapped_column(
        ForeignKey("match_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    seeded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

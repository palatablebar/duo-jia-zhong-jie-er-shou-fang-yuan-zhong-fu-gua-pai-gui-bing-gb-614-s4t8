"""一条原始挂牌：保留采集原文，同时存归一结果（归一由 backend 计算）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models import Base
from src.utils.timeutil import utcnow


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (UniqueConstraint("agency_id", "lid", name="uq_listings_agency_lid"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agency_id: Mapped[int] = mapped_column(ForeignKey("agencies.id", ondelete="CASCADE"), index=True)
    lid: Mapped[str] = mapped_column(String(40), index=True)
    community_raw: Mapped[str] = mapped_column(String(160))
    layout_raw: Mapped[str] = mapped_column(String(60))
    area_raw: Mapped[str] = mapped_column(String(60))
    price_raw: Mapped[str] = mapped_column(String(60))
    floor_raw: Mapped[str] = mapped_column(String(60))
    orientation_raw: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    listed_days: Mapped[int] = mapped_column(Integer, default=0)
    views: Mapped[int] = mapped_column(Integer, default=0)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # 归一结果（算法 ②「字段解析归一」写入；重算时整表刷新）
    community_norm: Mapped[str] = mapped_column(String(160), default="", index=True)
    layout_norm: Mapped[str] = mapped_column(String(40), default="")
    area_num: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    price_num: Mapped[int | None] = mapped_column(Integer, nullable=True)
    floor_num: Mapped[int | None] = mapped_column(Integer, nullable=True)
    floor_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    floor_band: Mapped[str] = mapped_column(String(10), default="")
    orientation_norm: Mapped[str] = mapped_column(String(20), default="")
    title_tokens: Mapped[list] = mapped_column(JSON, default=list)
    parse_flags: Mapped[list] = mapped_column(JSON, default=list)

    property_id: Mapped[int | None] = mapped_column(
        ForeignKey("properties.id", ondelete="SET NULL"), nullable=True, index=True
    )
    risk_tags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

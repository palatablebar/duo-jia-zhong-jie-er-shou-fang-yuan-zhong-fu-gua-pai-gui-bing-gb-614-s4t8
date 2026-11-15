"""共享枚举（后端唯一定义处）。前端副本见 frontend/site/js/config.js。

README「共享枚举出现位置」一节列出全部出现点，改动需两侧同步。
"""
from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class AgencyKind(StrEnum):
    """中介 / 采集渠道类型。"""

    BROKER = "broker"
    PLATFORM = "platform"
    FEED = "feed"


AGENCY_KIND_LABELS: dict[str, str] = {
    AgencyKind.BROKER.value: "中介门店",
    AgencyKind.PLATFORM.value: "信息平台",
    AgencyKind.FEED.value: "数据服务商",
}

AGENCY_KIND_ORDER: list[str] = [
    AgencyKind.BROKER.value,
    AgencyKind.PLATFORM.value,
    AgencyKind.FEED.value,
]


class ListingStatus(StrEnum):
    """挂牌状态。"""

    ACTIVE = "active"
    SOLD = "sold"
    OFF = "off_market"


LISTING_STATUS_LABELS: dict[str, str] = {
    ListingStatus.ACTIVE.value: "在售",
    ListingStatus.SOLD.value: "已成交未下架",
    ListingStatus.OFF.value: "已下架",
}

LISTING_STATUS_ORDER: list[str] = [
    ListingStatus.ACTIVE.value,
    ListingStatus.SOLD.value,
    ListingStatus.OFF.value,
]


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


RUN_STATUS_LABELS: dict[str, str] = {
    RunStatus.QUEUED.value: "排队中",
    RunStatus.RUNNING.value: "执行中",
    RunStatus.SUCCESS.value: "成功",
    RunStatus.PARTIAL.value: "部分成功",
    RunStatus.FAILED.value: "失败",
}


class TriggerKind(StrEnum):
    MANUAL = "manual"
    SCHEDULE = "schedule"
    SEED = "seed"


TRIGGER_LABELS: dict[str, str] = {
    TriggerKind.MANUAL.value: "手动",
    TriggerKind.SCHEDULE.value: "定时",
    TriggerKind.SEED.value: "初始化",
}


class RiskLevel(StrEnum):
    """簇 / 挂牌的风险等级。"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


RISK_LEVEL_LABELS: dict[str, str] = {
    RiskLevel.HIGH.value: "高风险",
    RiskLevel.MEDIUM.value: "中风险",
    RiskLevel.LOW.value: "低风险",
    RiskLevel.NONE.value: "正常",
}

RISK_LEVEL_ORDER: list[str] = [
    RiskLevel.HIGH.value,
    RiskLevel.MEDIUM.value,
    RiskLevel.LOW.value,
    RiskLevel.NONE.value,
]


class RiskTag(StrEnum):
    """算法 B 输出的风险标签。"""

    BAIT = "bait"
    STALE = "stale"
    SPREAD = "spread"


RISK_TAG_LABELS: dict[str, str] = {
    RiskTag.BAIT.value: "钓鱼价",
    RiskTag.STALE.value: "僵尸挂牌",
    RiskTag.SPREAD.value: "价格离散",
}

RISK_TAG_ORDER: list[str] = [RiskTag.BAIT.value, RiskTag.STALE.value, RiskTag.SPREAD.value]


class ReviewStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"


REVIEW_STATUS_LABELS: dict[str, str] = {
    ReviewStatus.PENDING.value: "待复核",
    ReviewStatus.CONFIRMED.value: "已确认",
    ReviewStatus.DISMISSED.value: "已驳回",
}

REVIEW_STATUS_ORDER: list[str] = [
    ReviewStatus.PENDING.value,
    ReviewStatus.CONFIRMED.value,
    ReviewStatus.DISMISSED.value,
]


class ReviewReason(StrEnum):
    BAIT = "bait"
    STALE = "stale"
    SPREAD = "spread"
    MANUAL = "manual"


REVIEW_REASON_LABELS: dict[str, str] = {
    ReviewReason.BAIT.value: "疑似钓鱼价",
    ReviewReason.STALE.value: "疑似僵尸挂牌",
    ReviewReason.SPREAD.value: "簇内价差异常",
    ReviewReason.MANUAL.value: "人工抽查",
}

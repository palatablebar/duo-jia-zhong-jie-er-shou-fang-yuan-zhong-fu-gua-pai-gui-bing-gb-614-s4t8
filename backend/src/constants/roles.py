"""角色 -> 权限点映射。README 与前端 site/js/config.js 同步。

角色键固定为 admin / analyst / viewer，各项目的展示名与职责不同。
"""
from __future__ import annotations

from src.constants.enums import Role

ROLE_LABELS: dict[str, str] = {
    Role.ADMIN.value: "平台管理员",
    Role.ANALYST.value: "数据专员",
    Role.VIEWER.value: "业务只读",
}

ROLE_DUTIES: dict[str, str] = {
    Role.ADMIN.value: "维护中介渠道与阈值、导出报表、查看审计",
    Role.ANALYST.value: "发起归并重算、复核风险簇、导出报表",
    Role.VIEWER.value: "只读查看挂牌与归并结果，不能重算、复核或导出",
}

PERMISSIONS: dict[str, set[str]] = {
    Role.ADMIN.value: {
        "agency:read", "agency:write",
        "listing:read", "property:read",
        "run:read", "run:create",
        "review:read", "review:write",
        "export:read", "audit:read", "overview:read",
    },
    Role.ANALYST.value: {
        "agency:read",
        "listing:read", "property:read",
        "run:read", "run:create",
        "review:read", "review:write",
        "export:read", "overview:read",
    },
    Role.VIEWER.value: {
        "agency:read", "listing:read", "property:read", "run:read", "review:read", "overview:read",
    },
}

AGENCY_WRITE_ROLES = (Role.ADMIN.value,)
RUN_CREATE_ROLES = (Role.ADMIN.value, Role.ANALYST.value)
REVIEW_ROLES = (Role.ADMIN.value, Role.ANALYST.value)
EXPORT_ROLES = (Role.ADMIN.value, Role.ANALYST.value)
AUDIT_ROLES = (Role.ADMIN.value,)
READ_ROLES = (Role.ADMIN.value, Role.ANALYST.value, Role.VIEWER.value)


def has_permission(role: str, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())

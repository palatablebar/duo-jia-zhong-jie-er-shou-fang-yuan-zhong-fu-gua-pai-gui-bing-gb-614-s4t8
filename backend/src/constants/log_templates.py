"""审计动作 -> 中文标签。"""
from __future__ import annotations

ACTIONS: dict[str, str] = {
    "auth.login": "登录",
    "agency.create": "登记中介渠道",
    "agency.update": "修改中介渠道",
    "run.create": "发起归并重算",
    "run.complete": "归并完成",
    "review.submit": "提交复核",
    "export.clusters": "导出归并簇",
    "export.listings": "导出挂牌明细",
    "review.seed": "初始化复核单",
    "http.mutation": "写请求",
}

"""契约层：权限矩阵、参数校验、分页夹取。"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.constants.enums import Role
from src.constants.roles import AUDIT_ROLES, EXPORT_ROLES, has_permission
from src.schemas.agency import AgencyIn
from src.schemas.match_run import RunIn
from src.schemas.review import ReviewIn
from src.utils.pagination import page_params


def test_viewer_cannot_write_or_export_or_audit():
    assert has_permission(Role.VIEWER.value, "listing:read") is True
    assert has_permission(Role.VIEWER.value, "agency:write") is False
    assert has_permission(Role.VIEWER.value, "review:write") is False
    assert has_permission(Role.VIEWER.value, "export:read") is False
    assert has_permission(Role.VIEWER.value, "audit:read") is False


def test_analyst_can_run_but_not_manage_agencies_or_audit():
    assert has_permission(Role.ANALYST.value, "run:create") is True
    assert has_permission(Role.ANALYST.value, "review:write") is True
    assert has_permission(Role.ANALYST.value, "export:read") is True
    assert has_permission(Role.ANALYST.value, "agency:write") is False
    assert has_permission(Role.ANALYST.value, "audit:read") is False
    assert Role.ADMIN.value in AUDIT_ROLES
    assert Role.VIEWER.value not in EXPORT_ROLES


def test_agency_payload_validation():
    with pytest.raises(ValidationError):
        AgencyIn(code="Bad Code", name="x")
    with pytest.raises(ValidationError):
        AgencyIn(code="ok", name="")
    with pytest.raises(ValidationError):
        AgencyIn(code="ok", name="ok name", kind="unknown")
    assert AgencyIn(code="xinyi", name="信义房屋").kind == "broker"


def test_run_threshold_bounds():
    with pytest.raises(ValidationError):
        RunIn(threshold=0.2)
    with pytest.raises(ValidationError):
        RunIn(threshold=1.6)
    with pytest.raises(ValidationError):
        RunIn(trigger="cron")
    assert RunIn().threshold == 0.80


def test_review_status_literal():
    with pytest.raises(ValidationError):
        ReviewIn(status="approved")
    assert ReviewIn(status="confirmed", note="ok").status == "confirmed"


def test_page_params_clamped():
    page = page_params(9999, -5)
    assert page.limit == 200
    assert page.offset == 0

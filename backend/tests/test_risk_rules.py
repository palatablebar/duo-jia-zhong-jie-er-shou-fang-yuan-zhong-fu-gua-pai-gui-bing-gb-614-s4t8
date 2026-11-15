"""业务模块 ⑤ 算法 B：僵尸与钓鱼挂牌识别。"""
from __future__ import annotations

from src.services import risk_rules


def _member(lid, price, days=30, views=5, status="active"):
    return {"id": hash(lid) % 10000, "lid": lid, "price_num": price, "listed_days": days, "views": views, "status": status}


def test_bait_flagged_when_below_ten_percent():
    golden = {"price_median": 6_000_000, "price_min": 5_280_000, "price_max": 6_060_000, "dispersion": 0.05}
    members = [_member("A-1", 5_280_000), _member("A-2", 6_000_000), _member("A-3", 6_060_000)]
    result = risk_rules.scan_cluster(members, golden)
    assert "bait" in result["risk_tags"]
    assert result["risk_detail"]["bait_lids"] == ["A-1"]
    assert result["risk_score"] >= 45


def test_no_bait_when_deviation_small():
    golden = {"price_median": 6_000_000, "price_min": 5_940_000, "price_max": 6_060_000, "dispersion": 0.02}
    members = [_member("A-1", 5_940_000), _member("A-2", 6_060_000)]
    result = risk_rules.scan_cluster(members, golden)
    assert "bait" not in result["risk_tags"]
    assert result["risk_level"] in {"low", "none"}


def test_stale_requires_long_days_and_zero_views():
    golden = {"price_median": 5_000_000, "price_min": 5_000_000, "price_max": 5_000_000, "dispersion": 0.0}
    stale = [_member("S-1", 5_000_000, days=220, views=0)]
    fresh = [_member("F-1", 5_000_000, days=220, views=8)]
    short = [_member("F-2", 5_000_000, days=120, views=0)]
    assert risk_rules.scan_cluster(stale, golden)["risk_tags"] == ["stale"]
    assert "stale" not in risk_rules.scan_cluster(fresh, golden)["risk_tags"]
    assert "stale" not in risk_rules.scan_cluster(short, golden)["risk_tags"]


def test_spread_tag_and_score_bounds():
    golden = {"price_median": 6_000_000, "price_min": 4_000_000, "price_max": 8_000_000, "dispersion": 0.35}
    members = [_member("B-1", 4_000_000, days=400, views=0), _member("B-2", 8_000_000)]
    result = risk_rules.scan_cluster(members, golden)
    assert "spread" in result["risk_tags"]
    assert "bait" in result["risk_tags"]
    assert "stale" in result["risk_tags"]
    assert 0 <= result["risk_score"] <= 100
    assert result["risk_level"] == "high"
    assert result["risk_detail"]["spread_points"] <= 20


def test_empty_cluster_is_clean():
    result = risk_rules.scan_cluster([], {"price_median": 0, "dispersion": 0.0})
    assert result["risk_score"] == 0
    assert result["risk_level"] == "none"
    assert result["risk_tags"] == []


def test_deterministic_scan():
    golden = {"price_median": 6_000_000, "price_min": 5_200_000, "price_max": 6_100_000, "dispersion": 0.12}
    members = [_member("C-1", 5_200_000, days=200, views=0), _member("C-2", 6_100_000)]
    assert risk_rules.scan_cluster(members, golden) == risk_rules.scan_cluster(members, golden)

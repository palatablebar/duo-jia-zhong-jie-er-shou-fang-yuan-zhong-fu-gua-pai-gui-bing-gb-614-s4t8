"""业务模块 ② 字段解析归一：真实写法覆盖 + 边界。"""
from __future__ import annotations

import pytest

from src.services import normalizer


@pytest.mark.parametrize(
    "text,expected",
    [
        ("89.5㎡", 89.5),
        ("89.5平米", 89.5),
        ("建面89.5", 89.5),
        ("89.5 平方米", 89.5),
        ("建筑面积89.5㎡", 89.5),
        ("89.5平方米（套内72）", 89.5),
        ("118", 118.0),
    ],
)
def test_area_variants(text, expected):
    value, _flags = normalizer.parse_area(text)
    assert value == expected


def test_area_missing_or_dirty():
    value, flags = normalizer.parse_area("暂无")
    assert value is None
    assert "area_missing" in flags


@pytest.mark.parametrize(
    "text,gross,inner,caliber",
    [
        ("建筑面积108㎡", 108.0, None, "gross"),
        ("建面89.5", 89.5, None, "gross"),
        ("套内84㎡", None, 84.0, "inner"),
        ("套内面积84平方米", None, 84.0, "inner"),
        ("套内建筑面积84㎡", None, 84.0, "inner"),
        ("使用面积76.5㎡", None, 76.5, "inner"),
        ("89.5平方米（套内72）", 89.5, 72.0, "both"),
        ("建筑面积108㎡ 套内84㎡", 108.0, 84.0, "both"),
        ("89.5㎡", None, None, "unknown"),
        ("118", None, None, "unknown"),
        ("暂无", None, None, "missing"),
    ],
)
def test_area_caliber_variants(text, gross, inner, caliber):
    detail = normalizer.parse_area_detail(text)
    assert detail["gross"] == gross
    assert detail["inner"] == inner
    assert detail["caliber"] == caliber


def test_area_caliber_flags_and_canonical_value():
    norm = normalizer.normalize_listing(
        {
            "community_raw": "翠湖名邸",
            "layout_raw": "3-2-1",
            "area_raw": "套内84㎡",
            "price_raw": "598万",
            "floor_raw": "2/18",
            "orientation_raw": "南北",
            "title": "",
        }
    )
    assert norm["area_caliber"] == "inner"
    assert norm["area_inner"] == 84.0
    # 仅套内：单条阶段不折算，待 calibrate_areas 按小区得房率回填
    assert norm["area_num"] is None
    assert "area_caliber_inner" in norm["parse_flags"]


def test_area_falls_back_to_title_when_missing():
    norm = normalizer.normalize_listing(
        {
            "community_raw": "翠湖名邸",
            "layout_raw": "3-2-1",
            "area_raw": "暂无",
            "price_raw": "598万",
            "floor_raw": "2/18",
            "orientation_raw": "南北",
            "title": "翠湖名邸 建筑面积108㎡ 套内84㎡ 南北通透",
        }
    )
    assert norm["area_caliber"] == "both"
    assert norm["area_gross"] == 108.0
    assert norm["area_inner"] == 84.0
    assert norm["area_num"] == 108.0
    assert "area_from_title" in norm["parse_flags"]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("3/18", (3, 18, "low")),
        ("3层/共18层", (3, 18, "low")),
        ("12层", (12, None, "mid")),
        ("低楼层(共18层)", (None, 18, "low")),
        ("高楼层(共33层)", (None, 33, "high")),
    ],
)
def test_floor_variants(text, expected):
    floor, total, band, _flags = normalizer.parse_floor(text)
    assert (floor, total, band) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("598万", 5_980_000),
        ("602万元", 6_020_000),
        ("总价604万", 6_040_000),
        ("6,020,000元", 6_020_000),
        ("604 万（可谈）", 6_040_000),
        ("598.5万", 5_985_000),
    ],
)
def test_price_variants(text, expected):
    value, _flags = normalizer.parse_price(text)
    assert value == expected


def test_price_missing():
    value, flags = normalizer.parse_price("价格面议")
    assert value is None
    assert "price_missing" in flags


@pytest.mark.parametrize(
    "text,expected",
    [
        ("3-2-1", "3-2-1"),
        ("3室2厅1卫", "3-2-1"),
        ("三室两厅一卫", "3-2-1"),
        ("3房2厅1卫", "3-2-1"),
        ("3/2/1", "3-2-1"),
        ("2-1", "2-1-0"),
    ],
)
def test_layout_variants(text, expected):
    assert normalizer.parse_layout(text)[0] == expected


def test_orientation_and_community_normalization():
    assert normalizer.parse_orientation("南北通透")[0] == "南北"
    assert normalizer.parse_orientation("朝南北")[0] == "南北"
    assert normalizer.parse_orientation("朝南")[0] == "南"
    assert normalizer.parse_community(" 翠湖·名邸 ")[0] == "翠湖名邸"
    assert normalizer.parse_community("翠湖名邸（一期）")[0] == "翠湖名邸"


def test_title_tokens_are_shared_for_similar_titles():
    left = normalizer.title_tokens("3-2-1 89.5平方米 南北 2层 满五唯一")
    right = normalizer.title_tokens("3-2-1 89.5平方米 南北 2层 近地铁")
    overlap = len(set(left) & set(right)) / len(set(left) | set(right))
    assert overlap > 0.55


def test_normalize_listing_returns_all_fields():
    norm = normalizer.normalize_listing(
        {
            "community_raw": " 翠湖名邸（一期）",
            "layout_raw": "三室两厅一卫",
            "area_raw": "建面89.5",
            "price_raw": "总价598万",
            "floor_raw": "2/18",
            "orientation_raw": "南北通透",
            "title": "3-2-1 89.5平方米 南北 2层 满五唯一",
        }
    )
    assert norm["community_norm"] == "翠湖名邸"
    assert norm["layout_norm"] == "3-2-1"
    assert norm["area_num"] == 89.5
    assert norm["price_num"] == 5_980_000
    assert norm["floor_num"] == 2
    assert norm["floor_total"] == 18
    assert norm["floor_band"] == "low"
    assert norm["orientation_norm"] == "南北"
    assert norm["parse_flags"] == ["community_bracket_removed"]
    assert normalizer.area_bucket(89.5) == 17

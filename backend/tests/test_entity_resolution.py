"""业务模块 ③④ 算法 A：blocking / 相似度 / 并查集 / golden record。"""
from __future__ import annotations

from src.constants.limits import SIMILARITY_THRESHOLD
from src.services import entity_resolution as er
from src.services import normalizer


def _row(community="翠湖名邸", layout="3-2-1", area="89.5", price="598万", floor="2/18", orientation="南北", title="3-2-1 89.5平方米 南北 2层 满五唯一"):
    return normalizer.normalize_listing(
        {
            "community_raw": community,
            "layout_raw": layout,
            "area_raw": area,
            "price_raw": price,
            "floor_raw": floor,
            "orientation_raw": orientation,
            "title": title,
        }
    )


def test_duplicate_pair_scores_above_threshold():
    left = _row(area="89.5㎡", price="598万")
    right = _row(area="建面89.5", price="602万")
    detail = er.similarity(left, right)
    assert detail["score"] >= SIMILARITY_THRESHOLD
    assert detail["area"] == 1.0
    assert detail["floor"] == 1.0
    assert detail["orientation"] == 1.0
    assert detail["score"] == round(
        0.35 * detail["area"] + 0.25 * detail["price"] + 0.20 * detail["floor"]
        + 0.10 * detail["orientation"] + 0.10 * detail["title"],
        4,
    )


def test_distinct_property_scores_below_threshold():
    left = _row(area="89.5", price="598万")
    right = _row(area="89.5", price="598万", floor="12/18", orientation="北", title="2-1-1 62平方米 北 12层 采光好")
    detail = er.similarity(left, right)
    assert detail["score"] < SIMILARITY_THRESHOLD


def test_blocking_excludes_far_area_and_other_community():
    rows = [
        _row(area="89.5"),
        _row(area="91.5"),  # 同小区同户型，面积差 2㎡ -> 候选
        _row(area="118"),  # 面积差过大 -> 不入候选
        _row(community="仁恒河滨城", area="89.5"),  # 换小区 -> 不入候选
    ]
    pairs = er.candidate_pairs(rows)
    assert (0, 1) in pairs
    assert all(2 not in pair and 3 not in pair for pair in pairs)


def test_union_find_transitive_closure():
    """A~B、B~C 都过阈值，则 A/B/C 归为同一簇（传递闭包）。"""
    rows = [
        _row(area="89.5", price="598万"),
        _row(area="89.5", price="602万"),
        _row(area="89.5", price="606万"),
    ]
    result = er.resolve(rows, [1, 2, 3])
    assert result["metrics"]["clusters"] == 1
    assert result["clusters"][0]["members"] == [0, 1, 2]
    assert 0.8 <= result["clusters"][0]["confidence"] <= 1.0


def test_golden_record_median_mode_and_agency_count():
    rows = [_row(area="89.5", price="598万"), _row(area="89.5", price="602万"), _row(area="89.5", price="610万")]
    result = er.resolve(rows, [11, 22, 33])
    golden = result["clusters"][0]["golden"]
    assert golden["price_median"] == 6_020_000
    assert golden["area_mode"] == 89.5
    assert golden["price_min"] == 5_980_000
    assert golden["price_max"] == 6_100_000
    assert golden["spread"] == 120_000
    assert golden["agency_count"] == 3
    assert golden["member_count"] == 3


def test_deterministic_resolution():
    rows = [_row(area="89.5", price="598万"), _row(area="89.5", price="602万"), _row(area="118", price="780万")]
    first = er.resolve(rows, [1, 2, 3])
    second = er.resolve(rows, [1, 2, 3])
    assert first == second


def test_threshold_controls_linking():
    rows = [_row(area="89.5", price="598万"), _row(area="89.5", price="700万")]
    loose = er.resolve(rows, [1, 2], threshold=0.80)
    strict = er.resolve(rows, [1, 2], threshold=0.99)
    assert loose["metrics"]["clusters"] == 1
    assert strict["metrics"]["clusters"] == 2


def test_cross_caliber_same_property_merges():
    """中介 A 建面 108 / 中介 B 仅套内 84 / 中介 C 双口径：同一套房并成一簇（跨中介覆盖率）。"""
    rows = [
        _row(area="建筑面积108㎡", price="598万"),
        _row(area="套内84㎡", price="602万"),
        _row(area="建筑面积108㎡（套内84㎡）", price="606万"),
    ]
    result = er.resolve(rows, [1, 2, 3])
    assert result["metrics"]["clusters"] == 1
    golden = result["clusters"][0]["golden"]
    assert golden["area_caliber"] == "mixed"
    assert abs(golden["area_mode"] - 108.0) < 1.0
    basis = golden["area_basis"]
    assert basis["members_inferred"] == 1
    assert abs(basis["inner_ratio"] - 84.0 / 108.0) < 0.01
    assert basis["ratio_source"] == "community"
    assert "套内" in basis["summary"]


def test_adjacent_layout_not_merged_by_conversion():
    """同小区相邻户型：套内折算把 84 折成 105 后，只能并上真正的 105 那套，不能把 108 也凑进来。"""
    rows = [
        _row(area="建筑面积108㎡（套内86.4㎡）", price="598万", floor="2/18"),
        _row(area="套内84㎡", price="592万", floor="9/18", orientation="北", title="3-2-1 105平方米 北 9层 随时看房"),
        _row(area="建筑面积105㎡", price="590万", floor="9/18", orientation="北", title="3-2-1 105平方米 北 9层 随时看房"),
    ]
    result = er.resolve(rows, [1, 2, 3])
    assert result["metrics"]["clusters"] == 2
    sizes = sorted(len(cluster["members"]) for cluster in result["clusters"])
    assert sizes == [1, 2]
    merged = next(cluster for cluster in result["clusters"] if len(cluster["members"]) == 2)
    assert merged["members"] == [1, 2]
    assert merged["golden"]["area_caliber"] == "mixed"


def test_inferred_link_requires_tighter_area_diff():
    """折算面积参与的连边面积差硬上限 3㎡：总分过阈值但差 3.2㎡ 的折算对不连。"""
    rows = [
        _row(area="建筑面积100㎡（套内80㎡）", price="500万"),
        _row(area="套内82.56㎡", price="500万"),  # 折 103.2，与 100 差 3.2㎡
    ]
    result = er.resolve(rows, [1, 2])
    assert result["metrics"]["clusters"] == 2
    direct = [
        _row(area="建筑面积100㎡", price="500万"),
        _row(area="建筑面积103.2㎡", price="500万"),
    ]
    assert er.resolve(direct, [1, 2])["metrics"]["clusters"] == 1


def test_calibrate_areas_idempotent():
    rows = [_row(area="套内84㎡"), _row(area="建筑面积108㎡（套内84㎡）")]
    er.calibrate_areas(rows)
    snapshot = [(row["area_num"], row["area_inferred"], row["area_basis"]) for row in rows]
    er.calibrate_areas(rows)
    assert [(row["area_num"], row["area_inferred"], row["area_basis"]) for row in rows] == snapshot


def test_rerun_same_batch_does_not_spawn_new_clusters():
    """口径缺失/仅套内的挂牌同批重跑：两次 resolve 簇集合逐字一致（不新增簇）。"""
    rows = [
        _row(area="89.5㎡", price="598万"),
        _row(area="套内71.6㎡", price="602万"),
        _row(area="建筑面积89.5㎡（套内71.6㎡）", price="606万"),
        _row(area="118", price="780万", floor="12/18"),
    ]
    first = er.resolve([dict(row) for row in rows], [1, 2, 3, 4])
    second = er.resolve([dict(row) for row in rows], [1, 2, 3, 4])
    assert first["metrics"]["clusters"] == second["metrics"]["clusters"] == 2
    assert [cluster["members"] for cluster in first["clusters"]] == [
        cluster["members"] for cluster in second["clusters"]
    ]
    # 口径缺失的挂牌保持直采，不参与得房率估计也不被折算
    assert rows[0]["area_caliber"] == "unknown"
    assert rows[0]["area_inferred"] is False

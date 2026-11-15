"""字段解析归一（业务模块 ②）：把 9 家中介五花八门的写法压成可比字段。

示例：``89.5㎡`` / ``89.5平米`` / ``建面89.5`` / ``89.5 平方米`` -> 89.5
      ``3/18`` / ``3层/共18层`` / ``低楼层(共18层)``        -> (3, 18, low)
      ``598万`` / ``6,020,000元`` / ``598.5万元``            -> 5980000 / 6020000

面积带口径：``建筑面积108㎡`` -> gross=108；``套内84㎡`` -> inner=84；
``89.5平方米（套内72）`` -> both（gross=89.5, inner=72）；``89.5㎡`` -> 口径缺失直采。
全部为纯函数，确定性，无外部依赖。
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping

from src.constants.limits import AREA_TOLERANCE_M2

_CN_NUM = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}

# 面积口径标记词：出现在数字之前，用于判定该数字是建筑面积还是套内面积
_GROSS_MARKS = ("建筑面积", "建面", "产权面积")
_INNER_MARKS = ("套内建筑面积", "套内面积", "套内", "使用面积")


def _to_half(text: str | None) -> str:
    return unicodedata.normalize("NFKC", text or "").strip()


def _first_number(text: str) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", text)
    return float(match.group(0)) if match else None


def _number_after(text: str, marks: tuple[str, ...], skip_before: str | None = None) -> float | None:
    """标记词之后的第一个数字（``建筑面积108㎡`` -> 108）。

    ``skip_before``：标记词前紧邻该串时跳过（``套内建筑面积`` 里的「建筑面积」不算建面口径）。
    """
    for mark in marks:
        start = 0
        while True:
            index = text.find(mark, start)
            if index < 0:
                break
            start = index + len(mark)
            if skip_before and text[max(0, index - len(skip_before)) : index] == skip_before:
                continue
            match = re.search(r"\d+(?:\.\d+)?", text[start:])
            if match:
                return float(match.group(0))
    return None


def parse_area_detail(text: str | None) -> dict:
    """面积 -> 口径明细：gross（建筑面积）/ inner（套内）/ value（无口径直采值）+ caliber。

    caliber：``gross`` 明确建面 / ``inner`` 仅套内 / ``both`` 双口径 /
    ``unknown`` 有数字无口径 / ``missing`` 缺失。
    无口径数字与套内并存时（``89.5平方米（套内72）``），按行业惯例把无口径数字视为建筑面积。
    """
    half = _to_half(text)
    missing = {"gross": None, "inner": None, "value": None, "caliber": "missing", "flags": ["area_missing"]}
    if not half:
        return dict(missing)
    gross = _number_after(half, _GROSS_MARKS, skip_before="套内")
    inner = _number_after(half, _INNER_MARKS)
    first = _first_number(half)
    if gross is None and inner is None and first is None:
        return dict(missing)
    if gross is None and inner is not None and first is not None and abs(first - inner) > 1e-9:
        gross = first
    flags: list[str] = []
    if gross is not None and inner is not None:
        caliber = "both"
        flags.append("area_caliber_both")
    elif gross is not None:
        caliber = "gross"
    elif inner is not None:
        caliber = "inner"
        flags.append("area_caliber_inner")
    else:
        caliber = "unknown"
        flags.append("area_caliber_unknown")
    taken = gross if gross is not None else (first if first is not None else inner)
    if taken is not None and (taken < 5 or taken > 2000):
        flags.append("area_out_of_range")
    return {
        "gross": round(gross, 2) if gross is not None else None,
        "inner": round(inner, 2) if inner is not None else None,
        "value": round(first, 2) if first is not None else None,
        "caliber": caliber,
        "flags": flags,
    }


def parse_area(text: str | None) -> tuple[float | None, list[str]]:
    """面积 -> 平方米数值（第一个数字；口径明细见 :func:`parse_area_detail`）。"""
    detail = parse_area_detail(text)
    return detail["value"], detail["flags"]


def area_basis_text(
    caliber: str,
    gross: float | None,
    inner: float | None,
    value: float | None,
    taken: float | None,
    ratio: float | None = None,
    ratio_source: str | None = None,
) -> str:
    """单条挂牌的面积采信依据（估价师在簇成员对照里看到的说明）。"""
    if caliber == "missing":
        return "面积缺失"
    if caliber == "gross":
        return f"原文建筑面积 {gross:g}㎡，直采"
    if caliber == "both":
        return f"原文双口径：建筑面积 {gross:g}㎡ / 套内 {inner:g}㎡，采信建筑面积"
    if caliber == "unknown":
        return f"口径缺失，按原文直采 {value:g}㎡（视为建筑面积）"
    if ratio:
        source = {"community": "小区实测", "global": "全库实测", "default": "默认得房率"}.get(
            ratio_source or "", ratio_source or ""
        )
        return f"原文仅套内 {inner:g}㎡，÷ 得房率 {ratio:.3f}（{source}）≈ {taken:g}㎡"
    return f"原文仅套内 {inner:g}㎡，待折算"


def parse_layout(text: str | None) -> tuple[str, list[str]]:
    """户型 -> ``室-厅-卫``（缺失的卫记为 0）。"""
    half = _to_half(text)
    flags: list[str] = []
    if not half:
        return "", ["layout_missing"]
    normalized = re.sub(r"([一二两三四五六七八九])(?=\s*[室房居厅卫])", lambda m: str(_CN_NUM[m.group(1)]), half)
    match = re.search(r"(\d+)\s*(?:室|房|居)\s*(\d+)\s*厅(?:\s*(\d+)\s*卫)?", normalized)
    if match:
        baths = match.group(3)
        if baths is None:
            flags.append("layout_no_bath")
        return f"{int(match.group(1))}-{int(match.group(2))}-{int(baths) if baths else 0}", flags
    match = re.search(r"(\d+)\s*[-/]\s*(\d+)\s*[-/]\s*(\d+)", normalized)
    if match:
        return f"{int(match.group(1))}-{int(match.group(2))}-{int(match.group(3))}", flags
    match = re.search(r"(\d+)\s*[-/]\s*(\d+)", normalized)
    if match:
        flags.append("layout_no_bath")
        return f"{int(match.group(1))}-{int(match.group(2))}-0", flags
    return "", ["layout_unparsed"]


def floor_band_of(floor: int | None, total: int | None) -> str:
    if floor is None:
        return ""
    if total and total > 0:
        ratio = floor / total
        if ratio <= 0.33:
            return "low"
        if ratio <= 0.66:
            return "mid"
        return "high"
    if floor <= 6:
        return "low"
    if floor <= 12:
        return "mid"
    return "high"


def parse_floor(text: str | None) -> tuple[int | None, int | None, str, list[str]]:
    """楼层 -> (所在层, 总层, 低/中/高, 归一标记)。"""
    half = _to_half(text)
    flags: list[str] = []
    if not half:
        return None, None, "", ["floor_missing"]
    band_hint = ""
    if "低" in half:
        band_hint = "low"
    elif "中" in half:
        band_hint = "mid"
    elif "高" in half:
        band_hint = "high"
    floor: int | None = None
    total: int | None = None
    match = re.search(r"(\d+)\s*层?\s*/\s*共?\s*(\d+)\s*层?", half)
    if not match:
        match = re.search(r"(\d+)\s*/\s*(\d+)", half)
    if match:
        floor, total = int(match.group(1)), int(match.group(2))
    else:
        total_match = re.search(r"共\s*(\d+)\s*层", half)
        if total_match:
            total = int(total_match.group(1))
        single = re.search(r"(\d+)\s*层", half)
        if single:
            floor = int(single.group(1))
            if total is not None and floor == total:
                floor = None
    if floor is None and band_hint:
        flags.append("floor_band_only")
    band = band_hint or floor_band_of(floor, total)
    if floor is None and not band_hint:
        flags.append("floor_unparsed")
    return floor, total, band, flags


_ORIENTATION_GROUPS: list[tuple[str, tuple[str, ...]]] = [
    ("南北", ("南北通透", "南北向", "朝南北", "南北")),
    ("东南", ("东南",)),
    ("西南", ("西南",)),
    ("东北", ("东北",)),
    ("西北", ("西北",)),
    ("南", ("朝南", "正南", "南向", "南")),
    ("北", ("朝北", "正北", "北向", "北")),
    ("东", ("朝东", "正东", "东向", "东")),
    ("西", ("朝西", "正西", "西向", "西")),
]


def parse_orientation(text: str | None) -> tuple[str, list[str]]:
    """朝向 -> 标准朝向。"""
    half = _to_half(text).replace(" ", "")
    if not half:
        return "", ["orientation_missing"]
    for canonical, aliases in _ORIENTATION_GROUPS:
        for alias in aliases:
            if alias in half:
                return canonical, []
    return half, ["orientation_unparsed"]


def parse_price(text: str | None) -> tuple[int | None, list[str]]:
    """挂牌价 -> 元（整数）。支持 万 / 亿 / 纯数字。"""
    half = _to_half(text).replace(",", "").replace("，", "")
    if not half:
        return None, ["price_missing"]
    value = _first_number(half)
    if value is None:
        return None, ["price_missing"]
    flags: list[str] = []
    if "亿" in half:
        amount = value * 100_000_000
    elif "万" in half:
        amount = value * 10_000
    elif value < 10_000:
        amount = value * 10_000
        flags.append("price_unit_inferred")
    else:
        amount = value
    return int(round(amount)), flags


def parse_community(text: str | None) -> tuple[str, list[str]]:
    """小区名 -> 归一名（去空白/间隔符，去掉结尾括号备注）。"""
    half = _to_half(text)
    if not half:
        return "", ["community_missing"]
    flags: list[str] = []
    cleaned = re.sub(r"\s+", "", half)
    for mark in ("·", "・", "•", "‧"):
        cleaned = cleaned.replace(mark, "")
    stripped = re.sub(r"[（(][^）)]*[）)]$", "", cleaned)
    if stripped and stripped != cleaned:
        flags.append("community_bracket_removed")
        cleaned = stripped
    return cleaned, flags


def title_tokens(title: str | None) -> list[str]:
    """标题 -> 字符二元组集合（用于 Jaccard 相似度）。"""
    half = _to_half(title).lower()
    half = re.sub(r"[^\w\u4e00-\u9fff]+", "", half)
    if len(half) < 2:
        return [half] if half else []
    return sorted({half[index : index + 2] for index in range(len(half) - 1)})


def normalize_listing(raw: Mapping[str, object]) -> dict:
    """把一条原始挂牌压成可比字段；返回纯字典（可 JSON 化）。

    面积统一为建筑面积口径：gross/both/unknown 在单条阶段即可定值；
    仅套内（inner）的挂牌 area_num 暂为 None，由算法 A 的 calibrate_areas
    按小区实测得房率折算后回填（见 entity_resolution）。
    """
    flags: list[str] = []
    community_norm, f_community = parse_community(str(raw.get("community_raw") or ""))
    layout_norm, f_layout = parse_layout(str(raw.get("layout_raw") or ""))
    title = str(raw.get("title") or "")
    area = parse_area_detail(str(raw.get("area_raw") or ""))
    if area["caliber"] == "missing":
        # 面积缺失时回退解析标题（有中介把面积口径写进标题）
        title_area = parse_area_detail(title)
        if title_area["caliber"] != "missing":
            area = title_area
            area["flags"] = [*area["flags"], "area_from_title"]
    price_num, f_price = parse_price(str(raw.get("price_raw") or ""))
    floor_num, floor_total, floor_band, f_floor = parse_floor(str(raw.get("floor_raw") or ""))
    orientation_norm, f_orientation = parse_orientation(str(raw.get("orientation_raw") or ""))
    flags.extend(f_community + f_layout + area["flags"] + f_price + f_floor + f_orientation)
    caliber = area["caliber"]
    if caliber in ("gross", "both"):
        area_num = area["gross"]
    elif caliber == "unknown":
        area_num = area["value"]
    else:  # inner：待 calibrate_areas 折算；missing：无面积
        area_num = None
    return {
        "community_norm": community_norm,
        "layout_norm": layout_norm,
        "area_num": area_num,
        "area_gross": area["gross"],
        "area_inner": area["inner"],
        "area_value": area["value"],
        "area_caliber": caliber,
        "area_inferred": False,
        "area_ratio": None,
        "area_ratio_source": None,
        "area_basis": area_basis_text(caliber, area["gross"], area["inner"], area["value"], area_num),
        "price_num": price_num,
        "floor_num": floor_num,
        "floor_total": floor_total,
        "floor_band": floor_band,
        "orientation_norm": orientation_norm,
        "title_tokens": title_tokens(title),
        "parse_flags": flags,
    }


def area_bucket(area: float | None) -> int | None:
    """blocking 用的面积桶（5㎡ 一档）。"""
    if area is None:
        return None
    return int(area // AREA_TOLERANCE_M2)

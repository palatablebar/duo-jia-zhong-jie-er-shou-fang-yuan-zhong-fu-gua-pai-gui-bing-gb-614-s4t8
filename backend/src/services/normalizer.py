"""字段解析归一（业务模块 ②）：把 9 家中介五花八门的写法压成可比字段。

示例：``89.5㎡`` / ``89.5平米`` / ``建面89.5`` / ``89.5 平方米`` -> 89.5
      ``3/18`` / ``3层/共18层`` / ``低楼层(共18层)``        -> (3, 18, low)
      ``598万`` / ``6,020,000元`` / ``598.5万元``            -> 5980000 / 6020000
全部为纯函数，确定性，无外部依赖。
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping

from src.constants.limits import AREA_TOLERANCE_M2

_CN_NUM = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def _to_half(text: str | None) -> str:
    return unicodedata.normalize("NFKC", text or "").strip()


def _first_number(text: str) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", text)
    return float(match.group(0)) if match else None


def parse_area(text: str | None) -> tuple[float | None, list[str]]:
    """面积 -> 平方米数值。"""
    half = _to_half(text)
    flags: list[str] = []
    if not half:
        return None, ["area_missing"]
    value = _first_number(half)
    if value is None:
        return None, ["area_missing"]
    if value < 5 or value > 2000:
        flags.append("area_out_of_range")
    if "套内" in half:
        flags.append("area_has_inner")
    return round(value, 2), flags


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
    """把一条原始挂牌压成可比字段；返回纯字典（可 JSON 化）。"""
    flags: list[str] = []
    community_norm, f_community = parse_community(str(raw.get("community_raw") or ""))
    layout_norm, f_layout = parse_layout(str(raw.get("layout_raw") or ""))
    area_num, f_area = parse_area(str(raw.get("area_raw") or ""))
    price_num, f_price = parse_price(str(raw.get("price_raw") or ""))
    floor_num, floor_total, floor_band, f_floor = parse_floor(str(raw.get("floor_raw") or ""))
    orientation_norm, f_orientation = parse_orientation(str(raw.get("orientation_raw") or ""))
    flags.extend(f_community + f_layout + f_area + f_price + f_floor + f_orientation)
    return {
        "community_norm": community_norm,
        "layout_norm": layout_norm,
        "area_num": area_num,
        "price_num": price_num,
        "floor_num": floor_num,
        "floor_total": floor_total,
        "floor_band": floor_band,
        "orientation_norm": orientation_norm,
        "title_tokens": title_tokens(str(raw.get("title") or "")),
        "parse_flags": flags,
    }


def area_bucket(area: float | None) -> int | None:
    """blocking 用的面积桶（5㎡ 一档）。"""
    if area is None:
        return None
    return int(area // AREA_TOLERANCE_M2)

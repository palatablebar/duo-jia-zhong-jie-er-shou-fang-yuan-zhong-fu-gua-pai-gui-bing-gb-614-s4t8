"""演示账号与种子数据集（确定性生成，不依赖数据库）。

数据集口径（与 batch-plan gb-614 验收一致）：
  9 家中介 × 60 条挂牌 = 540 条原始挂牌 → 386 个房源簇（41 个多成员簇）；
  其中「翠湖名邸 3-2-1 89.5㎡」在 4 家中介交叉命中、价差 12 万；
  1 个簇含 2 条钓鱼价（低于簇中位 11% 以上）；5 条僵尸挂牌（>180 天且 0 带看）。
"""

DEMO_PASSWORD = "Demo@2026"

DEMO_USERS = [
    ("admin@listingmerge.io", "林可 · 平台管理员", "admin"),
    ("analyst@listingmerge.io", "周棠 · 数据专员", "analyst"),
    ("viewer@listingmerge.io", "陈默 · 业务只读", "viewer"),
]

ORG = "安家数据 · 房源中台"

AGENCIES = [
    {
        "code": "lianjia",
        "name": "链家 · 浦东花木店",
        "kind": "broker",
        "endpoint": "https://sh.lianjia.com/ershoufang/pudong/",
        "note": "字段最规整，面积写 89.5㎡，价格写 598 万",
        "config": {"crawl": "daily", "respect_robots": True},
    },
    {
        "code": "wawj",
        "name": "我爱我家 · 世纪公园店",
        "kind": "broker",
        "endpoint": "https://sh.5i5j.com/ershoufang/",
        "note": "面积常写「89.5平米」，楼层只写低/中/高",
        "config": {"crawl": "daily", "respect_robots": True},
    },
    {
        "code": "zhongyuan",
        "name": "中原地产 · 联洋店",
        "kind": "broker",
        "endpoint": "https://sh.centanet.com/ershoufang/",
        "note": "价格单位混用「万 / 元」，需要归一",
        "config": {"crawl": "daily", "respect_robots": True},
    },
    {
        "code": "zhijia",
        "name": "21 世纪不动产 · 塘桥店",
        "kind": "broker",
        "endpoint": "https://www.century21cn.com/sh/",
        "note": "标题带门店后缀，户型写「三室两厅一卫」",
        "config": {"crawl": "daily", "respect_robots": True},
    },
    {
        "code": "fangdd",
        "name": "房多多 · 线上撮合",
        "kind": "platform",
        "endpoint": "https://www.fangdd.com/sh/",
        "note": "接口返回 JSON，面积偶有「建面89.5」写法",
        "config": {"crawl": "hourly", "api": "/v2/listings"},
    },
    {
        "code": "anjuke",
        "name": "安居客 · 浦东频道",
        "kind": "platform",
        "endpoint": "https://shanghai.anjuke.com/sale/pudong/",
        "note": "挂牌量大，重复率高，价格含「万（可谈）」",
        "config": {"crawl": "hourly", "respect_robots": True},
    },
    {
        "code": "ke",
        "name": "贝壳找房 · 数据服务",
        "kind": "feed",
        "endpoint": "https://sh.ke.com/ershoufang/",
        "note": "按天推送 CSV，面积带「建筑面积」前缀",
        "config": {"crawl": "daily", "format": "csv"},
    },
    {
        "code": "taofang",
        "name": "淘房网 · 数据服务",
        "kind": "feed",
        "endpoint": "https://www.taofang.com/sh/",
        "note": "历史挂架混杂已成交房源，需要僵尸识别",
        "config": {"crawl": "weekly", "format": "csv"},
    },
    {
        "code": "hongkan",
        "name": "宏康地产 · 金桥店",
        "kind": "broker",
        "endpoint": "https://www.hongkang.example.com/list",
        "note": "人工登记为主，字段偶尔缺失（面积/楼层）",
        "config": {"crawl": "manual", "steward": "门店店长"},
    },
]

COMMUNITIES = [
    "翠湖名邸",
    "仁恒河滨城",
    "联洋花园",
    "世纪公园壹号",
    "香梅花园",
    "大唐盛世花园",
    "金桥湾",
    "碧云国际",
    "花木星辰",
    "广洋新景",
    "陆家嘴中央公寓",
    "浦东世纪花园",
    "汤臣豪园",
    "罗山花苑",
    "东珂花苑",
    "绿城玉兰花园",
    "中星美华村",
    "金色维也纳",
    "万邦都市花园",
    "四季雅苑",
    "康桥半岛",
    "张江汤臣豪园",
    "阳光欧洲城",
    "海上国际花园",
]

LAYOUTS = ["2-1-1", "3-2-1", "3-2-2", "4-2-2"]
LAYOUT_CN = {"2-1-1": "两室一厅一卫", "3-2-1": "三室两厅一卫", "3-2-2": "三室两厅两卫", "4-2-2": "四室两厅两卫"}

ORIENTATION_VARIANTS = {
    "南北": ["南北", "南北通透", "南北向", "朝南北"],
    "南": ["南", "朝南", "正南"],
    "东南": ["东南", "朝东南"],
    "西南": ["西南", "朝西南"],
    "东": ["东", "朝东"],
    "北": ["北", "朝北"],
}
ORIENTATION_CYCLE = ["南北", "南", "南北", "东南", "南", "东", "南北", "南", "西南", "北"]

AREA_VARIANTS = ["{a}㎡", "{a}平米", "建面{a}", "{a} 平方米", "建筑面积{a}㎡", "{a}平方米（套内{inner}）"]
PRICE_VARIANTS = ["{w}万", "{w}万元", "总价{w}万", "{yuan}元", "{w} 万（可谈）"]
TITLE_SUFFIX = ["满五唯一", "近地铁", "采光好", "随时看房", "业主诚心卖"]

COMMUNITY_VARIANTS = ["{c}", "{c} ", " {c}", "{c}（一期）"]

# ---- 簇结构：41 个多成员簇（1×4 + 31×5 + 9×4 = 195 条）+ 345 个单成员簇 = 540 条 ----
CLUSTER_SIZES: list[int] = [4] + [5] * 31 + [4] * 9 + [1] * 345
SPECIAL_SPREAD_CLUSTER = 0
BAIT_CLUSTER = 1
STALE_CLUSTER_INDEXES = (50, 120, 210, 300, 350)
DIRTY_FLOOR_INDEX = 201
DIRTY_PRICE_INDEX = 202

SPECIAL_PRICES = [5_980_000, 6_020_000, 6_060_000, 6_100_000]
BAIT_PRICES = [5_280_000, 5_320_000, 5_980_000, 6_020_000, 6_060_000]
PRICE_JITTER = [0.0, 0.004, -0.003, 0.007, -0.006]


def community_of(index: int) -> str:
    return COMMUNITIES[index % len(COMMUNITIES)]


def layout_of(index: int) -> str:
    if index == SPECIAL_SPREAD_CLUSTER:
        return "3-2-1"
    return LAYOUTS[(index + index // len(COMMUNITIES)) % len(LAYOUTS)]


def _area_for(index: int, used: dict) -> float:
    community, layout = community_of(index), layout_of(index)
    group = (community, layout)
    used.setdefault(group, [])
    if index == SPECIAL_SPREAD_CLUSTER:
        used[group].append(89.5)
        return 89.5
    slot = 1
    area = 62.0 + 15.0 * slot
    while any(abs(area - taken) <= 6.0 for taken in used[group]):
        slot += 1
        area = 62.0 + 15.0 * slot
    used[group].append(area)
    return area


def base_price(community_index: int, layout: str, area: float, member_index: int) -> int:
    rooms = int(layout.split("-")[0])
    unit = 42000 + (community_index % 7) * 2600 + (rooms - 2) * 1200
    raw = area * unit * (1 + PRICE_JITTER[member_index % len(PRICE_JITTER)])
    return int(round(raw / 10000.0)) * 10000


def build_listings() -> tuple[list[dict], list[dict]]:
    """返回 (clusters, listings)；clusters 里带 golden 期望值，便于测试断言。"""
    clusters: list[dict] = []
    used_areas: dict = {}
    slot = 0
    for index, size in enumerate(CLUSTER_SIZES):
        community = community_of(index)
        layout = layout_of(index)
        area = _area_for(index, used_areas)
        floor_total = [18, 11, 26, 33, 6][index % 5]
        floor = 2 + (index * 5) % max(1, floor_total - 2)
        orientation = ORIENTATION_CYCLE[index % len(ORIENTATION_CYCLE)]

        if index == SPECIAL_SPREAD_CLUSTER:
            prices = list(SPECIAL_PRICES)
        elif index == BAIT_CLUSTER:
            prices = list(BAIT_PRICES)
        else:
            prices = [max(60_000, base_price(index % len(COMMUNITIES), layout, area, member)) for member in range(size)]

        members: list[dict] = []
        for member in range(size):
            agency = AGENCIES[slot % len(AGENCIES)]
            lid = f"{agency['code'].upper()}-{slot // len(AGENCIES) + 1:04d}"
            price = prices[member]
            area_text = f"{area:g}"
            area_raw = AREA_VARIANTS[slot % len(AREA_VARIANTS)].format(a=area_text, inner=f"{area * 0.8:.1f}")
            price_raw = PRICE_VARIANTS[slot % len(PRICE_VARIANTS)].format(w=price // 10000, yuan=f"{price:,}")
            floor_raw_variants = [f"{floor}/{floor_total}", f"{floor}层/共{floor_total}层", f"{floor}层", f"{floor}/{floor_total}"]
            if floor <= 6 and slot % 5 == 4:
                floor_raw = f"低楼层(共{floor_total}层)"
            else:
                floor_raw = floor_raw_variants[slot % len(floor_raw_variants)]
            orientation_raw = ORIENTATION_VARIANTS[orientation][slot % len(ORIENTATION_VARIANTS[orientation])]
            layout_raw = (
                layout
                if slot % 3 == 0
                else f"{layout.split('-')[0]}室{layout.split('-')[1]}厅{layout.split('-')[2]}卫"
                if slot % 3 == 1
                else LAYOUT_CN[layout]
            )
            title = f"{layout} {area_text}平方米 {orientation} {floor}层 {TITLE_SUFFIX[slot % len(TITLE_SUFFIX)]}"

            listed_days = 20 + (slot * 13) % 130
            views = 1 + (slot * 7) % 23
            status = "active"
            if slot % 19 == 5:
                status = "sold"
                listed_days = 150 + slot % 45
                views = 2 + slot % 9
            elif slot % 41 == 7:
                status = "off_market"

            if index in STALE_CLUSTER_INDEXES:
                listed_days = 220 + index % 40
                views = 0
            if index == DIRTY_FLOOR_INDEX:
                floor_raw = "暂无数据"
            if index == DIRTY_PRICE_INDEX:
                price_raw = "价格面议"

            members.append(
                {
                    "agency_code": agency["code"],
                    "lid": lid,
                    "community_raw": COMMUNITY_VARIANTS[slot % len(COMMUNITY_VARIANTS)].format(c=community),
                    "layout_raw": layout_raw,
                    "area_raw": area_raw,
                    "price_raw": price_raw,
                    "floor_raw": floor_raw,
                    "orientation_raw": orientation_raw,
                    "title": title,
                    "status": status,
                    "listed_days": listed_days,
                    "views": views,
                }
            )
            slot += 1

        clusters.append(
            {
                "index": index,
                "community": community,
                "layout": layout,
                "area": area,
                "floor": floor,
                "floor_total": floor_total,
                "orientation": orientation,
                "size": size,
                "prices": prices,
                "members": members,
            }
        )
    listings = [member for cluster in clusters for member in cluster["members"]]
    assert len(listings) == 540, len(listings)
    assert len(clusters) == 386, len(clusters)
    assert sum(1 for cluster in clusters if cluster["size"] > 1) == 41
    return clusters, listings


SEED_RUNS = [
    ("seed-run-baseline", "seed", "admin@listingmerge.io", 0.80),
    ("seed-run-analyst", "manual", "analyst@listingmerge.io", 0.80),
]

REVIEW_LIMIT = 6

# listingmerge · 多家中介二手房源重复挂牌归并

> 客户：安家数据 · 房源中台（7 人）。聚合 9 家中介的二手房挂牌，供 3 家银行做抵押估价参考。
> 现状：爬虫把 9 家挂牌原样入库，同一套房出现 3-5 次，估价师手动挑一条；
> 面积/楼层/朝向写法不一（`89.5㎡` / `89.5平米` / `建面89.5`），已成交未下架的僵尸挂牌还在拉低均价。

本系统把「采集 → 字段解析归一 → blocking → 相似度 → 并查集 → golden record → 风险分诊 → 复核 → 导出」串成一条可追溯链路：
同一套房只留一份主档（价格中位 / 面积众数 / 中介去重计数），
价格离群（钓鱼价）与超期无带看（僵尸挂牌）单独进复核队列，导出清单带全部算法读数。

## 1. 运行

```bash
cd batch-20261114/projects/gb-614
docker compose up -d --build          # 5 个服务全部 healthy（约 20-40s）
docker compose exec -T backend python -m scripts.seed_demo     # 幂等，可重复执行
docker compose exec -T backend python -m pytest tests -q
BASE_URL=http://localhost:18203 node ../../test-artifacts/gb-614/tests/smoke.mjs
BASE_URL=http://localhost:18203 node ../../test-artifacts/gb-614/tests/screenshots.cjs
docker compose down -v --remove-orphans
```

| 服务 | 端口 | 说明 |
| --- | --- | --- |
| frontend（Nginx 静态站） | 18203 | 原生 HTML/CSS/ES Modules，`/api` 反代到 backend 并剥掉前缀 |
| backend（FastAPI） | 19203 | 全部计算/校验/持久化 |
| db（MySQL 8.0） | 17703 | utf8mb4，启动时 `create_all` 建表 |
| redis | 内部 | Celery broker + worker 心跳 |
| worker（Celery） | 内部 | 10s 心跳 + 每日 07:40 全量重算（`service_healthy` 校验心跳） |

演示账号（密码 `Demo@2026`）：`admin@listingmerge.io` / `analyst@listingmerge.io` / `viewer@listingmerge.io`。

## 2. 五个领域实体

| 实体 | 表 | 作用 | 自然键 |
| --- | --- | --- | --- |
| Agency 中介渠道 | `agencies` | 9 家挂牌来源、采集入口与口径 | `code` |
| Listing 原始挂牌 | `listings` | 采集原文 + 归一结果 + 所属簇 | `(agency_id, lid)` |
| Property 房源簇 | `properties` | golden record：面积众数/价格中位/中介数/风险分 | `cluster_key`（成员挂牌哈希） |
| MatchRun 归并重算 | `match_runs` | 每次算法 A+B 的输入输出与耗时 | `run_no` / `seed_key` |
| Review 复核单 | `reviews` | 风险簇的人工结论（待复核/确认/驳回） | `seed_key` |

每个实体都贯穿：表 → `models/` → `schemas/` → `services/` → `controllers/` → `routes/` → 前端 `api.js` + 页面。

## 3. 业务模块表（6 个）

| 模块 | 页面 | services + controller | 主要 API |
| --- | --- | --- | --- |
| ① 中介与采集 | `#/agencies` 中介与采集 | `agency_service` + `controllers/agency_controller.py` | `GET/POST /api/agencies`、`GET/PATCH /api/agencies/{id}` |
| ② 字段解析归一 | `#/listings` 挂牌明细（原文 vs 归一） | `normalizer` + `listing_service` + `listing_controller.py` | `GET /api/listings`、`GET /api/listings/{id}` |
| ③ 分块与相似度 | `#/clusters` 归并簇（成员对照） | `entity_resolution`（blocking / similarity / UnionFind） | 由 `POST /api/runs` 驱动，读数见 `GET /api/runs/{id}` |
| ④ 聚类与 golden record | `#/clusters` 归并簇 | `entity_resolution.resolve` + `pipeline_service` + `property_service` + `property_controller.py` | `GET /api/properties`、`GET /api/properties/{id}`、`POST /api/runs` |
| ⑤ 风险与复核 | `#/reviews` 复核与导出 | `risk_rules` + `review_service` + `review_controller.py` | `GET /api/reviews`、`PATCH /api/reviews/{id}`、`GET /api/overview` |
| ⑥ 导出 | `#/reviews` 复核与导出 | `export_service` + `export_controller.py` | `GET /api/exports/{clusters,listings,reviews}.csv` |

横切能力（不计入业务模块）：登录 JWT（`auth_service` / `routes/auth.py`）、审计日志（`middlewares/audit_logger.py` + `audit_service` + `routes/audit.py`）、限流（`middlewares/rate_limit.py`）。

## 4. 两个算法（纯 Python，结果进页面与导出）

### 算法 A｜实体解析（`backend/src/services/entity_resolution.py`）

- **blocking**：同 `community_norm` + 同 `layout_norm` + 面积桶（5㎡ 一档，取同桶与相邻桶）且 `|Δ面积| ≤ 5㎡`；
- **相似度**：`0.35*area_close + 0.25*price_close + 0.20*floor_match + 0.10*orientation + 0.10*title_token`
  - `area_close = 1 − |Δa|/6`，`price_close = 1 − |Δp|/均值/0.30`（30% 价差处归零，跨中介报价天然差 1-3%），
    `floor_match` 同层 1.0 / 同区间 0.6，`orientation` 归一后相等 1.0，`title_token` = 标题字符二元组 Jaccard；
- **阈值 0.80 连边**，并查集 + 传递闭包；簇置信 = 簇内最大成对分（`max_pair_score`）；
- **golden record**：价格取簇内中位、面积取众数（并列取小）、中介数去重计数、价差 = p90 − p10。

### 算法 B｜僵尸与钓鱼挂牌识别（`backend/src/services/risk_rules.py`）

- 簇内价格离散度 `dispersion = (p90 − p10) / median`；`dispersion > 0.10` 打 `spread`；
- 挂牌价相对簇中位**低于 10% 以上** → `bait`（钓鱼价），同时落 `bait_lids`；
- 挂牌 **> 180 天且带看数为 0** → `stale`（僵尸挂牌），落 `stale_lids`；
- 风险分 `0-100 = 45*钓鱼 + 35*僵尸 + min(20, dispersion*200)`；`≥65` 高风险、`≥35` 中风险、`>0` 低风险、否则正常；
- 阈值常量集中在 `backend/src/constants/limits.py`，前端不复制任何算法结果。

## 5. 共享枚举出现位置

| 枚举组 | 后端 | 前端 |
| --- | --- | --- |
| 风险等级 `high/medium/low/none` | `constants/enums.py::RiskLevel` + `RISK_LEVEL_LABELS` | `js/config.js::ENUMS.riskLevel`、`riskTone()` |
| 风险标签 `bait/stale/spread` | `constants/enums.py::RiskTag` + `RISK_TAG_LABELS` | `js/config.js::ENUMS.riskTag`、`tagTone()` |
| 挂牌状态 `active/sold/off_market` | `constants/enums.py::ListingStatus` | `js/config.js::ENUMS.listingStatus`、`statusTone()` |
| 渠道类型 `broker/platform/feed` | `constants/enums.py::AgencyKind` | `js/config.js::ENUMS.agencyKind` |
| 复核状态/原因、运行状态、触发方式 | `enums.py::ReviewStatus/ReviewReason/RunStatus/TriggerKind` | `js/config.js::ENUMS.reviewStatus/reviewReason/runStatus/trigger` |
| 角色与权限点 | `constants/roles.py::PERMISSIONS` | `js/config.js::PERMISSIONS` + `can()` |

## 6. 页面（6 个）

1. `#/login` 登录 —— 橱窗房源贴：4 张挂牌便签（3 家原文 + 1 张已归并）。
2. `#/overview` 总览 —— 挂牌数 / 归并簇 / 去重率 / 风险簇四张价签 + 中介覆盖 + 风险台账 + 近 7 天重算。
3. `#/agencies` 中介与采集 —— 9 家渠道表 + 抽屉（采集口径、挂牌样例、暂停采集）+ 登记渠道。
4. `#/listings` 挂牌明细 —— 原文 → 归一 对照、归一标记、所属簇；按中介/状态/风险筛选。
5. `#/clusters` 归并簇 —— 簇列表（价差/成员/置信/风险）+ 抽屉（成员对照表、golden record、钓鱼/僵尸命中）+ 全量重算 + 运行历史。
6. `#/reviews` 复核与导出 —— 复核队列 + 复核结论表单 + 三种 CSV 导出 + 管理员审计日志。

共用组件：`ui.js` 的 `table` / `drawer` / `filter-bar` 在 3、4、5、6 四个页面复用；`badge`、`kv`、`emptyState` 全站复用。

## 7. seed 口径（幂等）

`backend/scripts/demo_config.py` 确定性生成：9 家中介 × 60 条 = **540 条挂牌**，覆盖 24 个小区、4 种户型；
原始写法随机混用 `㎡ / 平米 / 建面 / 建筑面积 / 平方米（套内…）`、`万 / 元 / 总价…万 / 万（可谈）`、`3/18 / 3层/共18层 / 低楼层(共18层)`；
含 2 条脏数据（楼层缺失、价格面议）。

跑完算法 A/B 后：**386 个房源簇**（41 个多成员簇，去重率 28.52%）、**6 个风险簇**（1 个钓鱼价簇含 2 条 bait、5 条僵尸挂牌）、**6 张待复核单**。
特别注意：`翠湖名邸 3-2-1 89.5㎡` 在 4 家中介交叉命中，价格 598/602/606/610 万，价差 12 万，中位 604 万。

seed 结束打印一行（连续两次逐字一致）：

```
SEED_SUMMARY brand=listingmerge users=3 sources=9 runs=2 findings=386 pending=6
```

## 8. 权限矩阵

| 能力 | admin | analyst | viewer |
| --- | --- | --- | --- |
| 读总览/挂牌/簇/复核 | ✅ | ✅ | ✅ |
| 登记/改中介渠道 | ✅ | ❌ 403 | ❌ 403 |
| 发起全量重算 | ✅ | ✅ | ❌ 403 |
| 提交复核结论 | ✅ | ✅ | ❌ 403 |
| 导出 CSV | ✅ | ✅ | ❌ 403 |
| 审计日志 | ✅ | ❌ 403 | ❌ 403 |

无 token 一律 401；非法参数 422；重复编码 409。

## 9. 目录

```
backend/src/{config,constants,controllers,middlewares,models,routes,schemas,services,utils}
backend/scripts/{seed_demo.py,demo_config.py,worker_healthcheck.sh}
backend/migrations/001_core_tables.sql   # DDL 参考（运行时由 create_all 建表）
frontend/site/{index.html,css/{tokens,app}.css,js/{config,api,store,ui,app}.js,js/pages/*.js}
docker-compose.yml  .env  README.md
```

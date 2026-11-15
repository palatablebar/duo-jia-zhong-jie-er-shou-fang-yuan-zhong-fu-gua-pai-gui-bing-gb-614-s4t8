/**
 * 项目品牌、导航、角色权限与枚举文案（前端唯一定义处）。
 * 后端对应：backend/src/constants/{roles,enums,limits}.py；README 列出全部出现位置。
 */
export const BRAND = {
  short: 'listingmerge',
  title: '多家中介二手房源重复挂牌归并',
  org: '安家数据 · 房源中台',
  edition: 'PROPERTY WINDOW · 2026',
  subtitle: '9 家中介的挂牌在这里合成一份 golden record：同一套房只留一条主档，价差与僵尸挂牌单独挑出来',
  loginLead: '估价师以前要在 4 条几乎一样的挂牌里挑一条，还得自己算价差。现在系统先把它们认成同一套房。',
  loginPoints: [
    ['01', '字段解析归一：89.5㎡ / 89.5平米 / 建面89.5 归一成同一个数字。'],
    ['02', 'blocking + 相似度 + 并查集：同小区同户型 ±5㎡ 内连边，阈值 0.80。'],
    ['03', 'golden record 取价格中位、面积众数、中介去重计数，风险簇进复核队列。'],
  ],
};

export const NAV = [
  { to: '#/overview', no: '01', label: '总览', permission: 'overview:read' },
  { to: '#/agencies', no: '02', label: '中介与采集', permission: 'agency:read' },
  { to: '#/listings', no: '03', label: '挂牌明细', permission: 'listing:read' },
  { to: '#/clusters', no: '04', label: '归并簇', permission: 'property:read' },
  { to: '#/reviews', no: '05', label: '复核与导出', permission: 'review:read' },
];

export const ROLE_LABELS = {
  admin: '平台管理员',
  analyst: '数据专员',
  viewer: '业务只读',
};

export const PERMISSIONS = {
  admin: [
    'overview:read', 'agency:read', 'agency:write', 'listing:read', 'property:read',
    'run:read', 'run:create', 'review:read', 'review:write', 'export:read', 'audit:read',
  ],
  analyst: [
    'overview:read', 'agency:read', 'listing:read', 'property:read',
    'run:read', 'run:create', 'review:read', 'review:write', 'export:read',
  ],
  viewer: ['overview:read', 'agency:read', 'listing:read', 'property:read', 'run:read', 'review:read'],
};

export const ENUMS = {
  riskLevel: { high: '高风险', medium: '中风险', low: '低风险', none: '正常' },
  riskTag: { bait: '钓鱼价', stale: '僵尸挂牌', spread: '价格离散' },
  listingStatus: { active: '在售', sold: '已成交未下架', off_market: '已下架' },
  agencyKind: { broker: '中介门店', platform: '信息平台', feed: '数据服务商' },
  runStatus: { queued: '排队中', running: '执行中', success: '成功', partial: '部分成功', failed: '失败' },
  reviewStatus: { pending: '待复核', confirmed: '已确认', dismissed: '已驳回' },
  reviewReason: { bait: '疑似钓鱼价', stale: '疑似僵尸挂牌', spread: '簇内价差异常', manual: '人工抽查' },
  trigger: { manual: '手动', schedule: '定时', seed: '初始化' },
};

export function can(role, permission) {
  return (PERMISSIONS[role] || []).includes(permission);
}

export function riskTone(level) {
  return { high: 'danger', medium: 'warn', low: 'ok', none: '' }[level] ?? '';
}

export function statusTone(status) {
  return { active: 'ok', sold: 'warn', off_market: '' }[status] ?? '';
}

export function reviewTone(status) {
  return { pending: 'warn', confirmed: 'ok', dismissed: 'danger' }[status] || '';
}

export function tagTone(tag) {
  return { bait: 'danger', stale: 'warn', spread: 'info' }[tag] || '';
}

/** 金额（元）-> 万元展示，保留一位小数以内。 */
export function wan(value) {
  const num = Number(value || 0);
  if (!num) return '—';
  return `${(num / 10000).toFixed(num % 10000 === 0 ? 0 : 1)} 万`;
}

/** 0..1 比率 -> 百分比字符串。 */
export function pct(value, digits = 1) {
  return `${(Number(value || 0) * 100).toFixed(digits)}%`;
}

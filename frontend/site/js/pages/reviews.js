import { api } from '../api.js';
import { ENUMS, can, pct, riskTone, reviewTone, tagTone, wan } from '../config.js';
import { badge, drawer, errorBox, errorMessage, esc, field, fmtTime, kv, table, toast } from '../ui.js';

const state = { status: 'pending', reason: '', severity: '' };

function openReview(view, ctx, item) {
  const editable = can(ctx.user.role, 'review:write');
  const prop = item.property || {};
  const { root, close } = drawer({
    title: `${prop.community || ''} · ${prop.layout || ''}`,
    subtitle: `复核单 #${item.id} · ${item.reason_label} · 风险分 ${item.risk_score}`,
    body: `${kv([
      ['簇', `<span class="mono">#${esc(item.property_id)}</span>`],
      ['面积 / 价格中位', `<span class="mono">${esc(prop.area_mode)} ㎡ · ${esc(wan(prop.price_median))}</span>`],
      ['成员 / 中介', `${esc(prop.member_count)} 条 / ${esc(prop.agency_count)} 家`],
      ['价差', `<span class="mono">${esc(wan(prop.spread))}</span>`],
      ['风险等级', badge(riskTone(item.severity), item.severity_label)],
      ['风险标签', (prop.risk_tags || []).map((tag) => `<span class="badge ${tagTone(tag)}">${esc(ENUMS.riskTag[tag] || tag)}</span>`).join(' ') || '—'],
      ['复核状态', badge(reviewTone(item.status), item.status_label)],
      ['复核人', esc(item.reviewer || '—')],
      ['结论备注', esc(item.note || '—')],
      ['创建时间', fmtTime(item.created_at)],
    ])}
    <p class="note">确认后该簇的风险标签进入归档结论；驳回表示算法判断不成立，会留痕但不改簇内数据。</p>`,
    footer: editable
      ? `<form id="review-form" style="display:grid;gap:10px">
          ${field({ label: '复核结论', name: 'status', value: item.status, options: Object.entries(ENUMS.reviewStatus).map(([value, label]) => ({ value, label })) })}
          ${field({ label: '备注', name: 'note', value: item.note || '', placeholder: '写一句判定依据，例如：确认 5.28 万/㎡ 为中介钓鱼价' })}
          <button class="btn accent" type="submit">提交复核</button>
        </form>`
      : '<span class="mono muted">只读角色可以查看复核单，但不能提交结论</span>',
  });
  root.querySelector('#review-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.target;
    try {
      await api.patch(`/api/reviews/${item.id}`, {
        status: form.status.value,
        note: form.note.value.trim() || null,
      });
      toast('复核结论已保存');
      close();
      await reviewsPage.render(view, ctx);
    } catch (err) {
      toast(errorMessage(err), 'err');
    }
  });
}

async function auditPanel(view, ctx) {
  const node = view.querySelector('#audit-body');
  if (!node) return;
  try {
    const data = await api.get('/api/audit', { limit: 40 });
    node.innerHTML = table({
      rows: data.items,
      columns: [
        { key: 'created_at', label: '时间', render: (row) => fmtTime(row.created_at) },
        { key: 'actor_email', label: '操作人', className: 'mono' },
        { key: 'action_label', label: '动作' },
        { key: 'entity', label: '对象' },
        { key: 'layer', label: '层', render: (row) => `<span class="chip">${esc(row.layer)}</span>` },
        { key: 'detail', label: '详情', render: (row) => `<span class="mono muted">${esc(JSON.stringify(row.detail || {}))}</span>` },
      ],
      empty: { title: '还没有审计记录', hint: '登录、重算、复核都会留痕。' },
    });
    node.querySelectorAll('table.data').forEach((el) => el.classList.add('compact'));
  } catch (err) {
    node.innerHTML = `<p class="note">${esc(errorMessage(err))}</p>`;
  }
}

export const reviewsPage = {
  async render(view, ctx) {
    let data;
    let overview;
    try {
      [data, overview] = await Promise.all([
        api.get('/api/reviews', { status: state.status, reason: state.reason, severity: state.severity, limit: 50 }),
        api.get('/api/overview'),
      ]);
    } catch (err) {
      view.innerHTML = errorBox(errorMessage(err));
      view.querySelector('#retry-btn')?.addEventListener('click', () => reviewsPage.render(view, ctx));
      return;
    }
    const canExport = can(ctx.user.role, 'export:read');
    view.innerHTML = `
      <section class="panel">
        <div class="panel-head">
          <h2>复核队列</h2>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
            <span class="meta">${data.total} 张</span>
            ${
              canExport
                ? `<button class="btn sm ghost" id="export-reviews">复核 CSV</button>
                   <button class="btn sm ghost" id="export-listings">挂牌 CSV</button>
                   <button class="btn sm ghost accent" id="export-clusters">归并簇 CSV</button>`
                : '<span class="mono muted">只读角色不能导出</span>'
            }
          </div>
        </div>
        <div class="panel-body">
          <div class="filter-bar" id="review-filters">
            ${field({ label: '状态', name: 'status', value: state.status, options: [{ value: '', label: '全部' }, ...Object.entries(ENUMS.reviewStatus).map(([value, label]) => ({ value, label }))] })}
            ${field({ label: '原因', name: 'reason', value: state.reason, options: [{ value: '', label: '全部' }, ...Object.entries(ENUMS.reviewReason).map(([value, label]) => ({ value, label }))] })}
            ${field({ label: '风险等级', name: 'severity', value: state.severity, options: [{ value: '', label: '全部' }, ...Object.entries(ENUMS.riskLevel).map(([value, label]) => ({ value, label }))] })}
          </div>
        </div>
        ${table({
          rows: data.items,
          columns: [
            { key: 'id', label: '复核单', className: 'mono', render: (row) => `#${esc(row.id)}` },
            { key: 'community', label: '小区 / 户型', render: (row) => `<b>${esc((row.property || {}).community || '')}</b><div class="mono muted">${esc((row.property || {}).layout || '')} · 簇 #${esc(row.property_id)}</div>` },
            { key: 'risk_score', label: '风险分', className: 'num', render: (row) => `${esc(row.risk_score)}` },
            { key: 'severity', label: '等级', render: (row) => badge(riskTone(row.severity), row.severity_label) },
            { key: 'reason_label', label: '原因' },
            { key: 'property', label: '价差', className: 'num', render: (row) => esc(wan((row.property || {}).spread)) },
            { key: 'status', label: '状态', render: (row) => badge(reviewTone(row.status), row.status_label) },
            { key: 'reviewer', label: '复核人', render: (row) => esc(row.reviewer || '—') },
          ],
          empty: { title: '这个筛选下没有复核单', hint: '换成「全部」看看，或先跑一次归并。' },
        })}
      </section>

      ${
        canExport
          ? `<section class="panel">
              <div class="panel-head"><h2>导出与口径</h2><span class="meta">CSV · UTF-8 BOM</span></div>
              <div class="panel-body" style="display:grid;gap:10px">
                <p class="note">归并簇 CSV 含面积众数、价格中位、价差、离散度、风险分与两个算法命中的挂牌编号；挂牌明细 CSV 同时保留采集原文与归一结果，方便银行侧复核口径。</p>
                <div class="kv">
                  <dt>挂牌数</dt><dd class="mono">${esc(overview.listing_total)} 条</dd>
                  <dt>归并簇</dt><dd class="mono">${esc(overview.cluster_total)} 个（多成员 ${esc(overview.multi_cluster_total)}）</dd>
                  <dt>去重率</dt><dd class="mono">${esc(pct(overview.dedup_rate))}</dd>
                  <dt>风险簇</dt><dd class="mono">${esc(overview.risk_total)} 个 · 待复核 ${esc(overview.pending_total)} 张</dd>
                </div>
              </div>
            </section>`
          : ''
      }

      ${
        can(ctx.user.role, 'audit:read')
          ? `<details class="audit-fold" id="audit-fold">
              <summary>审计日志（管理员可见，最近 40 条）</summary>
              <div class="panel-body" id="audit-body"><span class="muted">展开后加载…</span></div>
            </details>`
          : ''
      }`;

    const filters = view.querySelector('#review-filters');
    filters?.addEventListener('change', () => {
      state.status = filters.querySelector('[name=status]').value;
      state.reason = filters.querySelector('[name=reason]').value;
      state.severity = filters.querySelector('[name=severity]').value;
      reviewsPage.render(view, ctx);
    });
    view.querySelectorAll('table.data tbody tr').forEach((row) => {
      row.addEventListener('click', () => {
        const item = data.items.find((entry) => String(entry.id) === row.dataset.id);
        if (item) openReview(view, ctx, item);
      });
    });
    const download = async (path, filename, label) => {
      try {
        await api.download(path, filename);
        toast(`已开始下载${label}`);
      } catch (err) {
        toast(errorMessage(err), 'err');
      }
    };
    view.querySelector('#export-clusters')?.addEventListener('click', () => download('/api/exports/clusters.csv', 'clusters.csv', '归并簇清单'));
    view.querySelector('#export-listings')?.addEventListener('click', () => download('/api/exports/listings.csv', 'listings.csv', '挂牌明细'));
    view.querySelector('#export-reviews')?.addEventListener('click', () => download('/api/exports/reviews.csv', 'reviews.csv', '复核单'));
    const fold = view.querySelector('#audit-fold');
    fold?.addEventListener('toggle', () => {
      if (fold.open) auditPanel(view, ctx);
    });
  },
};

export default reviewsPage;

import { api } from '../api.js';
import { ENUMS, riskTone, statusTone, tagTone, wan } from '../config.js';
import { drawer, errorBox, errorMessage, esc, field, fmtTime, kv, table } from '../ui.js';

const state = { q: '', agencyId: '', status: '', risk: '', propertyId: '' };

function pairCell(raw, norm) {
  return `<div class="pair"><span class="raw">${esc(raw)}</span><span class="arrow">→</span><span class="norm">${esc(norm)}</span></div>`;
}

function openListing(view, ctx, item) {
  const flags = item.parse_flags || [];
  const { root } = drawer({
    title: `${item.community_raw.trim()} · ${item.layout_raw}`,
    subtitle: `${item.lid} · ${item.agency_name} · ${fmtTime(item.captured_at)}`,
    body: `${kv([
      ['小区', `${pairCell(item.community_raw, item.norm.community)}`],
      ['户型', `${pairCell(item.layout_raw, item.norm.layout)}`],
      ['面积', `${pairCell(item.area_raw, item.norm.area === null ? '（无法解析）' : `${item.norm.area} ㎡`)}`],
      ['价格', `${pairCell(item.price_raw, item.norm.price ? wan(item.norm.price) : '（无法解析）')}`],
      ['楼层', `${pairCell(item.floor_raw, item.norm.floor ? `${item.norm.floor}/${item.norm.floor_total || '?'} · ${item.norm.floor_band}` : '（仅区间 / 缺失）')}`],
      ['朝向', `${pairCell(item.orientation_raw, item.norm.orientation || '—')}`],
      ['挂牌状态', `<span class="badge ${statusTone(item.status)}">${esc(item.status_label)}</span>`],
      ['挂牌天数 / 带看', `<span class="mono">${esc(item.listed_days)} 天 · ${esc(item.views)} 次</span>`],
      ['所属簇', item.property_id ? `<span class="mono">#${esc(item.property_id)} ${esc(item.property_community || '')} ${esc(item.property_layout || '')}</span>` : '未入簇'],
      ['风险标签', (item.risk_tags || []).length ? item.risk_tags.map((tag) => `<span class="badge ${tagTone(tag)}">${esc(ENUMS.riskTag[tag] || tag)}</span>`).join(' ') : '—'],
    ])}
    <h3 style="margin:14px 0 8px;font-size:0.95rem">归一标记</h3>
    <div class="chips">${
      flags.length ? flags.map((flag) => `<span class="chip flag">${esc(flag)}</span>`).join('') : '<span class="chip">无（字段规整）</span>'
    }</div>
    <h3 style="margin:14px 0 8px;font-size:0.95rem">标题与切词</h3>
    <p class="note">${esc(item.title)}</p>
    <div class="chips" style="margin-top:8px">${(item.norm.title_tokens || [])
      .slice(0, 18)
      .map((token) => `<span class="chip">${esc(token)}</span>`)
      .join('')}</div>`,
    footer: item.property_id
      ? `<button class="btn accent" data-cluster>查看归并簇 #${esc(item.property_id)}</button>`
      : '<span class="mono muted">该挂牌尚未进入任何簇</span>',
  });
  root.querySelector('[data-cluster]')?.addEventListener('click', () => {
    ctx.navigate(`#/clusters?focus=${item.property_id}`);
  });
}

export const listingsPage = {
  async render(view, ctx) {
    if (ctx.query.agency_id) state.agencyId = ctx.query.agency_id;
    if (ctx.query.risk) state.risk = ctx.query.risk;
    if (ctx.query.property_id) state.propertyId = ctx.query.property_id;
    let data;
    let agencies;
    try {
      [data, agencies] = await Promise.all([
        api.get('/api/listings', {
          q: state.q,
          agency_id: state.agencyId,
          status: state.status,
          risk: state.risk,
          property_id: state.propertyId,
          limit: 50,
        }),
        api.get('/api/agencies', { limit: 50 }),
      ]);
    } catch (err) {
      view.innerHTML = errorBox(errorMessage(err));
      view.querySelector('#retry-btn')?.addEventListener('click', () => listingsPage.render(view, ctx));
      return;
    }
    view.innerHTML = `
      <section class="panel">
        <div class="panel-head">
          <h2>挂牌明细 <span class="mono muted">· 原文 vs 归一</span></h2>
          <div style="display:flex;gap:8px;align-items:center">
            <span class="meta">${data.total} 条${state.propertyId ? ` · 簇 #${esc(state.propertyId)}` : ''}</span>
            ${
              state.propertyId
                ? '<button class="btn sm ghost" id="clear-cluster">看全部挂牌</button>'
                : ''
            }
          </div>
        </div>
        <div class="panel-body">
          <div class="filter-bar" id="listing-filters">
            ${field({ label: '搜索', name: 'q', value: state.q, placeholder: '小区 / 编号 / 标题' })}
            ${field({ label: '中介', name: 'agency_id', value: state.agencyId, options: [{ value: '', label: '全部' }, ...agencies.items.map((item) => ({ value: item.id, label: item.name }))] })}
            ${field({ label: '挂牌状态', name: 'status', value: state.status, options: [{ value: '', label: '全部' }, ...Object.entries(ENUMS.listingStatus).map(([value, label]) => ({ value, label }))] })}
            ${field({ label: '风险', name: 'risk', value: state.risk, options: [{ value: '', label: '全部' }, { value: 'bait', label: '钓鱼价' }, { value: 'stale', label: '僵尸挂牌' }, { value: 'none', label: '无标签' }] })}
          </div>
        </div>
        ${table({
          rows: data.items,
          columns: [
            { key: 'lid', label: '挂牌编号', className: 'mono' },
            { key: 'agency_name', label: '中介', render: (row) => esc(row.agency_name) },
            { key: 'community', label: '小区', render: (row) => pairCell(row.community_raw, row.norm.community) },
            { key: 'area', label: '面积', render: (row) => pairCell(row.area_raw, row.norm.area === null ? '—' : `${row.norm.area}㎡`) },
            { key: 'price', label: '价格', render: (row) => pairCell(row.price_raw, row.norm.price ? wan(row.norm.price) : '—') },
            { key: 'floor', label: '楼层', render: (row) => pairCell(row.floor_raw, row.norm.floor ? `${row.norm.floor}/${row.norm.floor_total || '?'} 层` : '仅区间') },
            { key: 'status', label: '状态', render: (row) => `<span class="badge ${statusTone(row.status)}">${esc(row.status_label)}</span>` },
            {
              key: 'risk_tags',
              label: '风险',
              render: (row) =>
                (row.risk_tags || []).length
                  ? row.risk_tags.map((tag) => `<span class="badge ${tagTone(tag)}">${esc(ENUMS.riskTag[tag] || tag)}</span>`).join(' ')
                  : `<span class="muted">${row.property_risk_level ? esc(ENUMS.riskLevel[row.property_risk_level] || '') : '—'}</span>`,
            },
          ],
          empty: { title: '没有匹配的挂牌', hint: '换个中介或风险筛选再看。' },
        })}
      </section>`;

    const filters = view.querySelector('#listing-filters');
    filters?.addEventListener('change', () => {
      state.q = filters.querySelector('[name=q]').value.trim();
      state.agencyId = filters.querySelector('[name=agency_id]').value;
      state.status = filters.querySelector('[name=status]').value;
      state.risk = filters.querySelector('[name=risk]').value;
      state.propertyId = '';
      listingsPage.render(view, ctx);
    });
    filters?.querySelector('[name=q]')?.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        state.q = event.target.value.trim();
        state.propertyId = '';
        listingsPage.render(view, ctx);
      }
    });
    view.querySelector('#clear-cluster')?.addEventListener('click', () => {
      state.propertyId = '';
      listingsPage.render(view, ctx);
    });
    view.querySelectorAll('table.data tbody tr').forEach((row) => {
      row.addEventListener('click', () => {
        const item = data.items.find((entry) => String(entry.id) === row.dataset.id);
        if (item) openListing(view, ctx, item);
      });
    });
  },
};

export default listingsPage;

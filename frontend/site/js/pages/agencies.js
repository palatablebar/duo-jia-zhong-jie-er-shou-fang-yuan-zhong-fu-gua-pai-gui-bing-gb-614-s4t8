import { api } from '../api.js';
import { ENUMS, can, statusTone } from '../config.js';
import { drawer, errorBox, errorMessage, esc, field, fmtTime, kv, table, toast } from '../ui.js';

const state = { q: '', kind: '', enabled: '' };

function openAgency(view, ctx, agency) {
  const editable = can(ctx.user.role, 'agency:write');
  const { root, close } = drawer({
    title: agency.name,
    subtitle: `${agency.code} · ${agency.kind_label} · 挂牌 ${agency.listing_count} 条`,
    body: `${kv([
      ['接入方式', esc(agency.kind_label)],
      ['采集入口', agency.endpoint ? `<span class="mono">${esc(agency.endpoint)}</span>` : '—'],
      ['负责人', esc(agency.owner)],
      ['状态', statusBadge(agency)],
      ['最近采集', fmtTime(agency.last_listing_at || agency.last_synced_at)],
      ['采集口径', `<span class="mono">${esc(JSON.stringify(agency.config || {}))}</span>`],
      ['备注', esc(agency.note || '—')],
    ])}
    <h3 style="margin:14px 0 8px;font-size:0.95rem">该渠道的挂牌样例</h3>
    <div id="agency-samples" class="members"><div class="empty"><div class="mark">读取中…</div></div></div>`,
    footer: editable
      ? `<button class="btn ghost" data-toggle>${agency.enabled ? '暂停采集' : '恢复采集'}</button>`
      : '<span class="mono muted">只读角色只能查看渠道信息</span>',
  });
  api
    .get('/api/listings', { agency_id: agency.id, limit: 5 })
    .then((data) => {
      const node = root.querySelector('#agency-samples');
      if (!node) return;
      node.innerHTML = table({
        rows: data.items,
        columns: [
          { key: 'lid', label: '编号', className: 'mono' },
          { key: 'community_raw', label: '小区原文', render: (row) => esc(row.community_raw) },
          { key: 'area_raw', label: '面积原文', className: 'mono' },
          { key: 'price_raw', label: '价格原文', className: 'mono' },
          { key: 'status', label: '状态', render: (row) => `<span class="badge ${statusTone(row.status)}">${esc(ENUMS.listingStatus[row.status] || row.status)}</span>` },
        ],
        empty: { title: '该渠道还没有挂牌', hint: '等采集器跑一轮，或检查入口是否可用。' },
      });
      node.querySelectorAll('table.data').forEach((el) => el.classList.add('compact'));
    })
    .catch(() => {
      const node = root.querySelector('#agency-samples');
      if (node) node.innerHTML = '<div class="empty"><div class="mark">样例读取失败</div></div>';
    });
  root.querySelector('[data-toggle]')?.addEventListener('click', async () => {
    try {
      await api.patch(`/api/agencies/${agency.id}`, { enabled: !agency.enabled });
      toast(agency.enabled ? '已暂停该渠道采集' : '已恢复该渠道采集');
      close();
      await agenciesPage.render(view, ctx);
    } catch (err) {
      toast(errorMessage(err), 'err');
    }
  });
}

function statusBadge(agency) {
  return agency.enabled ? '<span class="badge ok">采集中</span>' : '<span class="badge">已暂停</span>';
}

function openCreate(view, ctx) {
  const { root, close } = drawer({
    title: '登记中介渠道',
    subtitle: '登记后采集器按这份口径入库，归并重算时一并参与',
    body: `<form id="agency-form" style="display:grid;gap:12px">
      ${field({ label: '编码（小写字母 / 数字 / -）', name: 'code', placeholder: 'xinfang' })}
      ${field({ label: '名称', name: 'name', placeholder: '例如：信义房屋 · 花木店' })}
      ${field({ label: '接入方式', name: 'kind', value: 'broker', options: Object.entries(ENUMS.agencyKind).map(([value, label]) => ({ value, label })) })}
      ${field({ label: '采集入口', name: 'endpoint', placeholder: 'https://…' })}
      ${field({ label: '备注', name: 'note', placeholder: '字段口径 / 采集频率' })}
      <div class="form-error" id="agency-error"></div>
      <button class="btn accent" type="submit">保存渠道</button>
    </form>`,
  });
  root.querySelector('#agency-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.target;
    try {
      await api.post('/api/agencies', {
        code: form.code.value.trim(),
        name: form.name.value.trim(),
        kind: form.kind.value,
        endpoint: form.endpoint.value.trim() || null,
        note: form.note.value.trim() || null,
        config: { crawl: 'manual' },
      });
      toast('渠道已登记');
      close();
      await agenciesPage.render(view, ctx);
    } catch (err) {
      root.querySelector('#agency-error').textContent =
        err.code === 'CONFLICT' ? '编码已存在，请换一个' : errorMessage(err);
    }
  });
}

export const agenciesPage = {
  async render(view, ctx) {
    let data;
    try {
      data = await api.get('/api/agencies', { q: state.q, kind: state.kind, enabled: state.enabled, limit: 50 });
    } catch (err) {
      view.innerHTML = errorBox(errorMessage(err));
      view.querySelector('#retry-btn')?.addEventListener('click', () => agenciesPage.render(view, ctx));
      return;
    }
    const totalListings = data.items.reduce((sum, item) => sum + item.listing_count, 0);
    view.innerHTML = `
      <section class="panel">
        <div class="panel-head">
          <h2>中介与采集</h2>
          <div style="display:flex;gap:8px;align-items:center">
            <span class="meta">${data.total} 家 · ${totalListings} 条挂牌</span>
            ${can(ctx.user.role, 'agency:write') ? '<button class="btn sm accent" id="new-agency">登记渠道</button>' : ''}
          </div>
        </div>
        <div class="panel-body">
          <div class="filter-bar" id="agency-filters">
            ${field({ label: '搜索', name: 'q', value: state.q, placeholder: '名称 / 编码' })}
            ${field({ label: '接入方式', name: 'kind', value: state.kind, options: [{ value: '', label: '全部' }, ...Object.entries(ENUMS.agencyKind).map(([value, label]) => ({ value, label }))] })}
            ${field({ label: '状态', name: 'enabled', value: state.enabled, options: [{ value: '', label: '全部' }, { value: 'true', label: '采集中' }, { value: 'false', label: '已暂停' }] })}
          </div>
        </div>
        ${table({
          rows: data.items,
          columns: [
            { key: 'name', label: '中介 / 渠道', render: (row) => `<b>${esc(row.name)}</b><div class="mono muted">${esc(row.code)}</div>` },
            { key: 'kind_label', label: '接入方式' },
            { key: 'endpoint', label: '采集入口', render: (row) => `<span class="mono muted">${esc(row.endpoint || '—')}</span>` },
            { key: 'listing_count', label: '挂牌数', className: 'num' },
            { key: 'last_listing_at', label: '最近采集', render: (row) => fmtTime(row.last_listing_at || row.last_synced_at) },
            { key: 'enabled', label: '状态', render: (row) => statusBadge(row) },
          ],
          empty: { title: '还没有中介渠道', hint: '管理员可以登记第一家渠道。' },
        })}
      </section>`;
    const filters = view.querySelector('#agency-filters');
    filters?.addEventListener('change', () => {
      state.q = filters.querySelector('[name=q]').value.trim();
      state.kind = filters.querySelector('[name=kind]').value;
      state.enabled = filters.querySelector('[name=enabled]').value;
      agenciesPage.render(view, ctx);
    });
    filters?.querySelector('[name=q]')?.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        state.q = event.target.value.trim();
        agenciesPage.render(view, ctx);
      }
    });
    view.querySelectorAll('table.data tbody tr').forEach((row) => {
      row.addEventListener('click', () => {
        const item = data.items.find((entry) => String(entry.id) === row.dataset.id);
        if (item) openAgency(view, ctx, item);
      });
    });
    view.querySelector('#new-agency')?.addEventListener('click', () => openCreate(view, ctx));
  },
};

export default agenciesPage;

import { api } from '../api.js';
import { ENUMS, pct, riskTone, wan } from '../config.js';
import { barList, badge, emptyState, errorBox, errorMessage, esc, fmtTime, trendChart } from '../ui.js';

function heroTags(data) {
  return `<div class="hero-tags">
    <div class="price-tag">
      <span class="k">挂牌原文</span>
      <span class="v" data-testid="listing-total">${esc(data.listing_total)}</span>
      <span class="hint">${esc(data.agency_total)} 家中介的原始挂牌条数</span>
    </div>
    <div class="price-tag alt">
      <span class="k">归并后的房源</span>
      <span class="v" data-testid="cluster-total">${esc(data.cluster_total)}</span>
      <span class="hint">多成员簇 ${esc(data.multi_cluster_total)} 个 · 其余为独挂</span>
    </div>
    <div class="price-tag">
      <span class="k">去重率</span>
      <span class="v" data-testid="dedup-rate">${esc(pct(data.dedup_rate))}</span>
      <span class="hint">1 − 簇数 / 挂牌数（算法 A 计算）</span>
    </div>
    <div class="price-tag alt">
      <span class="k">风险簇 / 待复核</span>
      <span class="v" data-testid="risk-total">${esc(data.risk_total)}</span>
      <span class="hint">待复核 ${esc(data.pending_total)} 张 · 算法 B 分诊</span>
    </div>
  </div>`;
}

function coverage(data) {
  const max = Math.max(1, ...data.agencies.map((item) => item.listing_count));
  return `<div class="coverage">${data.agencies
    .map(
      (item) => `<div class="coverage-row">
        <span class="name" title="${esc(item.name)}">${esc(item.name)}</span>
        <div class="track"><div class="fill" style="width:${Math.round((item.listing_count / max) * 100)}%"></div></div>
        <span class="mono" style="text-align:right">${esc(item.listing_count)}</span>
      </div>`,
    )
    .join('')}</div>`;
}

function ledger(items) {
  if (!items.length) return emptyState({ title: '台账空着', hint: '跑一次归并重算就会有数字。' });
  const max = Math.max(1, ...items.map((item) => item.count));
  return `<div class="ledger">${items
    .map(
      (item) => `<div class="ledger-row">
        <span>${esc(item.label)}</span>
        <div class="track" style="height:8px;background:var(--paper-3);border-radius:999px;overflow:hidden">
          <div style="height:100%;width:${Math.round((item.count / max) * 100)}%;background:var(--accent-soft)"></div>
        </div>
        <span class="count">${esc(item.count)}</span>
      </div>`,
    )
    .join('')}</div>`;
}

export const overviewPage = {
  async render(view, ctx) {
    view.innerHTML = '<div class="empty"><div class="mark">读取台账…</div></div>';
    let data;
    try {
      data = await api.get('/api/overview');
    } catch (err) {
      view.innerHTML = errorBox(errorMessage(err));
      view.querySelector('#retry-btn')?.addEventListener('click', () => overviewPage.render(view, ctx));
      return;
    }
    const latest = data.latest_run;
    view.innerHTML = `
      <section class="hero">
        <div class="hero-top">
          <div>
            <div class="eyebrow">今日橱窗 · ${esc(ctx.user.display_name)}</div>
            <h2>一份主档，九家挂牌</h2>
          </div>
          <div class="hero-note">
            <p style="margin:0 0 6px">${
              latest
                ? `最近一次重算 <span class="mono">${esc(latest.run_no)}</span>（阈值 ${esc(latest.threshold)}）：簇内价格中位 <b>${esc(wan(data.unit_price_median))}/㎡</b> 级别的口径已刷新，${esc(latest.multi_count)} 个多成员簇合并了重复挂牌。`
                : '还没有归并记录，去「归并簇」发起一次全量重算。'
            }</p>
            <p class="note">算法 A 连边阈值 0.80；算法 B 用 (p90−p10)/中位 判价格离散，低于中位 10% 记钓鱼价、挂牌超 180 天且 0 带看记僵尸挂牌。</p>
          </div>
        </div>
        ${heroTags(data)}
      </section>

      <div class="grid-2">
        <section class="panel">
          <div class="panel-head"><h2>中介覆盖</h2><span class="meta">${esc(data.agency_total)} 家中介 · 每家 60 条</span></div>
          <div class="panel-body">${coverage(data)}</div>
        </section>
        <section class="panel">
          <div class="panel-head"><h2>风险台账</h2><span class="meta">算法 B</span></div>
          <div class="panel-body" style="display:grid;gap:12px">
            ${
              data.risk_levels.length
                ? ledger(data.risk_levels.filter((item) => item.key !== 'none' || data.risk_levels.length === 1))
                : emptyState({ title: '还没有风险结果', hint: '重算后风险簇会出现在这里。' })
            }
            <div class="chips">
              ${(data.risk_tags.length ? data.risk_tags : [])
                .map((tag) => `<span class="chip tag">${esc(tag.label)} ${esc(tag.count)}</span>`)
                .join('') || '<span class="chip">暂无风险标签</span>'}
            </div>
            <div class="step" style="display:flex;justify-content:space-between;align-items:center;gap:10px">
              <span class="muted" style="font-size:var(--fs-sm)">待复核 ${esc(data.pending_total)} 张</span>
              <button class="btn sm ghost" id="to-reviews">去复核队列</button>
            </div>
          </div>
        </section>
      </div>

      <div class="grid-2">
        <section class="panel">
          <div class="panel-head"><h2>近 7 天重算</h2><span class="meta">runs / day</span></div>
          <div class="panel-body">${trendChart(data.trend)}</div>
        </section>
        <section class="panel">
          <div class="panel-head"><h2>最近一次归并</h2><span class="meta">match run</span></div>
          <div class="panel-body">
            ${
              latest
                ? `<div class="kv">
                    <dt>运行号</dt><dd class="mono">${esc(latest.run_no)}</dd>
                    <dt>状态</dt><dd>${badge(latest.status === 'success' ? 'ok' : 'warn', latest.status_label)}</dd>
                    <dt>完成时间</dt><dd>${fmtTime(latest.finished_at)}</dd>
                    <dt>簇 / 多成员</dt><dd class="mono">${esc(latest.cluster_count)} / ${esc(latest.multi_count)}</dd>
                    <dt>去重率</dt><dd class="mono">${esc(pct(latest.dedup_rate))}</dd>
                    <dt>风险簇</dt><dd>${badge(riskTone('medium'), `${latest.risk_count} 个`)}</dd>
                  </div>`
                : emptyState({ title: '还没有归并记录', hint: '先在「中介与采集」确认 9 家渠道，再去「归并簇」重算。' })
            }
          </div>
        </section>
      </div>`;

    view.querySelector('#to-reviews')?.addEventListener('click', () => {
      ctx.navigate('#/reviews');
    });
  },
};

export default overviewPage;

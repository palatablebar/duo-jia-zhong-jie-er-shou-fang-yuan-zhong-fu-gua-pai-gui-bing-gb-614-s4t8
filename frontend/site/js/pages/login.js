import { api } from '../api.js';
import { session } from '../store.js';
import { BRAND } from '../config.js';
import { errorMessage, esc, toast } from '../ui.js';

const WINDOW_TAGS = [
  {
    src: '链家 · 浦东花木店',
    raw: '89.5㎡ · 南北 · 2/18 层',
    price: '598 万',
    hand: '挂牌原文',
  },
  {
    src: '我爱我家 · 世纪公园店',
    raw: '89.5平米 · 南北通透 · 2 层',
    price: '602 万',
    hand: '挂牌原文',
  },
  {
    src: '中原地产 · 联洋店',
    raw: '建面89.5 · 三室两厅一卫',
    price: '610 万',
    hand: '挂牌原文',
  },
  {
    src: 'golden record · 4 家中介',
    raw: '89.5㎡ · 3-2-1 · 中位 604 万 · 价差 12 万',
    price: '604 万',
    hand: '同一套房',
    merged: true,
  },
];

export const loginPage = {
  async render(root, ctx) {
    root.className = '';
    root.innerHTML = `
      <div class="login-shop">
        <section class="shop-front">
          <div class="shop-head">
            <div class="eyebrow">${esc(BRAND.edition)}</div>
            <h1>同一套房<br /><em>只挂一次</em><br />剩下的交给台账</h1>
            <p class="tagline">${esc(BRAND.loginLead)}</p>
          </div>
          <div class="shop-grid">
            ${WINDOW_TAGS.map(
              (tag) => `<article class="listing-tag${tag.merged ? ' merged' : ''}">
                <span class="tag-hand">${esc(tag.hand)}</span>
                <span class="tag-price">${esc(tag.price)}</span>
                <span class="tag-meta">${esc(tag.raw)}</span>
                <span class="tag-src">${esc(tag.src)}</span>
              </article>`,
            ).join('')}
          </div>
          <div class="shop-foot">
            <span class="eyebrow">${esc(BRAND.org)} · 内部工作台</span>
            <span class="eyebrow">示例橱窗，数据取自演示集</span>
          </div>
        </section>
        <section class="login-panel">
          <form class="login-card" id="login-form" novalidate>
            <div>
              <div class="brand">${esc(BRAND.title)}</div>
              <div class="sub">使用内部账号登录。三个演示账号权限不同，按钮与页面会随角色变化。</div>
            </div>
            <div class="field">
              <label for="email">邮箱</label>
              <input id="email" name="email" type="email" autocomplete="username" value="admin@${esc(BRAND.short)}.io" required />
            </div>
            <div class="field">
              <label for="password">密码</label>
              <input id="password" name="password" type="password" autocomplete="current-password" value="Demo@2026" required />
            </div>
            <div class="form-error" id="login-error" role="alert"></div>
            <button class="btn accent" id="login-submit" type="submit">进入房源中台</button>
            <div class="login-hint">
              演示账号（密码 <code>Demo@2026</code>）：<br />
              <code>admin@${esc(BRAND.short)}.io</code> 管理员 · <code>analyst@${esc(BRAND.short)}.io</code> 数据专员 ·
              <code>viewer@${esc(BRAND.short)}.io</code> 只读
            </div>
          </form>
        </section>
      </div>`;

    const form = root.querySelector('#login-form');
    const errorNode = root.querySelector('#login-error');
    const submit = root.querySelector('#login-submit');
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      errorNode.textContent = '';
      submit.disabled = true;
      submit.textContent = '正在核对…';
      try {
        const result = await api.post('/api/auth/login', {
          email: form.email.value.trim(),
          password: form.password.value,
        });
        session.set(result.access_token, result.user);
        toast(`欢迎回来，${result.user.display_name}`);
        location.hash = '#/overview';
        await ctx.reload();
      } catch (err) {
        errorNode.textContent = err.code === 'AUTH_INVALID' ? '账号或密码不正确' : errorMessage(err);
      } finally {
        submit.disabled = false;
        submit.textContent = '进入房源中台';
      }
    });
  },
};

export default loginPage;

const THEME_LABELS = {
  all:      "⛩️ すべて",
  quantum:  "🧮 量子",
  space:    "🛰 防衛宇宙",
  semi:     "⚡ 半導体",
  battery:  "🔋 次世代電池",
  energy:   "⛽ エネルギー",
  material: "🧱 素材",
  other:    "その他",
};

const ALERT_LABELS = {
  buy:      "🟢 買い",
  treasure: "💎 白虎単独宝",
  sell:     "🔴 売り",
  skip:     "⚪ 見送り",
};

const MARKET_LABELS = {
  all: "🌐 日米",
  us:  "🇺🇸 米国",
  jp:  "🇯🇵 日本",
};

let CURRENT_DATA = null;
let CURRENT_THEME = "all";
let CURRENT_ALERT = "buy";
let CURRENT_MARKET = "all";
let CURRENT_SEARCH = "";

async function loadSignals() {
  const summaryEl = document.querySelector("#summary");
  const tableEl = document.querySelector("#signals-table");
  setupIntroPanel();
  try {
    const res = await fetch("signals.json?t=" + Date.now());
    if (!res.ok) throw new Error("signals.json not found");
    const data = await res.json();
    CURRENT_DATA = data;
    renderSummary(summaryEl, data);
    renderTopPicks(data);
    renderAlertTabs(data);
    renderMarketToggle(data);
    renderTabs(data);
    bindSearch();
    rerender();
  } catch (e) {
    summaryEl.innerHTML = '<div class="meta">⛩️ 初回ビルド待ち — GitHub Actionsが朱雀を起動するまでお待ちください</div>';
    tableEl.innerHTML = '<p style="color:var(--muted)">神託データ未生成（signals.json）</p>';
  }
  document.querySelector("#footer-date").textContent =
    new Date().toLocaleDateString("ja-JP");
}

function setupIntroPanel() {
  const panel = document.querySelector("#intro-panel");
  const closeBtn = document.querySelector("#intro-close");
  if (!panel || !closeBtn) return;
  if (localStorage.getItem("intro_closed") === "1") {
    panel.style.display = "none";
  }
  closeBtn.addEventListener("click", () => {
    panel.style.display = "none";
    localStorage.setItem("intro_closed", "1");
  });
}

function buildRecommendReason(s) {
  const parts = [];
  // 朱雀
  if (s["総合"].includes("🦒")) parts.push("🦒4神合議の最上位");
  else if (s["総合"].includes("💎")) parts.push("💎複数神獣で確認");
  else if (s["総合"].includes("★★★")) parts.push("🔥強い買いシグナル");
  else if (s["総合"].includes("★★")) parts.push("🔥買いシグナル");
  else if (s["総合"].includes("★")) parts.push("🔥弱い買いシグナル");
  // 白虎
  const b = s["白虎"];
  if (b === "S") parts.push("🐅CEO/CFOクラス買い");
  else if (b === "A") parts.push("🐅幹部買い");
  else if (b === "B") parts.push("🐅役員買い");
  else if (b === "D") parts.push("⚠️幹部売却超過");
  // 玄武
  const gn = s["玄武詳細"] || "";
  if (s["玄武"] === "S") parts.push("🐢業績爆発加速中");
  else if (s["玄武"] === "A") parts.push(`🐢${gn.replace("(前期", "前期")}`);
  else if (s["玄武"] === "B") parts.push("🐢売上成長");
  else if (s["玄武"] === "D") parts.push("⚠️減収");
  // 青龍
  const sr = s["青龍詳細"] || "";
  if (s["青龍"] === "S") parts.push("🐉アナリスト強気＋EPS好調");
  else if (s["青龍"] === "A") parts.push("🐉アナリスト強気");
  else if (s["青龍"] === "B") parts.push("🐉アナリストやや強気");
  else if (s["青龍"] === "D") parts.push("⚠️アナリスト弱気");
  return parts.join(" × ");
}

function renderTopPicks(data) {
  const el = document.querySelector("#picks-grid");
  if (!el) return;
  const tops = (data.signals || []).filter(s =>
    s["総合"].includes("🦒") || s["総合"].includes("💎🐢") || s["総合"].includes("💎🐉")
  ).slice(0, 5);
  if (tops.length === 0) {
    el.innerHTML = '<p class="picks-empty">本日 麒麟・二神宝 該当銘柄なし。★★★/★★ を確認してください。</p>';
    return;
  }
  el.innerHTML = tops.map((s, i) => {
    const medal = i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `${i+1}`;
    const reason = buildRecommendReason(s);
    const flag = s["市場"] === "jp" ? "🇯🇵" : "🇺🇸";
    return `<div class="pick-card pick-rank-${i+1}">
      <div class="pick-rank">${medal}</div>
      <div class="pick-main">
        <div class="pick-head">
          <span class="pick-ticker">${esc(s["ティッカー"])}</span>
          <span class="pick-flag">${flag}</span>
          <span class="pick-theme">${esc(s["テーマ表示"] || "")}</span>
        </div>
        <div class="pick-name">${esc(s["社名"])}</div>
        <div class="pick-price">${s["現在値"]} <span class="pick-judgement">${esc(s["総合"])}</span></div>
        <div class="pick-reason">${reason}</div>
      </div>
    </div>`;
  }).join("");
}

function rerender() {
  const tableEl = document.querySelector("#signals-table");
  const filtered = applyFilters(CURRENT_DATA.signals);
  renderTabs(CURRENT_DATA);
  renderAlertTabs(CURRENT_DATA);
  renderMarketToggle(CURRENT_DATA);
  renderTable(tableEl, filtered);
  updateLegend();
}

function applyFilters(signals) {
  // 検索時はタブ・市場・テーマフィルタを無視して全銘柄から探す
  if (CURRENT_SEARCH) {
    const q = CURRENT_SEARCH.toLowerCase();
    return signals.filter(s => {
      const blob = (s["ティッカー"] + " " + s["社名"]).toLowerCase();
      return blob.includes(q);
    });
  }
  return signals.filter(s => {
    if (s["Alert"] !== CURRENT_ALERT) return false;
    if (CURRENT_MARKET !== "all" && s["市場"] !== CURRENT_MARKET) return false;
    if (CURRENT_THEME !== "all" && s["テーマ"] !== CURRENT_THEME) return false;
    return true;
  });
}

function renderSummary(el, d) {
  const a = d.alerts || {buy:0, sell:0, skip:0};
  const m = d.markets || {us:0, jp:0};
  el.innerHTML = `
    <div class="meta">最新神託: <b>${d.generated_jst}</b></div>
    <div class="stats">
      <div class="stat"><b>${d.universe_total}</b>母集団</div>
      <div class="stat"><b>${d.filtered_total}</b>抽出</div>
      <div class="stat" style="color:#16a34a"><b>${a.buy}</b>🟢買い</div>
      <div class="stat" style="color:#dc2626"><b>${a.sell}</b>🔴売り</div>
      <div class="stat" style="color:var(--muted)"><b>${a.skip}</b>⚪見送り</div>
      <div class="stat" style="color:var(--gold-dark)"><b>${d.counts.kirin || 0}</b>🦒麒麟</div>
    </div>`;
}

function renderAlertTabs(data) {
  const el = document.querySelector("#alert-tabs");
  if (!el) return;
  const a = data.alerts || {buy:0, sell:0, skip:0};
  el.innerHTML = ["buy","treasure","sell","skip"].map(k => {
    const cls = k === CURRENT_ALERT ? "alert-tab active alert-" + k : "alert-tab alert-" + k;
    return `<button class="${cls}" data-alert="${k}">
      ${ALERT_LABELS[k]}<span class="theme-count">${a[k] || 0}</span>
    </button>`;
  }).join("");
  el.querySelectorAll(".alert-tab").forEach(b => {
    b.addEventListener("click", () => {
      CURRENT_ALERT = b.dataset.alert;
      CURRENT_THEME = "all";
      rerender();
    });
  });
}

function renderMarketToggle(data) {
  const el = document.querySelector("#market-toggle");
  if (!el) return;
  const m = data.markets || {us:0, jp:0};
  const counts = {all: data.signal_total, us: m.us, jp: m.jp};
  el.innerHTML = ["all","us","jp"].map(k => {
    const active = k === CURRENT_MARKET ? " active" : "";
    return `<button class="market-btn${active}" data-market="${k}">
      ${MARKET_LABELS[k]}<span class="theme-count">${counts[k] || 0}</span>
    </button>`;
  }).join("");
  el.querySelectorAll(".market-btn").forEach(b => {
    b.addEventListener("click", () => {
      CURRENT_MARKET = b.dataset.market;
      rerender();
    });
  });
}

function renderTabs(data) {
  const el = document.querySelector("#theme-tabs");
  if (!el) return;
  // CURRENT_ALERT × CURRENT_MARKET でテーマ別件数を再計算
  const subset = data.signals.filter(s =>
    s["Alert"] === CURRENT_ALERT &&
    (CURRENT_MARKET === "all" || s["市場"] === CURRENT_MARKET));
  const themeCounts = {};
  subset.forEach(s => { themeCounts[s["テーマ"]] = (themeCounts[s["テーマ"]] || 0) + 1; });
  const order = ["all", "quantum", "space", "semi", "battery", "energy", "material", "other"];
  el.innerHTML = order.map(k => {
    const count = k === "all" ? subset.length : (themeCounts[k] || 0);
    if (k !== "all" && count === 0) return "";
    const active = k === CURRENT_THEME ? " active" : "";
    return `<button class="theme-tab${active}" data-theme="${k}">
      ${THEME_LABELS[k]}<span class="theme-count">${count}</span>
    </button>`;
  }).join("");
  el.querySelectorAll(".theme-tab").forEach(b => {
    b.addEventListener("click", () => {
      CURRENT_THEME = b.dataset.theme;
      rerender();
    });
  });
}

function bindSearch() {
  const input = document.querySelector("#search-input");
  if (!input) return;
  input.addEventListener("input", e => {
    CURRENT_SEARCH = e.target.value;
    rerender();
  });
}

function updateLegend() {
  const el = document.querySelector("#legend-buy");
  if (!el) return;
  if (CURRENT_ALERT === "buy") {
    el.innerHTML = `
      <span class="tag kirin">🦒 麒麟（朱雀×白虎）</span>
      <span class="tag strong">★★★ 強い買い</span>
      <span class="tag buy">★★ 買い</span>
      <span class="tag weak">★ 弱い買い</span>`;
  } else if (CURRENT_ALERT === "treasure") {
    el.innerHTML = `<span class="tag treasure">💎 朱雀-シグナル × 白虎B以上 = インサイダー単独宝</span>`;
  } else if (CURRENT_ALERT === "sell") {
    el.innerHTML = `
      <span class="tag sell-strong">💀 全神売り</span>
      <span class="tag sell">🔴 売り</span>
      <span class="tag sell-weak">🔴 弱い売り</span>`;
  } else {
    el.innerHTML = `<span class="tag skip">⚪ 見送り賢明（シグナル混在）</span>`;
  }
}

function renderTable(el, signals) {
  if (!signals || signals.length === 0) {
    el.innerHTML = '<p style="color:var(--muted); padding: 20px 0;">該当銘柄なし</p>';
    return;
  }
  const rows = signals.map((s, i) => {
    const rank = i + 1;
    const rankMark = rank === 1 ? "🥇" : rank === 2 ? "🥈" : rank === 3 ? "🥉" : rank;
    const cls = s["総合"].includes("🦒") ? "row-kirin"
              : s["Alert"] === "treasure" ? "row-treasure"
              : s["総合"].includes("★★★") ? "row-strong"
              : s["総合"].includes("★★") ? "row-buy"
              : s["Alert"] === "sell" ? "row-sell"
              : s["Alert"] === "skip" ? "row-skip" : "";
    const byakkoGrade = s["白虎"] || "-";
    const byakkoCls = byakkoGrade === "S" ? "byakko-s"
                    : byakkoGrade === "A" ? "byakko-a"
                    : byakkoGrade === "B" ? "byakko-b"
                    : byakkoGrade === "C" ? "byakko-c"
                    : byakkoGrade === "D" ? "byakko-d" : "byakko-none";
    const genbuGrade = s["玄武"] || "-";
    const genbuCls = genbuGrade === "S" ? "genbu-s"
                   : genbuGrade === "A" ? "genbu-a"
                   : genbuGrade === "B" ? "genbu-b"
                   : genbuGrade === "C" ? "genbu-c"
                   : genbuGrade === "D" ? "genbu-d" : "genbu-none";
    const seiryuGrade = s["青龍"] || "-";
    const seiryuCls = seiryuGrade === "S" ? "seiryu-s"
                    : seiryuGrade === "A" ? "seiryu-a"
                    : seiryuGrade === "B" ? "seiryu-b"
                    : seiryuGrade === "C" ? "seiryu-c"
                    : seiryuGrade === "D" ? "seiryu-d" : "seiryu-none";
    const marketFlag = s["市場"] === "jp" ? "🇯🇵" : "🇺🇸";
    const reason = buildRecommendReason(s);
    return `<tr class="${cls}">
      <td class="rank">${rankMark}</td>
      <td>${s["総合"]}</td>
      <td class="score">${s["Score"]}</td>
      <td class="flag">${marketFlag}</td>
      <td>${esc(s["テーマ表示"] || "")}</td>
      <td class="ticker">${esc(s["ティッカー"])}</td>
      <td>
        <div>${esc(s["社名"])}</div>
        ${reason ? `<div class="row-reason">${reason}</div>` : ""}
      </td>
      <td class="price">${s["現在値"]}</td>
      <td class="byakko ${byakkoCls}" title="${esc(s["白虎詳細"] || "")}">${byakkoGrade}</td>
      <td class="genbu ${genbuCls}" title="${esc(s["玄武詳細"] || "")}">${genbuGrade}</td>
      <td class="seiryu ${seiryuCls}" title="${esc(s["青龍詳細"] || "")}">${seiryuGrade}</td>
      <td>${esc(s["W%R"])}</td>
      <td>${esc(s["RSI"])}</td>
      <td>${esc(s["MACD"])}</td>
      <td>${esc(s["Stoch"])}</td>
      <td>${esc(s["MA"])}</td>
    </tr>`;
  }).join("");
  el.innerHTML = `<table>
    <thead><tr>
      <th>順位</th><th>総合</th><th>Score</th><th>市場</th><th>テーマ</th><th>ティッカー</th><th>社名</th>
      <th>現在値</th>
      <th title="インサイダー買い">🐅白虎</th>
      <th title="売上YoY成長率＋加速度">🐢玄武</th>
      <th title="アナリスト推奨×目標株価×EPS">🐉青龍</th>
      <th>W%R</th><th>RSI</th><th>MACD</th><th>Stoch</th><th>MA</th>
    </tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

function esc(s) {
  return String(s ?? "").replace(/[<>&"]/g, c =>
    ({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"}[c]));
}

loadSignals();

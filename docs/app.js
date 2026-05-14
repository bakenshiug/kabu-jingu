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
  try {
    const res = await fetch("signals.json?t=" + Date.now());
    if (!res.ok) throw new Error("signals.json not found");
    const data = await res.json();
    CURRENT_DATA = data;
    renderSummary(summaryEl, data);
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
  return signals.filter(s => {
    if (s["Alert"] !== CURRENT_ALERT) return false;
    if (CURRENT_MARKET !== "all" && s["市場"] !== CURRENT_MARKET) return false;
    if (CURRENT_THEME !== "all" && s["テーマ"] !== CURRENT_THEME) return false;
    if (CURRENT_SEARCH) {
      const q = CURRENT_SEARCH.toLowerCase();
      const blob = (s["ティッカー"] + " " + s["社名"]).toLowerCase();
      if (!blob.includes(q)) return false;
    }
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
    return `<tr class="${cls}">
      <td class="rank">${rankMark}</td>
      <td>${s["総合"]}</td>
      <td class="score">${s["Score"]}</td>
      <td class="flag">${marketFlag}</td>
      <td>${esc(s["テーマ表示"] || "")}</td>
      <td class="ticker">${esc(s["ティッカー"])}</td>
      <td>${esc(s["社名"])}</td>
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

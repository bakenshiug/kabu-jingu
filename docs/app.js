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

const TIMEFRAME_LABELS = {
  all:       "🌐 すべて",
  short:     "⏱ 短期",
  mid:       "📅 中期",
  long:      "🌳 長期",
  tenbagger: "🚀 テンバガー狙い",
};

let CURRENT_DATA = null;
let CURRENT_THEME = "all";
let CURRENT_ALERT = "buy";
let CURRENT_MARKET = "all";
let CURRENT_TIMEFRAME = "all";
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

function getKeibaMark(s) {
  const t = s["総合"];
  if (t.includes("⚠️") || t.includes("💀") || t.includes("🔴")) return {mark: "✕", label: "消し"};
  if (t.includes("真麒麟")) return {mark: "◎◎", label: "絶対本命"};
  if (t.includes("🦒")) return {mark: "◎", label: "本命"};
  if (t.includes("💎🐢") || t.includes("💎🐉")) return {mark: "○", label: "対抗"};
  if (t.includes("💎")) {
    if (s["白虎"] === "S") return {mark: "▲", label: "抑え"};
    return {mark: "△", label: "連下"};
  }
  if (t.includes("★★★")) return {mark: "▲", label: "抑え"};
  if (t.includes("★★")) return {mark: "△", label: "連下"};
  if (t.includes("★")) {
    const price = parseFloat(s["現在値"]);
    // 低位株（$5以下 or ¥500以下）& 朱雀シグナル = 大穴枠
    if ((s["市場"] === "us" && price < 5) || (s["市場"] === "jp" && price < 500)) {
      return {mark: "☆", label: "大穴（テンバガー枠）"};
    }
    return {mark: "△", label: "連下"};
  }
  return {mark: "", label: ""};
}

function getTimeframes(s) {
  const tags = [];
  const w = parseFloat(s["W%R"]);
  const rsi = parseFloat(s["RSI"]);
  const byakko = s["白虎"];
  const genbu = s["玄武"];
  const seiryu = s["青龍"];
  // 短期：テクニカル売られすぎ反発狙い
  if (s["Alert"] === "buy" && (w <= -80 || rsi < 30 || s["総合"].includes("★★★"))) {
    tags.push({tag: "⏱ 短期", title: "テクニカル売られすぎ反発・数日〜2週間"});
  }
  // 中期：業績モメンタム＋アナリスト
  if (["S","A","B"].includes(genbu) || ["S","A"].includes(seiryu)) {
    tags.push({tag: "📅 中期", title: "業績モメンタム×アナリスト評価・1〜3ヶ月"});
  }
  // 長期：インサイダー×成長
  if (["S","A","B"].includes(byakko) && ["S","A","B"].includes(genbu)) {
    tags.push({tag: "🌳 長期", title: "インサイダー買い×高成長・3ヶ月〜1年"});
  }
  return tags;
}

function getHumorTagline(s) {
  const t = s["総合"];
  if (t.includes("真麒麟")) return "🦒 4神全一致、神宮で年数回の現象。これは買わない理由を探す方が難しい";
  if (t.includes("🦒")) return "🦒 神獣3柱が「これだ」と頷いた。神宮の本命降臨";
  if (t.includes("💎🐢")) return "💎🐢 白虎の鼻と玄武の数字がガッチリ握手";
  if (t.includes("💎🐉")) return "💎🐉 白虎の動きにアナリストも黙ってない";
  if (t.includes("💎")) {
    if (s["白虎"] === "S") return "🐅 CEO/CFOが自腹で参戦、中の人は何かに気づいてる";
    if (s["白虎"] === "A") return "🐅 役員が動いてる。神宮の触覚がピクッと反応";
    if (s["白虎"] === "B") return "🐅 内部で小さな動き。様子見の打診価値あり";
    return "💎 隠れ宝の匂い";
  }
  if (t.includes("⚠️")) {
    if (t.includes("白虎D")) return "⚠️ 表は買いの顔、裏で幹部がドル箱抱えて逃走中";
    if (t.includes("玄武D")) return "⚠️ テクニカル○だが売上は減少。罠の予感";
    if (t.includes("青龍D")) return "⚠️ チャートは買いだがアナリストはそっぽ向き";
    return "⚠️ 何かがおかしい";
  }
  if (t.includes("★★★")) return "🔥 テクニカル鉄板、押し目の極上タイミング";
  if (t.includes("★★")) return "🔥 売られすぎ圏、神宮の打診買い候補";
  if (t.includes("★")) return "🔥 ちょっとだけ買いシグナル";
  if (t.includes("💀")) return "💀 全神が手を引いた。逃げ時の鐘";
  if (t.includes("🔴")) return "🔴 売りシグナル、利確の検討時";
  return "";
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

function renderPickCard(s, i) {
  const medal = i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `${i+1}`;
  const reason = buildRecommendReason(s);
  const humor = getHumorTagline(s);
  const km = getKeibaMark(s);
  const flag = s["市場"] === "jp" ? "🇯🇵" : "🇺🇸";
  const tfs = getTimeframes(s);
  const tfHtml = tfs.map(t => `<span class="tf-tag" title="${esc(t.title)}">${t.tag}</span>`).join("");
  const markHtml = km.mark ? `<span class="keiba-mark" title="${km.label}">${km.mark}</span>` : "";
  const ticker = esc(s["ティッカー"]);
  return `<div class="pick-card pick-rank-${i+1}">
    <div class="pick-rank">${medal}</div>
    <div class="pick-main">
      <div class="pick-head">
        ${markHtml}
        <span class="pick-ticker">${ticker}</span>
        <button class="copy-btn" data-copy="${ticker}" title="ティッカーをコピー">📋</button>
        <span class="pick-flag">${flag}</span>
        <span class="pick-theme">${esc(s["テーマ表示"] || "")}</span>
      </div>
      <div class="pick-name">${esc(s["社名"])}</div>
      <div class="pick-price">${s["現在値"]} <span class="pick-judgement">${esc(s["総合"])}</span></div>
      ${tfHtml ? `<div class="pick-tf">${tfHtml}</div>` : ""}
      ${humor ? `<div class="pick-humor">${humor}</div>` : ""}
      <div class="pick-reason">${reason}</div>
    </div>
  </div>`;
}

function renderTopPicks(data) {
  const honmei = document.querySelector("#picks-grid");
  const treasures = document.querySelector("#treasures-grid");
  if (!honmei || !treasures) return;
  const signals = data.signals || [];
  // 本命枠: 🦒麒麟 + 💎🐢/💎🐉 二神宝
  const tops = signals.filter(s =>
    s["総合"].includes("🦒") || s["総合"].includes("💎🐢") || s["総合"].includes("💎🐉")
  ).slice(0, 5);
  // 隠れ宝枠: 💎 単独宝（S/A）
  const treas = signals.filter(s =>
    s["Alert"] === "treasure"
    && !s["総合"].includes("🦒")
    && !s["総合"].includes("💎🐢") && !s["総合"].includes("💎🐉")
    && ["S","A"].includes(s["白虎"])
  ).slice(0, 5);

  if (tops.length === 0) {
    honmei.innerHTML = '<p class="picks-empty">本日 本命・対抗該当なし。★★★/★★ を確認してください</p>';
  } else {
    honmei.innerHTML = tops.map((s, i) => renderPickCard(s, i)).join("");
  }

  if (treas.length === 0) {
    treasures.innerHTML = '<p class="picks-empty">本日 隠れ宝該当なし</p>';
  } else {
    treasures.innerHTML = treas.map((s, i) => renderPickCard(s, i)).join("");
  }
}

function rerender() {
  const tableEl = document.querySelector("#signals-table");
  const filtered = applyFilters(CURRENT_DATA.signals);
  renderTabs(CURRENT_DATA);
  renderAlertTabs(CURRENT_DATA);
  renderMarketToggle(CURRENT_DATA);
  renderTimeframeTabs(CURRENT_DATA);
  renderTable(tableEl, filtered);
  updateLegend();
}

function hasTimeframe(s, tf) {
  if (tf === "all") return true;
  const km = getKeibaMark(s);
  if (tf === "tenbagger") return km.mark === "☆";
  const tfs = getTimeframes(s).map(t => t.tag);
  if (tf === "short") return tfs.some(t => t.includes("短期"));
  if (tf === "mid") return tfs.some(t => t.includes("中期"));
  if (tf === "long") return tfs.some(t => t.includes("長期"));
  return false;
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
    if (!hasTimeframe(s, CURRENT_TIMEFRAME)) return false;
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

function renderTimeframeTabs(data) {
  const el = document.querySelector("#timeframe-tabs");
  if (!el) return;
  // 朱雀alert × 市場フィルタ通過後のサブセットで件数算出
  const subset = (data.signals || []).filter(s =>
    s["Alert"] === CURRENT_ALERT &&
    (CURRENT_MARKET === "all" || s["市場"] === CURRENT_MARKET) &&
    (CURRENT_THEME === "all" || s["テーマ"] === CURRENT_THEME));
  const counts = {
    all: subset.length,
    short: subset.filter(s => hasTimeframe(s, "short")).length,
    mid: subset.filter(s => hasTimeframe(s, "mid")).length,
    long: subset.filter(s => hasTimeframe(s, "long")).length,
    tenbagger: subset.filter(s => hasTimeframe(s, "tenbagger")).length,
  };
  const order = ["all", "short", "mid", "long", "tenbagger"];
  el.innerHTML = order.map(k => {
    const active = k === CURRENT_TIMEFRAME ? " active" : "";
    return `<button class="tf-btn tf-${k}${active}" data-tf="${k}">
      ${TIMEFRAME_LABELS[k]}<span class="theme-count">${counts[k] || 0}</span>
    </button>`;
  }).join("");
  el.querySelectorAll(".tf-btn").forEach(b => {
    b.addEventListener("click", () => {
      CURRENT_TIMEFRAME = b.dataset.tf;
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
  const isSearching = !!CURRENT_SEARCH;
  const rows = signals.map((s, i) => {
    const rank = i + 1;
    const rankMark = isSearching ? "—"
                    : rank === 1 ? "🥇" : rank === 2 ? "🥈" : rank === 3 ? "🥉" : rank;
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
    const km = getKeibaMark(s);
    const tfs = getTimeframes(s);
    const tfHtml = tfs.map(t => `<span class="tf-tag-small" title="${esc(t.title)}">${t.tag}</span>`).join(" ");
    return `<tr class="${cls}">
      <td class="rank">${rankMark}</td>
      <td class="keiba-cell" title="${km.label}">${km.mark}</td>
      <td>
        <div>${s["総合"]}</div>
        ${tfHtml ? `<div class="row-tf">${tfHtml}</div>` : ""}
      </td>
      <td class="score">${s["Score"]}</td>
      <td class="flag">${marketFlag}</td>
      <td>${esc(s["テーマ表示"] || "")}</td>
      <td class="ticker">${esc(s["ティッカー"])} <button class="copy-btn-small" data-copy="${esc(s["ティッカー"])}" title="コピー">📋</button></td>
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
      <th>順位</th><th title="競馬印">印</th><th>総合</th><th>Score</th><th>市場</th><th>テーマ</th><th>ティッカー</th><th>社名</th>
      <th>現在値</th>
      <th class="god-th" title="米SEC Form 4 / インサイダー買い">🐅 白虎<br><span class="god-sub">インサイダー</span></th>
      <th class="god-th" title="売上YoY成長率＋加速度">🐢 玄武<br><span class="god-sub">業績</span></th>
      <th class="god-th" title="アナリスト推奨×目標株価×EPSサプライズ">🐉 青龍<br><span class="god-sub">評価</span></th>
      <th>W%R</th><th>RSI</th><th>MACD</th><th>Stoch</th><th>MA</th>
    </tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

function esc(s) {
  return String(s ?? "").replace(/[<>&"]/g, c =>
    ({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"}[c]));
}

// ティッカーコピー機能（全体イベント委譲）
document.addEventListener("click", async (e) => {
  const btn = e.target.closest(".copy-btn, .copy-btn-small");
  if (!btn) return;
  e.preventDefault();
  e.stopPropagation();
  const text = btn.dataset.copy;
  try {
    await navigator.clipboard.writeText(text);
    showToast(`📋 ${text} をコピーしました`);
  } catch (err) {
    // フォールバック
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); showToast(`📋 ${text} をコピーしました`); }
    catch { showToast("❌ コピーに失敗しました"); }
    document.body.removeChild(ta);
  }
});

let toastTimer = null;
function showToast(msg) {
  let el = document.querySelector("#copy-toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "copy-toast";
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.classList.add("show");
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 1800);
}

loadSignals();

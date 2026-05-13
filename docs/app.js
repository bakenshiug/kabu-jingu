async function loadSignals() {
  const summaryEl = document.querySelector("#summary");
  const tableEl = document.querySelector("#signals-table");
  try {
    const res = await fetch("signals.json?t=" + Date.now());
    if (!res.ok) throw new Error("signals.json not found");
    const data = await res.json();
    renderSummary(summaryEl, data);
    renderTable(tableEl, data.signals);
  } catch (e) {
    summaryEl.innerHTML = '<div class="meta">⛩️ 初回ビルド待ち — GitHub Actionsが朱雀を起動するまでお待ちください</div>';
    tableEl.innerHTML = '<p style="color:var(--muted)">神託データ未生成（signals.json）</p>';
  }
  document.querySelector("#footer-date").textContent =
    new Date().toLocaleDateString("ja-JP");
}

function renderSummary(el, d) {
  el.innerHTML = `
    <div class="meta">最新神託: <b>${d.generated_jst}</b></div>
    <div class="stats">
      <div class="stat"><b>${d.universe_total}</b>母集団</div>
      <div class="stat"><b>${d.filtered_total}</b>セクター抽出</div>
      <div class="stat"><b>${d.signal_total}</b>買い神託</div>
      <div class="stat" style="color:var(--strong)"><b>${d.counts.strong}</b>★★★</div>
      <div class="stat" style="color:var(--buy)"><b>${d.counts.buy}</b>★★</div>
      <div class="stat" style="color:var(--weak)"><b>${d.counts.weak}</b>★</div>
    </div>`;
}

function renderTable(el, signals) {
  if (!signals || signals.length === 0) {
    el.innerHTML = '<p style="color:var(--muted)">本日の買いシグナル該当銘柄なし</p>';
    return;
  }
  const rows = signals.map(s => {
    const cls = s["総合"].includes("★★★") ? "row-strong"
              : s["総合"].includes("★★") ? "row-buy" : "";
    return `<tr class="${cls}">
      <td>${s["総合"]}</td>
      <td class="score">${s["Score"]}</td>
      <td>${esc(s["セクター"])}</td>
      <td class="ticker">${esc(s["ティッカー"])}</td>
      <td>${esc(s["社名"])}</td>
      <td class="price">${s["現在値"]}</td>
      <td>${esc(s["W%R"])}</td>
      <td>${esc(s["RSI"])}</td>
      <td>${esc(s["MACD"])}</td>
      <td>${esc(s["Stoch"])}</td>
      <td>${esc(s["MA"])}</td>
    </tr>`;
  }).join("");
  el.innerHTML = `<table>
    <thead><tr>
      <th>総合</th><th>Score</th><th>セクター</th><th>ティッカー</th><th>社名</th>
      <th>現在値</th><th>W%R</th><th>RSI</th><th>MACD</th><th>Stoch</th><th>MA</th>
    </tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

function esc(s) {
  return String(s ?? "").replace(/[<>&"]/g, c =>
    ({"<":"&lt;",">":"&gt;","&":"&amp;",'"':"&quot;"}[c]));
}

loadSignals();

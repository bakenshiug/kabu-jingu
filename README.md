# ⛩️ UG株式神宮 ⛩️

日米株式の多指標合議による買いシグナル神託システム。

公開URL: `https://bakenshiug.github.io/kabu-jingu/`

## 神宮ロードマップ

| Phase | 神獣 | 担当 | 状態 |
|---|---|---|---|
| α | 🔥 朱雀 | テクニカル5指標合議 | ✅ 稼働中 |
| β | 🐉 青龍 | 決算言霊（CEO発言・IR資料） | 計画 |
| γ | 🐅 白虎 | 需給・空売り比率 | 計画 |
| γ | 🐢 玄武 | 業績トレンド・FCF | 計画 |
| γ | 🦒 麒麟 | 4神合議の総合1位 | 計画 |

## 構成

```
kabu-jingu/
├── scripts/suzaku_scan.py        # 朱雀スキャナー
├── docs/                          # GitHub Pages公開元
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── signals.json              # Actions が自動生成
└── .github/workflows/
    └── suzaku_scan.yml           # 朝7:00 JST 自動実行
```

## ローカル実行

```bash
pip install yfinance pandas lxml requests pandas-datareader
python scripts/suzaku_scan.py
# → docs/signals.json が生成される
python -m http.server 8765 --directory docs
# → http://localhost:8765/
```

## GitHubセットアップ手順

1. `bakenshiug` で新規Publicリポ `kabu-jingu` 作成
2. ローカルでpush:
   ```bash
   cd ~/kabu-jingu
   git init -b main
   git add .
   git commit -m "⛩️ 神宮α 開山"
   git remote add origin git@github.com:bakenshiug/kabu-jingu.git
   git push -u origin main
   ```
3. Settings → Pages → Source: `main` / `/docs`
4. Settings → Actions → General → Workflow permissions: **Read and write permissions**
5. Actions タブ → 🔥 朱雀テクニカル神託 → Run workflow（初回手動実行）

## スケジュール

- 平日 朝7:00 JST（米市場引け後）に自動実行
- cron: `0 22 * * 1-5` (UTC)
- 結果は `docs/signals.json` に書き出し → GitHub Pages即反映

## 朱雀ロジック

5指標合議で**売りシグナル0**を条件に買いのみ抽出：

- Williams %R(14)
- RSI(14)
- MACD
- Stochastic(14,3)
- 移動平均(5/25/75)

各指標 +2/+1/0/-1/-2 でスコア化。
- ★★★ 強い買い: 合計 ≥ 7 かつ売り0
- ★★ 買い: 合計 ≥ 4 かつ売り≤1
- ★ 弱い買い: 合計 ≥ 2 かつ売り≤1

## 母集団

- 🇺🇸 S&P500 + NASDAQ100（Wikipedia）
- 🇯🇵 Nikkei225 + 半導体/蓄電池/エネルギー/航空宇宙キュレーション銘柄
- キーワードフィルタ: Semiconductor / Quantum / Aerospace / Battery / Energy / Material 系

---

⛩️ 本サイトの情報は投資判断の参考であり、売買を勧誘するものではありません。

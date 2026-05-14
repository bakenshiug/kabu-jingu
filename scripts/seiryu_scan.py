"""
🐉 青龍スキャナー δ v0.1
言霊（市場の声）：アナリスト推奨度 × EPSサプライズ × 目標株価アップサイド
データソース: yfinance Ticker info / earnings
出力: docs/seiryu_data.json
"""
import sys, subprocess, importlib, json, os, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

def ensure(pkgs):
    for p, mod in pkgs:
        try: importlib.import_module(mod)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install",
                                   "--break-system-packages", "--quiet", p])

ensure([("yfinance", "yfinance")])

import yfinance as yf
import warnings
warnings.filterwarnings("ignore")

REC_SCORE = {
    "strong_buy": 2, "strongbuy": 2, "buy": 2,
    "hold": 0, "neutral": 0,
    "underperform": -1, "sell": -2, "strong_sell": -2,
    "none": None,
}

def fetch_seiryu(ticker):
    try:
        tk = yf.Ticker(ticker)
        info = tk.info or {}

        # アナリスト推奨
        rec_key = (info.get("recommendationKey") or "none").lower()
        rec_score = REC_SCORE.get(rec_key, None)
        rec_mean = info.get("recommendationMean")  # 1=Strong Buy ... 5=Sell

        # 目標株価
        current = info.get("currentPrice") or info.get("regularMarketPrice")
        target_mean = info.get("targetMeanPrice")
        target_high = info.get("targetHighPrice")
        upside_pct = None
        if current and target_mean and current > 0:
            upside_pct = (target_mean - current) / current * 100

        # アナリスト数
        n_analysts = info.get("numberOfAnalystOpinions", 0) or 0

        # EPSサプライズ（簡易版：earnings.q growthから推定）
        eps_surprise = None
        try:
            qf = tk.earnings_dates
            if qf is not None and not qf.empty:
                qf_sorted = qf.sort_index(ascending=False)
                # 直近の確報があるもの
                for _, row in qf_sorted.iterrows():
                    actual = row.get("Reported EPS")
                    estimate = row.get("EPS Estimate")
                    if actual is not None and estimate is not None and estimate != 0:
                        eps_surprise = ((actual - estimate) / abs(estimate)) * 100
                        break
        except Exception:
            pass

        # grade判定
        signals = []
        if rec_mean is not None:
            if rec_mean <= 1.8: signals.append(2)         # Strong Buy寄り
            elif rec_mean <= 2.3: signals.append(1)       # Buy
            elif rec_mean <= 3.2: signals.append(0)       # Hold
            elif rec_mean <= 3.8: signals.append(-1)      # Underperform
            else: signals.append(-2)                       # Sell
        if upside_pct is not None:
            if upside_pct >= 30: signals.append(2)
            elif upside_pct >= 15: signals.append(1)
            elif upside_pct >= 0: signals.append(0)
            elif upside_pct >= -10: signals.append(-1)
            else: signals.append(-2)
        if eps_surprise is not None:
            if eps_surprise >= 20: signals.append(2)
            elif eps_surprise >= 5: signals.append(1)
            elif eps_surprise >= -5: signals.append(0)
            else: signals.append(-1)

        if not signals or n_analysts < 2:
            return ticker, {"grade": None, "note": "カバレッジ不足"}

        total = sum(signals)
        if total >= 5: grade = "S"
        elif total >= 3: grade = "A"
        elif total >= 1: grade = "B"
        elif total >= -1: grade = "C"
        else: grade = "D"

        note_parts = []
        if rec_mean is not None: note_parts.append(f"推奨{rec_mean:.1f}")
        if upside_pct is not None: note_parts.append(f"上昇余地{upside_pct:+.0f}%")
        if eps_surprise is not None: note_parts.append(f"EPS差{eps_surprise:+.0f}%")
        note = " / ".join(note_parts) + f" (n={n_analysts})"

        return ticker, {"grade": grade, "note": note,
                        "upside": round(upside_pct, 1) if upside_pct is not None else None,
                        "rec_mean": rec_mean,
                        "n_analysts": int(n_analysts)}
    except Exception as e:
        return ticker, {"grade": None, "note": f"err"}

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    filtered_path = os.path.join(here, "..", "docs", "filtered_universe.json")
    out_path = os.path.join(here, "..", "docs", "seiryu_data.json")

    if not os.path.exists(filtered_path):
        print("⚠️ filtered_universe.json なし。先に suzaku_scan.py を実行してください")
        return

    f = json.load(open(filtered_path, encoding="utf-8"))
    tickers = [r["ticker"] for r in f["tickers"]]
    print(f"🐉 青龍判定対象: {len(tickers)} 銘柄")

    results = {}
    done = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(fetch_seiryu, t): t for t in tickers}
        for fut in as_completed(futures):
            t, info = fut.result()
            results[t] = info
            done += 1
            if done % 20 == 0 or done == len(tickers):
                print(f"  進捗 {done}/{len(tickers)} ...")

    payload = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "generated_jst": (datetime.datetime.now(datetime.timezone.utc)
                          + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M JST"),
        "source": "yfinance recommendationKey + targetMeanPrice + EPS surprise",
        "metric": "アナリスト推奨×目標株価×EPSサプライズの合議",
        "seiryu": results,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)

    counts = {g: sum(1 for v in results.values() if v["grade"] == g)
              for g in ["S", "A", "B", "C", "D"]}
    print(f"\n🐉 青龍判定完了: S={counts['S']} A={counts['A']} B={counts['B']} C={counts['C']} D={counts['D']}")
    print(f"📜 書出: {out_path}")

if __name__ == "__main__":
    main()

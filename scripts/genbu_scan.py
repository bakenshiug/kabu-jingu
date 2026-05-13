"""
🐢 玄武スキャナー γ v0.1
業績モメンタム（売上成長率の水準＋加速度）から grade S/A/B/C/D を判定。
データソース: yfinance quarterly_financials
出力: docs/genbu_data.json
"""
import sys, subprocess, importlib, json, os, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

def ensure(pkgs):
    for p, mod in pkgs:
        try: importlib.import_module(mod)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install",
                                   "--break-system-packages", "--quiet", p])

ensure([("yfinance", "yfinance"), ("pandas", "pandas")])

import yfinance as yf
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

def fetch_genbu(ticker):
    """yfinanceから四半期売上を取得し、grade判定"""
    try:
        tk = yf.Ticker(ticker)
        qf = tk.quarterly_income_stmt
        if qf is None or qf.empty:
            return ticker, {"grade": None, "note": "データなし"}

        # 売上行を探す
        rev_keys = ["Total Revenue", "Revenue", "Operating Revenue"]
        rev = None
        for k in rev_keys:
            if k in qf.index:
                rev = qf.loc[k].dropna()
                break
        if rev is None or len(rev) < 5:
            return ticker, {"grade": None, "note": "売上履歴不足"}

        # 列を時系列ソート（新→旧）
        rev = rev.sort_index(ascending=False)
        vals = rev.values

        # YoY成長率（直近Q vs 4Q前）
        if len(vals) < 5: return ticker, {"grade": None, "note": "YoY計算不可"}
        latest = float(vals[0])
        year_ago = float(vals[4])
        if year_ago <= 0:
            return ticker, {"grade": None, "note": "前年Q売上ゼロ"}
        yoy = (latest - year_ago) / abs(year_ago) * 100

        # 前期YoY（1Q前 vs 5Q前）
        prev_yoy = None
        if len(vals) >= 6 and float(vals[5]) > 0:
            prev_yoy = (float(vals[1]) - float(vals[5])) / abs(float(vals[5])) * 100

        # grade判定
        accel = (prev_yoy is not None and yoy > prev_yoy)
        if yoy >= 30 and accel: grade = "S"
        elif yoy >= 30:         grade = "A"
        elif yoy >= 15:         grade = "A" if accel else "B"
        elif yoy >= 5:          grade = "B" if accel else "C"
        elif yoy >= 0:          grade = "C"
        else:                   grade = "D"

        accel_mark = "↑" if accel else ("→" if prev_yoy is not None and abs(yoy-prev_yoy)<1 else "↓")
        note = f"YoY {yoy:+.1f}% {accel_mark}"
        if prev_yoy is not None:
            note += f" (前期{prev_yoy:+.1f}%)"

        return ticker, {"grade": grade, "note": note, "yoy": round(yoy, 1)}
    except Exception as e:
        return ticker, {"grade": None, "note": f"err"}

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    filtered_path = os.path.join(here, "..", "docs", "filtered_universe.json")
    out_path = os.path.join(here, "..", "docs", "genbu_data.json")

    if not os.path.exists(filtered_path):
        print("⚠️ filtered_universe.json なし。先に suzaku_scan.py を実行してください")
        return

    f = json.load(open(filtered_path, encoding="utf-8"))
    tickers = [r["ticker"] for r in f["tickers"]]
    print(f"🐢 玄武判定対象: {len(tickers)} 銘柄（日米全数）")

    results = {}
    done = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(fetch_genbu, t): t for t in tickers}
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
        "source": "yfinance quarterly_income_stmt",
        "metric": "売上YoY成長率＋加速度",
        "genbu": results,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)

    counts = {g: sum(1 for v in results.values() if v["grade"] == g)
              for g in ["S", "A", "B", "C", "D"]}
    print(f"\n🐢 玄武判定完了: S={counts['S']} A={counts['A']} B={counts['B']} C={counts['C']} D={counts['D']}")
    print(f"📜 書出: {out_path}")

if __name__ == "__main__":
    main()

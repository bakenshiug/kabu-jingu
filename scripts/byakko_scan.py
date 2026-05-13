"""
🐅 白虎スキャナー β v0.1
インサイダー買い（米SEC Form 4）から grade S/A/B/C を判定。
データソース: openinsider.com（SEC Form 4を整形・公開）
出力: docs/byakko_data.json
"""
import sys, subprocess, importlib, json, os, time, re, datetime
from urllib.parse import quote

def ensure(pkgs):
    for p, mod in pkgs:
        try: importlib.import_module(mod)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install",
                                   "--break-system-packages", "--quiet", p])

ensure([("requests", "requests"), ("lxml", "lxml"), ("pandas", "pandas")])

import requests
import pandas as pd
from io import StringIO

HEADERS = {
    "User-Agent": "Mozilla/5.0 (UG-Kabu-Jingu Byakko/0.1 contact: bbwakase@gmail.com)",
    "Accept": "text/html,*/*",
}

OPENINSIDER_BASE = "http://openinsider.com/screener"

def fetch_insider(ticker, days=90):
    """openinsider から直近のインサイダー取引を取得。買い・売り両方含む。"""
    url = f"{OPENINSIDER_BASE}?s={quote(ticker)}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200: return []
        tables = pd.read_html(StringIO(r.text))
        if not tables: return []
        for t in tables:
            cols = [str(c).replace("\xa0", " ").strip() for c in t.columns]
            if "Trade Date" in cols and "Trade Type" in cols:
                t.columns = cols
                return parse_insider_table(t, days)
        return []
    except Exception as e:
        return []

def parse_insider_table(df, days=90):
    """openinsiderテーブルを正規化"""
    now = datetime.date.today()
    rows = []
    for _, r in df.iterrows():
        try:
            trans_type = str(r.get("Trade Type", ""))
            title = str(r.get("Title", ""))
            value = parse_dollar(str(r.get("Value", "")))
            qty = parse_int(str(r.get("Qty", "")))
            date_str = str(r.get("Trade Date", ""))[:10]
            insider = str(r.get("Insider Name", ""))
            if "Purchase" in trans_type: is_buy = True
            elif "Sale" in trans_type: is_buy = False
            else: continue
            # 直近days日のみ
            try:
                d = datetime.date.fromisoformat(date_str)
                if (now - d).days > days: continue
            except Exception:
                continue
            rows.append({
                "date": date_str,
                "insider": insider,
                "title": title,
                "is_buy": is_buy,
                "value": abs(value),
                "qty": qty,
            })
        except Exception:
            continue
    return rows

def parse_dollar(s):
    s = str(s).replace(",", "").replace("$", "").replace("+", "").strip()
    m = re.search(r"-?\d+\.?\d*", s)
    return float(m.group()) if m else 0.0

def parse_int(s):
    s = str(s).replace(",", "").replace("+", "").strip()
    m = re.search(r"-?\d+", s)
    return int(m.group()) if m else 0

def grade_byakko(transactions):
    """白虎grade判定。
    S: CEO/CFO/Chairmanが直近30日で買い増し（売却なし）
    A: 複数役員が直近30日で買い増し（クラスター買い）
    B: 役員レベルの単発買い
    C: 機関/10%超保有者の買い
    減点: CEO/CFOクラスの直近30日売却
    None: 該当なし
    """
    if not transactions:
        return None, "データなし"

    now = datetime.date.today()
    def days_ago(date_str):
        try:
            d = datetime.date.fromisoformat(date_str)
            return (now - d).days
        except Exception:
            return 9999

    recent30_buys = [t for t in transactions if t["is_buy"] and days_ago(t["date"]) <= 30]
    recent30_sells = [t for t in transactions if not t["is_buy"] and days_ago(t["date"]) <= 30]

    def is_top_exec(title):
        t = title.upper()
        return any(k in t for k in ["CEO", "CFO", "PRESIDENT", "CHAIRMAN", "CHIEF EXECUTIVE",
                                     "CHIEF FINANCIAL", "FOUNDER"])
    def is_director(title):
        t = title.upper()
        return any(k in t for k in ["DIRECTOR", "OFFICER", "VP", "VICE PRESIDENT", "OFFICER"])
    def is_big_holder(title):
        return "10%" in title or "Beneficial" in title or "Holder" in title

    top_buys = [t for t in recent30_buys if is_top_exec(t["title"])]
    top_sells = [t for t in recent30_sells if is_top_exec(t["title"])]
    director_buys = [t for t in recent30_buys if is_director(t["title"]) and not is_top_exec(t["title"])]
    holder_buys = [t for t in recent30_buys if is_big_holder(t["title"])]

    total_buy_value = sum(t["value"] for t in recent30_buys)
    total_sell_value = sum(t["value"] for t in recent30_sells)

    # 致命減点: CEO/CFO売却が買いを上回る
    if top_sells and sum(t["value"] for t in top_sells) > total_buy_value:
        return "D", f"幹部売却超過 -${sum(t['value'] for t in top_sells)/1e6:.1f}M"

    # S: CEO/CFOクラスの買い・売却なし
    unique_top_buyers = len(set(t["insider"] for t in top_buys))
    if top_buys and not top_sells:
        if unique_top_buyers >= 2 or total_buy_value >= 1_000_000:
            return "S", f"幹部買い ${total_buy_value/1e6:.2f}M ({unique_top_buyers}名)"
        return "A", f"幹部買い ${total_buy_value/1e6:.2f}M"

    # A: 複数役員クラスター買い
    unique_director_buyers = len(set(t["insider"] for t in director_buys))
    if unique_director_buyers >= 2:
        return "A", f"クラスター買い ${total_buy_value/1e6:.2f}M ({unique_director_buyers}名)"

    # B: 単発役員買い
    if director_buys:
        return "B", f"役員買い ${total_buy_value/1e6:.2f}M"

    # C: 大株主買い
    if holder_buys:
        return "C", f"大株主買い ${total_buy_value/1e6:.2f}M"

    return None, "シグナルなし"

def fetch_one(t):
    """並列化用ワーカー"""
    try:
        trans = fetch_insider(t, days=90)
        grade, note = grade_byakko(trans)
        return t, {"grade": grade, "note": note}
    except Exception as e:
        return t, {"grade": None, "note": f"err: {e}"}

def main():
    # filtered_universe.json から全フィルタ通過銘柄を白虎対象に
    here = os.path.dirname(os.path.abspath(__file__))
    filtered_path = os.path.join(here, "..", "docs", "filtered_universe.json")
    signals_path = os.path.join(here, "..", "docs", "signals.json")
    out_path = os.path.join(here, "..", "docs", "byakko_data.json")

    us_tickers = []
    if os.path.exists(filtered_path):
        f = json.load(open(filtered_path, encoding="utf-8"))
        us_tickers = [r["ticker"] for r in f["tickers"] if r["market"] == "us"]
        print(f"🐅 白虎全銘柄カバレッジ: {len(us_tickers)} 米国銘柄（filtered_universe）")
    elif os.path.exists(signals_path):
        sig = json.load(open(signals_path, encoding="utf-8"))
        us_tickers = [s["ティッカー"] for s in sig["signals"]
                      if not s["ティッカー"].endswith(".T")]
        print(f"🐅 白虎判定対象: {len(us_tickers)} 米国銘柄（signals.jsonフォールバック）")
    else:
        print("⚠️ filtered_universe.json も signals.json もなし")
        return

    results = {}
    from concurrent.futures import ThreadPoolExecutor, as_completed
    # openinsider 礼儀: 並列度4・各リクエスト間に少し間隔
    done = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(fetch_one, t): t for t in us_tickers}
        for fut in as_completed(futures):
            t, info = fut.result()
            results[t] = info
            done += 1
            if done % 10 == 0 or done == len(us_tickers):
                print(f"  進捗 {done}/{len(us_tickers)} ...")

    payload = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "generated_jst": (datetime.datetime.now(datetime.timezone.utc)
                          + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M JST"),
        "source": "openinsider.com",
        "lookback_days": 90,
        "byakko": results,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    s_count = sum(1 for v in results.values() if v["grade"] == "S")
    a_count = sum(1 for v in results.values() if v["grade"] == "A")
    b_count = sum(1 for v in results.values() if v["grade"] == "B")
    print(f"\n🐅 白虎判定完了: S={s_count} A={a_count} B={b_count}")
    print(f"📜 書出: {out_path}")

if __name__ == "__main__":
    main()

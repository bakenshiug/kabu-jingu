"""
🇯🇵🐅 日本版白虎スキャナー（軽量版・kabutanニュース材料判定）
86銘柄の日本半導体テーマ株に対して、kabutan.jpのニュース材料から
「白虎シグナル」（自社株買い・大量保有・TOB等）を検出してgrade付与。

データソース: kabutan.jp 各銘柄のニュース一覧（公開ページ）
出力: docs/jp_byakko_data.json
"""
import sys, subprocess, importlib, json, os, re, time, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

def ensure(pkgs):
    for p, mod in pkgs:
        try: importlib.import_module(mod)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install",
                                   "--break-system-packages", "--quiet", p])

ensure([("requests", "requests")])

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (UG-Kabu-Jingu JP-Byakko/0.1 contact: bbwakase@gmail.com)",
    "Accept": "text/html,application/xhtml+xml",
}

# 白虎キーワード（強度別）
HIGH_KEYWORDS = [
    "自社株買い", "自己株式取得", "自己株取得",
    "MBO", "公開買付", "ＴＯＢ",
    "ストックオプション", "自社株消却",
]
MED_KEYWORDS = [
    "大量保有報告", "大量保有変更",
    "投資ファンド", "アクティビスト",
    "業務提携", "資本提携",
]
LOW_KEYWORDS = [
    "上方修正", "業績修正", "配当増",
    "増配", "予想据え置き", "決算予想",
]

def fetch_kabutan_news(code):
    """kabutan.jp の銘柄ニュースを取得。直近30日分"""
    url = f"https://kabutan.jp/stock/news?code={code}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200: return []
        # news_list テーブルから記事を抽出
        m = re.search(r'<table class="s_news_list[^"]*"(.*?)</table>',
                      r.text, re.DOTALL)
        if not m: return []
        items = re.findall(
            r'<time datetime="([^"]+)">[^<]*</time>'
            r'.*?<div class="newslist_ctg[^"]*">([^<]*)</div>'
            r'.*?<a[^>]*>([^<]+)</a>',
            m.group(1), re.DOTALL
        )
        # 直近30日でフィルタ
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
        results = []
        for dt_str, cat, title in items:
            try:
                dt = datetime.datetime.fromisoformat(dt_str)
                if dt < cutoff: continue
                results.append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "category": cat.strip(),
                    "title": title.strip(),
                })
            except Exception:
                continue
        return results
    except Exception:
        return []

def grade_jp_byakko(news_list):
    """ニュース材料から白虎grade判定。"""
    if not news_list:
        return None, "ニュースなし"

    high_hits, med_hits, low_hits = [], [], []
    for n in news_list:
        title = n["title"]
        if any(k in title for k in HIGH_KEYWORDS):
            high_hits.append(n)
        elif any(k in title for k in MED_KEYWORDS):
            med_hits.append(n)
        elif any(k in title for k in LOW_KEYWORDS):
            low_hits.append(n)

    # Grade判定
    # S: 自社株買い・MBO・TOB等の強材料2件以上 or 1件＋中強度2件
    # A: 強材料1件 or 中強度2件以上
    # B: 中強度1件 or 低強度3件以上
    # C: 低強度1-2件
    # 該当なし: None
    if len(high_hits) >= 2 or (len(high_hits) >= 1 and len(med_hits) >= 2):
        topic = high_hits[0]["title"][:30]
        return "S", f"強材料{len(high_hits)}件+中{len(med_hits)}件: {topic}"
    if len(high_hits) >= 1:
        topic = high_hits[0]["title"][:30]
        return "A", f"強材料: {topic}"
    if len(med_hits) >= 2:
        topic = med_hits[0]["title"][:30]
        return "A", f"中材料{len(med_hits)}件: {topic}"
    if len(med_hits) >= 1:
        topic = med_hits[0]["title"][:30]
        return "B", f"中材料: {topic}"
    if len(low_hits) >= 3:
        return "C", f"業績材料{len(low_hits)}件"
    if len(low_hits) >= 1:
        return None, f"業績材料{len(low_hits)}件のみ"
    return None, "白虎材料なし"

def fetch_one(t):
    """並列化用ワーカー"""
    code = t.replace(".T", "")
    try:
        news = fetch_kabutan_news(code)
        grade, note = grade_jp_byakko(news)
        return t, {
            "grade": grade,
            "note": note,
            "news_count": len(news),
        }
    except Exception:
        return t, {"grade": None, "note": "err"}

def load_jp_semi_tickers():
    """suzaku_scan.py の JP_SEMI_TICKERS を読み込む（簡易パース）"""
    here = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(here, "suzaku_scan.py")
    with open(script, encoding="utf-8") as f:
        text = f.read()
    m = re.search(r'JP_SEMI_TICKERS\s*=\s*\{(.*?)\}', text, re.DOTALL)
    if not m: return []
    tickers = re.findall(r'"(\d{3,4}[A-Z]?\.T)"', m.group(1))
    return list(set(tickers))

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(here, "..", "docs", "jp_byakko_data.json")

    tickers = load_jp_semi_tickers()
    print(f"🇯🇵🐅 日本版白虎判定対象: {len(tickers)} 銘柄（jp_semi 特設リスト）")

    results = {}
    done = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(fetch_one, t): t for t in tickers}
        for fut in as_completed(futures):
            t, info = fut.result()
            results[t] = info
            done += 1
            if done % 10 == 0 or done == len(tickers):
                print(f"  進捗 {done}/{len(tickers)} ...")

    payload = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "generated_jst": (datetime.datetime.now(datetime.timezone.utc)
                          + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M JST"),
        "source": "kabutan.jp news scraping",
        "lookback_days": 30,
        "scope": "JP_SEMI_TICKERS (86銘柄)",
        "byakko": results,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    counts = {g: sum(1 for v in results.values() if v["grade"] == g)
              for g in ["S", "A", "B", "C"]}
    print(f"\n🇯🇵🐅 日本版白虎判定完了: S={counts['S']} A={counts['A']} B={counts['B']} C={counts['C']}")
    print(f"📜 書出: {out_path}")

if __name__ == "__main__":
    main()

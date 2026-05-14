"""
Mega Scanner: 日米横断 蓄電池/半導体/テック Williams %R スクリーナー
- 母集団: S&P500 + NASDAQ100 + 日経225
- フィルタ: Semiconductor / Quantum / Aerospace / Battery / Energy / Material 等
- シグナル: Williams %R(14)  A: <=-80  B: -30 <= x <= -20
"""
import sys
import subprocess
import importlib

def ensure(pkgs):
    for p, mod in pkgs:
        try:
            importlib.import_module(mod)
        except ImportError:
            print(f"installing {p}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install",
                                   "--break-system-packages", "--quiet", p])

ensure([("yfinance", "yfinance"), ("pandas", "pandas"),
        ("lxml", "lxml"), ("requests", "requests")])

import pandas as pd
import yfinance as yf
import requests
import io
import time
import warnings
warnings.filterwarnings("ignore")

KEYWORDS = [
    # 半導体
    "semiconductor", "半導体", "chip", "wafer", "lithography", "fab", "foundry",
    "photonic", "photonics", "電子部品",
    # 量子
    "quantum", "量子", "qubit",
    # 宇宙・航空・防衛
    "aerospace", "航空宇宙", "宇宙", "space ", "spacemobile", "satellite", "衛星",
    "rocket", "ロケット", "drone", "ドローン", "defense", "防衛", "lunar",
    "orbital", "spacecraft", "ionq", "rigetti",
    # 電池・蓄電池
    "battery", "蓄電", "電池", "lithium", "リチウム", "全固体", "solid-state",
    # エネルギー
    "energy", "エネルギー", "nuclear", "原子力", "fusion", "核融合",
    "uranium", "ウラン", "solar", "太陽光", "wind", "風力", "再エネ", "renewable",
    "hydrogen", "水素", "fuel cell", "燃料電池", "geothermal", "地熱",
    "電力", "ガス", "石油", "lng",
    # 素材
    "material", "素材", "rare earth", "希土類", "chemical", "化学",
    "polymer", "ceramic", "metal", "金属", "鉱業", "mining", "rare metals",
    # EV・モビリティ
    "ev ", "electric vehicle", "automotive", "自動車", "evtol", "evtol",
    # AI・ロボット
    "ai ", "artificial intelligence", "人工知能", "robot", "ロボット", "ロボ",
    "automation", "オートメーション", "machine learning",
    # 新興・テンバガー領域
    "biotech", "バイオ", "gene", "cell ", "細胞",
    "blockchain", "crypto", "fintech", "saas", "cloud",
    # テック系（IPO銘柄を網羅）
    "テック", "tech",
]

# 特定銘柄ホワイトリスト（キーワード漏れ救済）
WHITELIST_TICKERS = {
    "464A.T",   # QPSホールディングス（衛星）
    "278A.T",   # Terra Drone（ドローン）
    "186A.T",   # アストロスケール
    "9348.T",   # ispace
    "5595.T",   # QPS研究所（旧コード）
    "4475.T",   # HENNGE
    "3993.T",   # PKSHA
    "4382.T",   # HEROZ
}

HEADERS = {"User-Agent": "Mozilla/5.0"}

def get_sp500():
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(io.StringIO(requests.get(url, headers=HEADERS, timeout=20).text))
        df = tables[0][["Symbol", "Security", "GICS Sector", "GICS Sub-Industry"]].copy()
        df.columns = ["ticker", "name", "sector", "industry"]
        df["ticker"] = df["ticker"].str.replace(".", "-", regex=False)
        df["market"] = "US-SP500"
        return df
    except Exception as e:
        print("SP500 fetch failed:", e); return pd.DataFrame()

def get_nasdaq100():
    try:
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        tables = pd.read_html(io.StringIO(requests.get(url, headers=HEADERS, timeout=20).text))
        target = None
        for t in tables:
            cols = [str(c).lower() for c in t.columns]
            if any("ticker" in c or "symbol" in c for c in cols) and any("company" in c or "security" in c for c in cols):
                target = t; break
        if target is None: return pd.DataFrame()
        cols = {c: str(c).lower() for c in target.columns}
        tcol = next(c for c, l in cols.items() if "ticker" in l or "symbol" in l)
        ncol = next(c for c, l in cols.items() if "company" in l or "security" in l)
        scol = next((c for c, l in cols.items() if "sector" in l or "gics" in l), None)
        icol = next((c for c, l in cols.items() if "industry" in l or "sub" in l), None)
        df = pd.DataFrame({
            "ticker": target[tcol].astype(str),
            "name": target[ncol].astype(str),
            "sector": target[scol].astype(str) if scol else "",
            "industry": target[icol].astype(str) if icol else "",
        })
        df["market"] = "US-NDX100"
        return df
    except Exception as e:
        print("NDX100 fetch failed:", e); return pd.DataFrame()

def get_nikkei225_wiki():
    """日本語版WikipediaのNikkei225構成銘柄を取得。"""
    try:
        url = "https://ja.wikipedia.org/wiki/%E6%97%A5%E7%B5%8C%E5%B9%B3%E5%9D%87%E6%A0%AA%E4%BE%A1"
        html = requests.get(url, headers=HEADERS, timeout=20).text
        tables = pd.read_html(io.StringIO(html))
        rows = []
        for t in tables:
            cols = [str(c) for c in t.columns]
            joined = " ".join(cols)
            if ("コード" in joined or "Code" in joined) and ("銘柄" in joined or "会社" in joined or "Company" in joined):
                tcol = next((c for c in t.columns if "コード" in str(c) or "Code" in str(c)), None)
                ncol = next((c for c in t.columns if "銘柄" in str(c) or "会社" in str(c) or "Company" in str(c)), None)
                scol = next((c for c in t.columns if "業種" in str(c) or "セクター" in str(c)), None)
                if tcol is None or ncol is None: continue
                for _, r in t.iterrows():
                    code = str(r[tcol])
                    m = pd.Series([code]).str.extract(r"(\d{4})")[0].iloc[0]
                    if pd.isna(m): continue
                    rows.append({
                        "ticker": f"{m}.T",
                        "name": str(r[ncol]),
                        "sector": str(r[scol]) if scol else "",
                        "industry": "",
                        "market": "JP-N225",
                    })
        return pd.DataFrame(rows)
    except Exception as e:
        print("N225 wiki fetch failed:", e); return pd.DataFrame()

# 米国小型成長銘柄（量子・宇宙・次世代電池・原子力・AI・先端半導体）
US_VENTURE = [
    # 量子コンピュータ
    ("IONQ", "IonQ Inc", "Quantum"),
    ("RGTI", "Rigetti Computing", "Quantum"),
    ("QBTS", "D-Wave Quantum", "Quantum"),
    ("QUBT", "Quantum Computing Inc", "Quantum"),
    ("ARQQ", "Arqit Quantum", "Quantum"),
    # 宇宙・航空
    ("RKLB", "Rocket Lab USA", "Aerospace"),
    ("ASTS", "AST SpaceMobile", "Aerospace"),
    ("LUNR", "Intuitive Machines", "Aerospace"),
    ("PL", "Planet Labs", "Aerospace"),
    ("SPIR", "Spire Global", "Aerospace"),
    ("RDW", "Redwire Corp", "Aerospace"),
    ("BKSY", "BlackSky Technology", "Aerospace"),
    ("ACHR", "Archer Aviation", "Aerospace"),
    ("JOBY", "Joby Aviation", "Aerospace"),
    ("KTOS", "Kratos Defense", "Aerospace"),
    # 次世代電池・蓄電池
    ("QS", "QuantumScape", "Battery"),
    ("MVST", "Microvast", "Battery"),
    ("ENVX", "Enovix", "Battery"),
    ("SLDP", "Solid Power", "Battery"),
    ("AMPX", "Amprius Technologies", "Battery"),
    ("FREY", "FREYR Battery", "Battery"),
    ("STEM", "Stem Inc", "Battery/Energy"),
    # 先端半導体・フォトニクス
    ("ATOM", "Atomera", "Semiconductor"),
    ("POET", "POET Technologies", "Semiconductor"),
    ("NVTS", "Navitas Semiconductor", "Semiconductor"),
    ("ACMR", "ACM Research", "Semiconductor"),
    ("AEHR", "Aehr Test Systems", "Semiconductor"),
    ("INDI", "indie Semiconductor", "Semiconductor"),
    ("LWLG", "Lightwave Logic", "Semiconductor"),
    # 小型原子力・核融合
    ("OKLO", "Oklo Inc", "Energy/Nuclear"),
    ("SMR", "NuScale Power", "Energy/Nuclear"),
    ("NNE", "Nano Nuclear Energy", "Energy/Nuclear"),
    ("LEU", "Centrus Energy", "Energy/Nuclear"),
    ("UEC", "Uranium Energy", "Energy/Nuclear"),
    ("CCJ", "Cameco", "Energy/Nuclear"),
    ("BWXT", "BWX Technologies", "Energy/Nuclear"),
    # AI/量子隣接
    ("SOUN", "SoundHound AI", "AI/Tech"),
    ("BBAI", "BigBear.ai", "AI/Tech"),
    ("AI", "C3.ai", "AI/Tech"),
    # 素材・水素
    ("MP", "MP Materials", "Material/Rare Earth"),
    ("REE", "REE Automotive", "Material"),
    ("PLUG", "Plug Power", "Energy/Hydrogen"),
    ("BE", "Bloom Energy", "Energy"),
    ("BLDP", "Ballard Power", "Energy/Hydrogen"),
]

# 主要セクター銘柄（日本株キュレーション。Wikipedia取得失敗時の保険＆カバレッジ補完）
JP_CURATED = [
    # 半導体
    ("8035.T", "東京エレクトロン", "半導体"),
    ("6857.T", "アドバンテスト", "半導体"),
    ("6920.T", "レーザーテック", "半導体"),
    ("6963.T", "ローム", "半導体"),
    ("6526.T", "ソシオネクスト", "半導体"),
    ("6890.T", "フェローテック", "半導体"),
    ("7735.T", "SCREENホールディングス", "半導体"),
    ("6areas.T", "", ""),  # placeholder removed below
    ("6areas2.T", "", ""),
    ("6areas3.T", "", ""),
    ("3436.T", "SUMCO", "半導体素材"),
    ("4063.T", "信越化学工業", "半導体素材"),
    ("5631.T", "日本製鋼所", "半導体"),
    ("7741.T", "HOYA", "半導体素材"),
    ("8036.T", "日立ハイテク", "半導体"),
    ("6324.T", "ハーモニック", "精密"),
    ("7752.T", "リコー", "テック"),
    ("6707.T", "サンケン電気", "半導体"),
    ("6areas4.T", "", ""),
    ("4185.T", "JSR", "半導体素材"),
    ("4186.T", "東京応化工業", "半導体素材"),
    ("3silinx.T", "", ""),
    ("6areas5.T", "", ""),
    # 電池・蓄電池
    ("6674.T", "ジーエス・ユアサ コーポレーション", "蓄電池"),
    ("6areas6.T", "", ""),
    ("4901.T", "富士フイルム", "素材"),
    ("4188.T", "三菱ケミカル", "素材・電池"),
    ("3402.T", "東レ", "素材・電池"),
    ("4042.T", "東ソー", "素材"),
    ("4061.T", "デンカ", "素材"),
    ("5resona.T", "", ""),
    ("4204.T", "積水化学工業", "素材・エネルギー"),
    ("5108.T", "ブリヂストン", "素材"),
    ("7203.T", "トヨタ自動車", "EV・蓄電池"),
    ("7267.T", "ホンダ", "EV・蓄電池"),
    ("7201.T", "日産自動車", "EV・蓄電池"),
    ("6areas7.T", "", ""),
    ("6areas8.T", "", ""),
    ("6areas9.T", "", ""),
    ("6areasA.T", "", ""),
    ("6areasB.T", "", ""),
    ("6areasC.T", "", ""),
    ("6areasD.T", "", ""),
    # 航空宇宙
    ("7011.T", "三菱重工業", "航空宇宙・エネルギー"),
    ("7012.T", "川崎重工業", "航空宇宙"),
    ("7013.T", "IHI", "航空宇宙"),
    ("6areasE.T", "", ""),
    ("7269.T", "スズキ", "輸送機器"),
    ("9301.T", "三菱倉庫", "物流"),
    # エネルギー
    ("9501.T", "東京電力ホールディングス", "エネルギー"),
    ("9502.T", "中部電力", "エネルギー"),
    ("9503.T", "関西電力", "エネルギー"),
    ("9531.T", "東京ガス", "エネルギー"),
    ("9532.T", "大阪ガス", "エネルギー"),
    ("5020.T", "ENEOSホールディングス", "エネルギー"),
    ("5019.T", "出光興産", "エネルギー"),
    ("1605.T", "INPEX", "エネルギー"),
    ("1662.T", "石油資源開発", "エネルギー"),
    ("9513.T", "Jパワー", "エネルギー"),
    ("9508.T", "九州電力", "エネルギー"),
    ("9504.T", "中国電力", "エネルギー"),
    ("9505.T", "北陸電力", "エネルギー"),
    ("9506.T", "東北電力", "エネルギー"),
    ("9507.T", "四国電力", "エネルギー"),
    ("9509.T", "北海道電力", "エネルギー"),
    ("9511.T", "沖縄電力", "エネルギー"),
    # 素材
    ("5401.T", "日本製鉄", "素材・鉄鋼"),
    ("5411.T", "JFEホールディングス", "素材・鉄鋼"),
    ("5713.T", "住友金属鉱山", "素材"),
    ("5714.T", "DOWAホールディングス", "素材"),
    ("5802.T", "住友電気工業", "素材"),
    ("5803.T", "フジクラ", "素材"),
    ("3401.T", "帝人", "素材"),
    ("4005.T", "住友化学", "素材"),
    ("4004.T", "レゾナック・ホールディングス", "素材・半導体"),
    ("4021.T", "日産化学", "素材"),
    ("4452.T", "花王", "素材"),
    ("4183.T", "三井化学", "素材"),
    ("3407.T", "旭化成", "素材・電池"),
    ("5803.T", "フジクラ", "素材"),
    ("5333.T", "日本ガイシ", "素材・蓄電池"),
    # 量子・先端テック
    ("6areasF.T", "", ""),
    ("3692.T", "FFRI セキュリティ", "テック"),
    ("4spiber.T", "", ""),
]

def get_japan_curated():
    rows = [{"ticker": t, "name": n, "sector": s, "industry": "", "market": "JP-CURATED"}
            for t, n, s in JP_CURATED if n]
    return pd.DataFrame(rows)

# 日本グロース・スタンダード市場の量子/宇宙/電池/半導体ベンチャー
JP_GROWTH = [
    # 量子・光・先端デバイス
    ("6521.T", "オキサイド", "量子・光半導体"),
    ("4393.T", "バンク・オブ・イノベーション", "テック"),
    ("6areas.T", "", ""),
    # 宇宙・航空
    ("186A.T", "アストロスケールホールディングス", "航空宇宙"),
    ("9348.T", "ispace", "航空宇宙"),
    ("5595.T", "QPS研究所", "航空宇宙"),
    ("7741b.T", "", ""),
    # 蓄電池・電池素材ベンチャー
    ("4880.T", "セルソース", "素材"),
    ("4598.T", "Delta-Fly Pharma", ""),
    ("6areas2.T", "", ""),
    ("3volt.T", "", ""),
    ("4395.T", "アクリート", ""),
    # 半導体製造装置・部材ベンチャー
    ("6525.T", "KOKUSAI ELECTRIC", "半導体"),
    ("6areas3.T", "", ""),
    ("6areas4.T", "", ""),
    ("4218.T", "ニチバン", ""),
    ("6areas5.T", "", ""),
    ("3awg.T", "", ""),
    # エネルギー・水素・再エネ
    ("9519.T", "レノバ", "エネルギー・再エネ"),
    ("1407.T", "ウエストホールディングス", "エネルギー・太陽光"),
    ("9514.T", "エフオン", "エネルギー"),
    ("1377.T", "サカタのタネ", ""),
    # 素材・新素材
    ("4395b.T", "", ""),
    ("4ferro.T", "", ""),
    # 防衛・航空関連ミッドキャップ
    ("6insouken.T", "", ""),
    ("7240.T", "NOK", "素材"),
    # AI・量子隣接日本
    ("3993.T", "PKSHA Technology", "AI/テック"),
    ("4475.T", "HENNGE", "テック"),
    ("4382.T", "HEROZ", "AI"),
    # 核融合・原子力
    ("1928.T", "積水ハウス", ""),
    ("1719.T", "安藤・間", ""),
    ("6areas6.T", "", ""),
]

def get_japan_growth():
    rows = [{"ticker": t, "name": n, "sector": s, "industry": "", "market": "JP-GROWTH"}
            for t, n, s in JP_GROWTH if n]
    return pd.DataFrame(rows)

def get_japan():
    parts = []
    w = get_nikkei225_wiki()
    print(f"  Nikkei225(wiki): {len(w)} 銘柄")
    if not w.empty: parts.append(w)
    c = get_japan_curated()
    print(f"  日本プライムキュレーション: {len(c)} 銘柄")
    parts.append(c)
    g = get_japan_growth()
    print(f"  日本グロース/小型: {len(g)} 銘柄")
    parts.append(g)
    df = pd.concat(parts, ignore_index=True).drop_duplicates(subset=["ticker"])
    return df

def get_us_venture():
    rows = [{"ticker": t, "name": n, "sector": s, "industry": "", "market": "US-VENTURE"}
            for t, n, s in US_VENTURE if n]
    return pd.DataFrame(rows)

def get_nasdaq_all():
    """NASDAQ trader からNYSE/NASDAQ全上場銘柄を取得。約7000銘柄。"""
    rows = []
    sources = [
        ("https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt", "NASDAQ"),
        ("https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt", "NYSE/AMEX"),
    ]
    for url, market in sources:
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code != 200: continue
            for line in r.text.splitlines()[1:]:  # スキップヘッダ
                if not line or line.startswith("File Creation"): continue
                parts = line.split("|")
                if len(parts) < 2: continue
                ticker = parts[0].strip()
                name = parts[1].strip()
                # ETF・テスト銘柄・SPAC等の除外
                if not ticker or "$" in ticker or ticker.endswith("W") or ticker.endswith("U"):
                    continue
                # Y, R, P等の優先株/ワラント記号で終わるものは除外
                if len(ticker) >= 5 and ticker[-1] in "WURP" and "." not in ticker:
                    continue
                # 名前にETF/Fund/Trust/SPAC等が含まれるものを除外
                low = name.lower()
                if any(k in low for k in [" etf", "exchange-traded", " fund ", " trust ",
                                           "warrant", "depositary", "preferred shares",
                                           "acquisition corp", "acquisition inc",
                                           "blank check"]):
                    continue
                rows.append({
                    "ticker": ticker,
                    "name": name,
                    "sector": "",
                    "industry": "",
                    "market": f"US-{market}",
                })
        except Exception as e:
            print(f"  NASDAQ {market} fetch error: {e}")
    return pd.DataFrame(rows)

def get_jpx_all():
    """JPX 上場会社一覧（Excel）を取得。約3800銘柄。"""
    url = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200: return pd.DataFrame()
        # xlsバイナリ → pandas
        try: importlib.import_module("xlrd")
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install",
                                   "--break-system-packages", "--quiet", "xlrd"])
        df = pd.read_excel(io.BytesIO(r.content))
        # 列名候補
        code_col = next((c for c in df.columns if "コード" in str(c) or "Code" in str(c)), None)
        name_col = next((c for c in df.columns if "銘柄名" in str(c) or "会社名" in str(c) or "Name" in str(c)), None)
        sec_col  = next((c for c in df.columns if "業種" in str(c) or "Sector" in str(c)), None)
        mkt_col  = next((c for c in df.columns if "市場" in str(c) and "区分" in str(c)), None)
        if code_col is None or name_col is None:
            return pd.DataFrame()
        rows = []
        for _, r in df.iterrows():
            code = str(r[code_col]).strip()
            # 4文字コード採用（4桁数字 or 3桁数字+1英字 例: 278A, 464A, 186A）
            if len(code) != 4: continue
            if not (code.isdigit() or (code[:3].isdigit() and code[3].isalpha())):
                continue
            mkt = str(r[mkt_col]) if mkt_col else ""
            # ETF/REIT除外
            if "ETF" in mkt or "REIT" in mkt or "ETN" in mkt:
                continue
            rows.append({
                "ticker": f"{code}.T",
                "name": str(r[name_col]),
                "sector": str(r[sec_col]) if sec_col else "",
                "industry": mkt,
                "market": f"JP-{mkt}" if mkt_col else "JP",
            })
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"  JPX fetch error: {e}")
        return pd.DataFrame()

def matches_keyword(row):
    ticker = str(row.get("ticker", ""))
    market = str(row.get("market", ""))
    if ticker in WHITELIST_TICKERS:
        return True
    # 主要指数構成銘柄は無条件で通す（Nikkei225/SP500/NDX100/Venture/Curated）
    if any(idx in market for idx in ["N225", "SP500", "NDX100", "VENTURE", "CURATED", "GROWTH"]):
        return True
    blob = " ".join([str(row.get("sector", "")), str(row.get("industry", "")),
                     str(row.get("name", ""))]).lower()
    return any(k in blob for k in KEYWORDS)

# テーマタグ判定（X人気4本柱）
THEME_RULES = [
    ("quantum",  ["quantum", "量子", "ionq", "rigetti", "d-wave", "qubit", "qbts", "qubt", "arqq", "oxide", "オキサイド"]),
    ("space",    ["aerospace", "space", "satellite", "航空宇宙", "宇宙", "rocket", "rkla", "rklb", "rocket lab",
                  "asts", "spacemobile", "intuitive machines", "lunr", "planet labs", "spire", "redwire",
                  "blacksky", "kratos", "northrop", "lockheed", "rtx", "general dynamics", "boeing",
                  "三菱重工", "川崎重工", "ihi", "アストロスケール", "ispace", "qps", "axon",
                  "archer", "joby", "bwx"]),
    ("semi",     ["semiconductor", "半導体", "chip", "wafer", "lithography", "fab",
                  "atomera", "atom", "poet", "navitas", "acm research", "aehr", "indie semi",
                  "lightwave", "東京エレクトロン", "アドバンテスト", "レーザーテック", "sumco",
                  "信越化学", "ローム", "ソシオネクスト", "フェローテック", "screen", "kokusai",
                  "hoya", "日立ハイテク", "jsr", "東京応化", "klac", "kla", "applied materials",
                  "lam research", "tsm", "nvidia", "amd", "intel", "micron", "analog devices",
                  "marvell", "broadcom", "asml", "qualcomm", "テキサス", "qnity"]),
    ("battery",  ["battery", "蓄電", "lithium", "電池", "全固体",
                  "quantumscape", "qs", "solid power", "sldp", "enovix", "envx",
                  "amprius", "ampx", "microvast", "mvst", "freyr", "frey",
                  "ジーエス", "ユアサ", "gs yuasa", "セルソース", "stem",
                  "panasonic", "パナソニック", "ev", "electric vehicle"]),
    ("energy",   ["energy", "エネルギー", "nuclear", "uranium", "原子力", "core",
                  "oklo", "nuscale", "smr", "nano nuclear", "nne", "centrus", "leu",
                  "uec", "cameco", "ccj", "plug power", "bloom energy", "ballard",
                  "電力", "ガス", "電気", "再エネ", "太陽光", "hydrogen", "水素",
                  "constellation", "exxon", "chevron", "marathon", "eqt", "duke",
                  "schlumberger", "halliburton", "valero", "phillips", "occidental",
                  "kinder", "williams", "oneok", "leno", "inpex", "出光"]),
    ("material", ["material", "素材", "rare earth", "希土類", "mp materials", "ree",
                  "linde", "ecolab", "sherwin", "ppg", "vulcan", "martin marietta",
                  "ball corp", "avery", "crh", "mosaic", "steel dynamics", "cf industries",
                  "nucor", "freeport", "dow", "lyondell", "dupont", "albemarle",
                  "東レ", "三菱ケミカル", "東ソー", "デンカ", "積水化学", "ブリヂストン",
                  "住友化学", "旭化成", "三井化学", "日産化学", "日本製鉄", "jfe",
                  "住友金属", "dowa", "住友電気", "フジクラ", "帝人", "レゾナック",
                  "日本ガイシ"]),
]

def assign_theme(row):
    """銘柄のテーマタグを判定。複数候補から最優先1つを返す（量子>宇宙>半導体>電池>原子力エネ>素材）"""
    blob = " ".join([str(row.get("sector", "")), str(row.get("industry", "")),
                     str(row.get("name", "")), str(row.get("ticker", ""))]).lower()
    for theme, kws in THEME_RULES:
        if any(k in blob for k in kws):
            return theme
    return "other"

THEME_LABELS = {
    "quantum":  "🧮 量子",
    "space":    "🛰 防衛宇宙",
    "semi":     "⚡ 半導体",
    "battery":  "🔋 次世代電池",
    "energy":   "⛽ エネルギー",
    "material": "🧱 素材",
    "other":    "その他",
}

def williams_r(high, low, close, period=14):
    hh = high.rolling(period).max()
    ll = low.rolling(period).min()
    return -100 * (hh - close) / (hh - ll)

def rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-9)
    return 100 - 100 / (1 + rs)

def macd(close, fast=12, slow=26, signal=9):
    ema_f = close.ewm(span=fast, adjust=False).mean()
    ema_s = close.ewm(span=slow, adjust=False).mean()
    line = ema_f - ema_s
    sig = line.ewm(span=signal, adjust=False).mean()
    hist = line - sig
    return line, sig, hist

def stochastic(high, low, close, k=14, d=3):
    ll = low.rolling(k).min()
    hh = high.rolling(k).max()
    kline = 100 * (close - ll) / (hh - ll).replace(0, 1e-9)
    dline = kline.rolling(d).mean()
    return kline, dline

def score_signals(high, low, close):
    """5指標の買いスコアを返す。各 +2(強い買い) / +1(買い) / 0(中立) / -1/-2(売り)。"""
    out = {}
    # Williams %R(14)
    wr = williams_r(high, low, close, 14)
    w = wr.iloc[-1]
    if w <= -80: out["Williams%R"] = (+2, f"{w:.1f}")
    elif -30 <= w <= -20: out["Williams%R"] = (+1, f"{w:.1f}")
    elif w >= -10: out["Williams%R"] = (-2, f"{w:.1f}")
    elif -20 < w < -10: out["Williams%R"] = (-1, f"{w:.1f}")
    else: out["Williams%R"] = (0, f"{w:.1f}")
    # RSI(14)
    r = rsi(close, 14).iloc[-1]
    if r < 30: out["RSI"] = (+2, f"{r:.1f}")
    elif r < 45: out["RSI"] = (+1, f"{r:.1f}")
    elif r > 70: out["RSI"] = (-2, f"{r:.1f}")
    elif r > 55: out["RSI"] = (-1, f"{r:.1f}")
    else: out["RSI"] = (0, f"{r:.1f}")
    # MACD
    line, sig, hist = macd(close)
    h_now, h_prev = hist.iloc[-1], hist.iloc[-2]
    if h_prev <= 0 < h_now: out["MACD"] = (+2, "GC")  # ゴールデンクロス
    elif h_now > 0 and h_now > h_prev: out["MACD"] = (+1, "上昇")
    elif h_prev >= 0 > h_now: out["MACD"] = (-2, "DC")
    elif h_now < 0 and h_now < h_prev: out["MACD"] = (-1, "下落")
    else: out["MACD"] = (0, "横ばい")
    # Stochastic(14,3)
    kl, dl = stochastic(high, low, close, 14, 3)
    k_now, k_prev = kl.iloc[-1], kl.iloc[-2]
    d_now, d_prev = dl.iloc[-1], dl.iloc[-2]
    if k_now < 20 and k_prev <= d_prev and k_now > d_now: out["Stoch"] = (+2, f"K={k_now:.0f}")
    elif k_now < 20: out["Stoch"] = (+1, f"K={k_now:.0f}")
    elif k_now > 80: out["Stoch"] = (-2, f"K={k_now:.0f}")
    elif k_now > 70: out["Stoch"] = (-1, f"K={k_now:.0f}")
    else: out["Stoch"] = (0, f"K={k_now:.0f}")
    # 移動平均（MA5/MA25/MA75）
    if len(close) >= 75:
        ma5 = close.rolling(5).mean().iloc[-1]
        ma25 = close.rolling(25).mean().iloc[-1]
        ma75 = close.rolling(75).mean().iloc[-1]
        p = close.iloc[-1]
        if p > ma5 > ma25 > ma75: out["MA"] = (+2, "PPP")  # パーフェクトオーダー
        elif p > ma25 and ma5 > ma25: out["MA"] = (+1, "上昇")
        elif p < ma5 < ma25 < ma75: out["MA"] = (-2, "逆PPP")
        elif p < ma25: out["MA"] = (-1, "下降")
        else: out["MA"] = (0, "もみあい")
    else:
        ma5 = close.rolling(5).mean().iloc[-1]
        ma25 = close.rolling(min(25, len(close))).mean().iloc[-1]
        p = close.iloc[-1]
        if p > ma5 > ma25: out["MA"] = (+1, "上昇")
        elif p < ma5 < ma25: out["MA"] = (-1, "下降")
        else: out["MA"] = (0, "中立")
    return out

def consensus(scores):
    """3アラート判定: buy / sell / skip / None"""
    total = sum(v for v, _ in scores.values())
    buys = sum(1 for v, _ in scores.values() if v > 0)
    sells = sum(1 for v, _ in scores.values() if v < 0)
    all_buy_aligned = all(v >= 1 for v, _ in scores.values())
    all_sell_aligned = all(v <= -1 for v, _ in scores.values())

    # 買いアラート
    if all_buy_aligned:
        return "🦒 麒麟（全神一致）", total, buys, sells, "buy"
    if total >= 7 and sells == 0:
        return "★★★ 強い買い", total, buys, sells, "buy"
    if total >= 4 and sells <= 1:
        return "★★  買い", total, buys, sells, "buy"
    if total >= 2 and sells <= 1:
        return "★   弱い買い", total, buys, sells, "buy"

    # 売りアラート（買われすぎ・トレンド崩壊）
    if all_sell_aligned:
        return "💀 全神売り", total, buys, sells, "sell"
    if total <= -7 and buys == 0:
        return "🔴 強い売り", total, buys, sells, "sell"
    if total <= -4 and buys <= 1:
        return "🔴 売り", total, buys, sells, "sell"
    if total <= -2 and buys <= 1:
        return "🔴 弱い売り", total, buys, sells, "sell"

    # 見送り賢明（シグナル混在・判定割れ）
    if buys >= 2 and sells >= 2:
        return "⚪ 判定割れ", total, buys, sells, "skip"
    if buys >= 1 and sells >= 1:
        return "⚪ 混在", total, buys, sells, "skip"

    return None, total, buys, sells, None

def main():
    print("=" * 70)
    print("Mega Scanner: 日米 蓄電池/半導体/テック Williams %R Buy Signal")
    print("=" * 70)

    print("\n[1/4] 母集団取得中 ...")
    parts = []
    # キュレーション系・指数系を先に → 全銘柄。drop_duplicatesで先勝ちで指数タグ温存
    for fn, name in [(get_sp500, "S&P500"),
                     (get_nasdaq100, "NASDAQ100"),
                     (get_us_venture, "US-Ventureキュレーション"),
                     (get_japan, "Japanキュレーション"),
                     (get_nasdaq_all, "NASDAQ+NYSE全銘柄"),
                     (get_jpx_all, "JPX全上場")]:
        df = fn()
        print(f"  {name}: {len(df)} 銘柄")
        if not df.empty: parts.append(df)
    universe = pd.concat(parts, ignore_index=True).drop_duplicates(subset=["ticker"])
    print(f"  Total (unique): {len(universe)}")

    print("\n[2/4] キーワードフィルタ適用 ...")
    mask = universe.apply(matches_keyword, axis=1)
    filtered = universe[mask].reset_index(drop=True)
    print(f"  対象銘柄: {len(filtered)}")

    # filtered一覧をJSONで保存（白虎が母集団として使う）
    import os as _os, json as _json
    _here = _os.path.dirname(_os.path.abspath(__file__))
    _filtered_path = _os.path.join(_here, "..", "docs", "filtered_universe.json")
    _os.makedirs(_os.path.dirname(_filtered_path), exist_ok=True)
    _records = []
    for _, _r in filtered.iterrows():
        _records.append({
            "ticker": str(_r["ticker"]),
            "name": str(_r.get("name", "")),
            "sector": str(_r.get("sector", "")),
            "market": "jp" if str(_r["ticker"]).endswith(".T") else "us",
        })
    with open(_filtered_path, "w", encoding="utf-8") as _f:
        _json.dump({"tickers": _records}, _f, ensure_ascii=False, indent=2)

    if filtered.empty:
        print("該当銘柄なし"); return

    print(f"\n[3/4] 株価ダウンロード & 5指標計算 ...")
    tickers = filtered["ticker"].tolist()
    BATCH = 50
    results = {}
    for i in range(0, len(tickers), BATCH):
        chunk = tickers[i:i+BATCH]
        try:
            data = yf.download(chunk, period="6mo", interval="1d",
                               progress=False, auto_adjust=False, threads=True)
            for t in chunk:
                try:
                    if len(chunk) == 1:
                        h, l, c = data["High"], data["Low"], data["Close"]
                    else:
                        h = data["High"][t]; l = data["Low"][t]; c = data["Close"][t]
                    h = h.dropna(); l = l.dropna(); c = c.dropna()
                    if len(c) < 30: continue
                    scores = score_signals(h, l, c)
                    results[t] = (float(c.iloc[-1]), scores)
                except Exception:
                    continue
        except Exception as e:
            print(f"  batch {i} error: {e}")
        print(f"  progress: {min(i+BATCH, len(tickers))}/{len(tickers)}")

    # 白虎データ事前読込（朱雀シグナル外の銘柄も拾うため）
    import os as _os2, json as _json2
    _byakko_path2 = _os2.path.abspath(_os2.path.join(_os2.path.dirname(__file__), "..", "docs", "byakko_data.json"))
    _byakko_pre = {}
    if _os2.path.exists(_byakko_path2):
        try:
            _byakko_pre = _json2.load(open(_byakko_path2, encoding="utf-8")).get("byakko", {})
        except Exception:
            _byakko_pre = {}

    print(f"\n[4/4] 総合シグナル合議判定（買い/売り/見送り＋白虎単独宝） ...")
    rows = []
    for _, r in filtered.iterrows():
        t = r["ticker"]
        if t not in results: continue
        price, scores = results[t]
        label, total, buys, sells, alert_type = consensus(scores)

        # 白虎単独宝: 朱雀がbuyでない（None/sell/skip）& 白虎B以上 → treasure昇格
        b_pre = _byakko_pre.get(t, {})
        b_grade = b_pre.get("grade")
        GRADE_RANK_PRE = {"S": 4, "A": 3, "B": 2, "C": 1}
        if alert_type != "buy" and GRADE_RANK_PRE.get(b_grade, 0) >= 2:
            label = f"💎 白虎単独宝({b_grade})"
            alert_type = "treasure"
            total = total or 0
        elif label is None:
            continue
        theme = assign_theme(r)
        market = "jp" if t.endswith(".T") else "us"
        rows.append({
            "総合": label,
            "Alert": alert_type,
            "Score": total,
            "市場": market,
            "テーマ": theme,
            "テーマ表示": THEME_LABELS.get(theme, theme),
            "セクター": (str(r.get("sector", "")) or "-")[:24],
            "ティッカー": t,
            "社名": str(r.get("name", ""))[:28],
            "現在値": round(price, 2),
            "W%R": scores["Williams%R"][1],
            "RSI": scores["RSI"][1],
            "MACD": scores["MACD"][1],
            "Stoch": scores["Stoch"][1],
            "MA": scores["MA"][1],
        })

    if not rows:
        print("\n買いシグナル銘柄なし。"); return

    out = pd.DataFrame(rows).sort_values(["Score"], ascending=False)
    print("\n" + "=" * 100)
    print(f"買いシグナル合議: {len(out)} 銘柄  "
          f"（★★★強い買い={sum(1 for x in rows if '★★★' in x['総合'])}  "
          f"★★買い={sum(1 for x in rows if x['総合']=='★★  買い')}  "
          f"★弱い買い={sum(1 for x in rows if x['総合']=='★   弱い買い')}）")
    print("=" * 100)
    pd.set_option("display.max_rows", None)
    pd.set_option("display.width", 220)
    pd.set_option("display.max_colwidth", 30)
    print(out.to_string(index=False))

    # JSON出力（GitHub Pages用）
    import json, os, datetime
    # 白虎データを読み込んで合議
    byakko_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "byakko_data.json"))
    byakko = {}
    if os.path.exists(byakko_path):
        try:
            byakko = json.load(open(byakko_path, encoding="utf-8")).get("byakko", {})
        except Exception:
            byakko = {}
    # 玄武データを読み込んで3神合議
    genbu_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "genbu_data.json"))
    genbu = {}
    if os.path.exists(genbu_path):
        try:
            genbu = json.load(open(genbu_path, encoding="utf-8")).get("genbu", {})
        except Exception:
            genbu = {}
    # 青龍データを読み込んで4神合議
    seiryu_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "seiryu_data.json"))
    seiryu = {}
    if os.path.exists(seiryu_path):
        try:
            seiryu = json.load(open(seiryu_path, encoding="utf-8")).get("seiryu", {})
        except Exception:
            seiryu = {}

    GRADE_RANK = {"S": 4, "A": 3, "B": 2, "C": 1, None: 0, "D": -2}
    for row in rows:
        t = row["ティッカー"]
        b = byakko.get(t, {})
        gn = genbu.get(t, {})
        sr = seiryu.get(t, {})
        row["白虎"] = b.get("grade") or "-"
        row["白虎詳細"] = b.get("note", "")
        row["玄武"] = gn.get("grade") or "-"
        row["玄武詳細"] = gn.get("note", "")
        row["青龍"] = sr.get("grade") or "-"
        row["青龍詳細"] = sr.get("note", "")
        byakko_grade = b.get("grade")
        genbu_grade = gn.get("grade")
        seiryu_grade = sr.get("grade")
        b_rank = GRADE_RANK.get(byakko_grade, 0)
        g_rank = GRADE_RANK.get(genbu_grade, 0)
        s_rank = GRADE_RANK.get(seiryu_grade, 0)
        suzaku_buy = row["Alert"] == "buy"
        suzaku_strong = row["Score"] >= 4
        # 🦒 真の麒麟（フル4神一致）
        if suzaku_buy and b_rank >= 2 and g_rank >= 2 and s_rank >= 2:
            row["総合"] = "🦒 真麒麟（4神全一致）"
        # 3神合議
        elif suzaku_buy and b_rank >= 2 and g_rank >= 2:
            row["総合"] = "🦒 麒麟（朱雀×白虎×玄武）"
        elif suzaku_buy and g_rank >= 2 and s_rank >= 2:
            row["総合"] = "🦒 麒麟（朱雀×玄武×青龍）"
        elif suzaku_strong and b_rank >= 2:
            row["総合"] = "🦒 麒麟（朱雀×白虎）"
        # 二神宝
        elif row["Alert"] == "treasure" and g_rank >= 3:
            row["総合"] = f"💎🐢 二神宝（白虎{byakko_grade}×玄武{genbu_grade}）"
        elif row["Alert"] == "treasure" and s_rank >= 3:
            row["総合"] = f"💎🐉 二神宝（白虎{byakko_grade}×青龍{seiryu_grade}）"
        # 警告系
        elif byakko_grade == "D" and suzaku_buy:
            row["総合"] = "⚠️ " + row["総合"] + "（白虎D・幹部売却）"
        elif genbu_grade == "D" and suzaku_buy:
            row["総合"] = "⚠️ " + row["総合"] + "（玄武D・減収）"
        elif seiryu_grade == "D" and suzaku_buy:
            row["総合"] = "⚠️ " + row["総合"] + "（青龍D・アナリスト弱気）"

    # 階層優先ソート（麒麟>★★★>★★>★ の順）+ 神獣grade副次ソート
    # 二神宝/単独宝（💎系）は treasure タブ内で白虎grade順に並ぶよう同じ階層に統合
    def tier_priority(row):
        t = row["総合"]
        if "⚠️" in t: return 90  # 警告は最後尾
        if "真麒麟" in t: return 1
        if "🦒" in t: return 2
        if "💎" in t: return 3  # 二神宝・単独宝とも同階層
        if "★★★" in t: return 5
        if "★★" in t: return 6
        if "★" in t: return 7
        if "💀" in t: return 10
        if "🔴 強い売り" in t: return 11
        if "🔴 売り" in t: return 12
        if "🔴" in t: return 13
        return 50
    GRADE_TO_NUM = {"S": 4, "A": 3, "B": 2, "C": 1, "D": -2, "-": 0, None: 0}
    for row in rows:
        row["_priority"] = tier_priority(row)
        row["_byakko_rank"] = GRADE_TO_NUM.get(row.get("白虎"), 0)
        row["_genbu_rank"] = GRADE_TO_NUM.get(row.get("玄武"), 0)
        row["_seiryu_rank"] = GRADE_TO_NUM.get(row.get("青龍"), 0)
    out = pd.DataFrame(rows).sort_values(
        ["_priority", "_byakko_rank", "_genbu_rank", "_seiryu_rank", "Score"],
        ascending=[True, False, False, False, False]
    ).drop(columns=["_priority", "_byakko_rank", "_genbu_rank", "_seiryu_rank"])

    payload = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "generated_jst": (datetime.datetime.now(datetime.timezone.utc)
                          + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M JST"),
        "universe_total": int(len(universe)),
        "filtered_total": int(len(filtered)),
        "signal_total": int(len(out)),
        "counts": {
            "kirin":  int(sum(1 for x in rows if "🦒" in x["総合"])),
            "strong": int(sum(1 for x in rows if "★★★" in x["総合"])),
            "buy":    int(sum(1 for x in rows if x["総合"] == "★★  買い")),
            "weak":   int(sum(1 for x in rows if x["総合"] == "★   弱い買い")),
        },
        "alerts": {
            "buy":      int(sum(1 for x in rows if x["Alert"] == "buy")),
            "sell":     int(sum(1 for x in rows if x["Alert"] == "sell")),
            "skip":     int(sum(1 for x in rows if x["Alert"] == "skip")),
            "treasure": int(sum(1 for x in rows if x["Alert"] == "treasure")),
        },
        "markets": {
            "us": int(sum(1 for x in rows if x["市場"] == "us")),
            "jp": int(sum(1 for x in rows if x["市場"] == "jp")),
        },
        "themes": {
            k: int(sum(1 for x in rows if x.get("テーマ") == k))
            for k in ["quantum", "space", "semi", "battery", "energy", "material", "other"]
        },
        "signals": out.to_dict(orient="records"),
    }
    out_path = os.path.join(os.path.dirname(__file__), "..", "docs", "signals.json")
    out_path = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n📜 神託書出: {out_path}")

if __name__ == "__main__":
    main()

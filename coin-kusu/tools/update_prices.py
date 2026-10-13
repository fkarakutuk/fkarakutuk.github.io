#!/usr/bin/env python3
"""Fetch real OHLC history for every Coin Kuşu coin and write coin-kusu/prices.js.

Sources (public, no API key):
  * Binance market-data API (data-api.binance.vision) – main source
  * Kraken – older history before the coin's Binance listing, and coins Binance lacks
  * Bybit / OKX / Gate – fallback for coins missing on both

Weekly candles are used when a coin has enough history; newer coins get 3-day or
daily candles so every map is long enough to play. Run daily by GitHub Actions.
"""
import json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "prices.js")
MIN_CANDLES = 130
UA = {"User-Agent": "coin-kusu-price-updater/1.0"}

# Binance pairs, oldest first; history of renamed tokens is joined.
BINANCE = {"POL": ["MATICUSDT", "POLUSDT"], "RENDER": ["RNDRUSDT", "RENDERUSDT"], "USDT": [],
           "USDC": ["USDCUSDT"], "LIT": []}   # Binance LITUSDT was Litentry, not Lighter
KRAKEN = {"BTC": "XBT", "DOGE": "XDG", "LIT": None}
EXTRA = {"LIT": [("bybit", "LITUSDT"), ("okx", "LIT-USDT"), ("gate", "LIT_USDT")]}


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(1.5 * (i + 1))
    print("  ! ", url, err, file=sys.stderr)
    return None


def clean(rows):
    rows = sorted(r for r in rows if r[1] > 0 and r[2] > 0 and r[3] > 0 and r[4] > 0)
    out = []
    for r in rows:
        if out and r[0] <= out[-1][0]:
            continue
        out.append(r)
    return out


# each row: [t_ms, open, high, low, close]
def binance(sym, iv):
    rows = []
    for pair in BINANCE.get(sym, [sym + "USDT"]):
        j = get(f"https://data-api.binance.vision/api/v3/klines?symbol={pair}&interval={iv}&limit=1000")
        if isinstance(j, list):
            rows += [[k[0], float(k[1]), float(k[2]), float(k[3]), float(k[4])] for k in j]
    return clean(rows)


def kraken(sym, iv):
    name = KRAKEN.get(sym, sym)
    if not name:
        return []
    j = get(f"https://api.kraken.com/0/public/OHLC?pair={name}USD&interval={iv}")
    if not j or j.get("error"):
        return []
    key = next((k for k in j["result"] if k != "last"), None)
    return clean([[k[0] * 1000, float(k[1]), float(k[2]), float(k[3]), float(k[4])] for k in j["result"][key]]) if key else []


def extra(sym, iv):
    for src, pair in EXTRA.get(sym, []):
        if src == "bybit":
            j = get(f"https://api.bybit.com/v5/market/kline?category=spot&symbol={pair}&interval={ {'1w':'W','3d':'D','1d':'D'}[iv] }&limit=1000")
            if j and j.get("retCode") == 0 and j["result"]["list"]:
                return clean([[int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4])] for k in j["result"]["list"]])
        if src == "okx":
            j = get(f"https://www.okx.com/api/v5/market/history-candles?instId={pair}&bar={ {'1w':'1W','3d':'3D','1d':'1D'}[iv] }&limit=300")
            if j and j.get("code") == "0" and j["data"]:
                return clean([[int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4])] for k in j["data"]])
        if src == "gate":
            j = get(f"https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair={pair}&interval={ {'1w':'7d','3d':'1d','1d':'1d'}[iv] }&limit=1000")
            if isinstance(j, list) and j:
                return clean([[int(k[0]) * 1000, float(k[5]), float(k[3]), float(k[4]), float(k[2])] for k in j])
    return []


def merge(older, main):
    """Prepend older-source candles only if prices line up (guards against ticker collisions)."""
    if not main:
        return older
    if not older:
        return main
    start = main[0][0]
    before = [r for r in older if r[0] < start]
    if not before:
        return main
    ratio = before[-1][4] / main[0][1]
    return before + main if 0.6 < ratio < 1.6 else main


def series(sym, iv):
    kv = {"1w": 10080, "3d": None, "1d": 1440}[iv]
    main = binance(sym, iv)
    if not main:
        main = extra(sym, iv)
    old = kraken(sym, kv) if kv else []
    if not main:
        return old
    return merge(old, main)


def main():
    page = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    raw = page[page.index("const RAW = {"):]
    raw = raw[:raw.index("\n};")]
    syms = re.findall(r'^"?([A-Z0-9]+)"?:\[', raw, re.M)
    print(len(syms), "coins")
    data = {}
    for s in syms:
        step, rows = 7, series(s, "1w")
        if len(rows) < MIN_CANDLES:
            step, rows = 3, series(s, "3d") if BINANCE.get(s, [1]) else []
            if len(rows) < MIN_CANDLES:
                step, rows = 1, series(s, "1d")
        if not rows:
            print(f"{s}: no data")
            continue
        p = lambda v: float(f"{v:.5g}")
        data[s] = {"s": step, "t": [round(r[0] / 864e5) for r in rows],
                   "d": [[p(r[1]), p(r[2]), p(r[3]), p(r[4])] for r in rows]}
        print(f"{s}: {len(rows)} x {step}d  {time.strftime('%Y-%m-%d', time.gmtime(rows[0][0]/1000))} -> "
              f"{time.strftime('%Y-%m-%d', time.gmtime(rows[-1][0]/1000))}  last {rows[-1][4]}")
        time.sleep(0.4)
    stamp = time.strftime("%Y-%m-%d", time.gmtime())
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(f"/* Coin Kuşu price history. Updated {stamp} by tools/update_prices.py. Rows: [open, high, low, close]; t = days since 1970-01-01 (UTC). */\n")
        f.write(f"window.COIN_PRICES_UPDATED={json.dumps(stamp)};\nwindow.COIN_PRICES=")
        json.dump(data, f, separators=(",", ":"))
        f.write(";\n")
    print("wrote", OUT, len(data), "coins")
    if len(data) < len(syms) * 0.9:
        sys.exit("too many coins missing, not committing")


if __name__ == "__main__":
    main()

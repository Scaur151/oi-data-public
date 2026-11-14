#!/usr/bin/env python3
"""Variational Omni: снимок открытого интереса и спреда только по SWAP-контрактам.
Один запуск = один снимок. Пишет в oi_ГГГГ-Wнн.csv (неделя ISO, UTC) в корень репо.
Колонки: ts_utc, ticker, oi, spread_pct, source
oi = (long_oi + short_oi) * 2  — реальный open interest
spread_pct = (base_spread_bps / 2) / 100  — half-spread в процентах (как на сайте)
source = scaurxyz
"""
import csv, json, os, sys, time, urllib.request, datetime as dt
URL = "https://omni-client-api.prod.ap-northeast-1.variational.io/metadata/v2/stats"
OUT = os.path.dirname(os.path.abspath(__file__))
COLS = ["ts_utc", "ticker", "oi", "spread_pct", "source"]
SOURCE = "scaurxyz"
def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0
def fetch():
    last = None
    for i in range(5):
        try:
            req = urllib.request.Request(URL, headers={"User-Agent": "oi-logger/1.4"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.load(r)
            if d.get("listings"):
                return d
            last = "empty listings"
        except Exception as e:
            last = e
        time.sleep(5 * (i + 1))
    raise RuntimeError("fetch failed: %s" % last)
def main():
    now = dt.datetime.now(dt.timezone.utc)
    ts = now.strftime("%Y-%m-%dT%H:%M:00Z")
    iso = now.isocalendar()
    filename = "oi_%d-W%02d.csv" % (iso[0], iso[1])
    path = os.path.join(OUT, filename)
    if os.path.exists(path):
        with open(path) as fh:
            if any(line.startswith(ts + ",") for line in fh):
                print("уже есть снимок за", ts)
                return
    data = fetch()
    rows = []
    for l in data["listings"]:
        if l.get("contract_type") != "swap":
            continue
        oi_raw = l.get("open_interest") or {}
        lo, so = num(oi_raw.get("long_open_interest")), num(oi_raw.get("short_open_interest"))
        oi = (lo + so) * 2
        spread_bps = num(l.get("base_spread_bps"))
        spread_pct = (spread_bps / 2) / 100
        rows.append([ts, l.get("ticker"), round(oi, 0), round(spread_pct, 6), SOURCE])
    new = not os.path.exists(path)
    with open(path, "a", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(COLS)
        w.writerows(rows)
    print(ts, len(rows), "свопов ->", filename)
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ОШИБКА:", e, file=sys.stderr)
        sys.exit(1)

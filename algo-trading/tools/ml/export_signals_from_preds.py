from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
import glob, datetime as dt

DATA = Path("/Users/sultan/Trading/data")
PREDS_DIR = DATA/"ml"/"preds"
OUT_DIR = DATA/"ml"/"signals"
OUT_DIR.mkdir(parents=True, exist_ok=True)

UMBRAL = 0.5

def main():
    files = sorted(glob.glob(str(PREDS_DIR/"*_preds.csv")))
    rows = []
    for fp in files:
        df = pd.read_csv(fp, parse_dates=["date"])
        if df.empty:
            continue
        last = df.sort_values("date").iloc[-1].copy()
        sym = str(last.get("symbol"))
        prob = float(last["prob_up"])
        side = "LONG" if prob >= UMBRAL else "FLAT"
        rows.append({
            "date": last["date"].isoformat(),
            "symbol": sym,
            "prob_up": prob,
            "side": side,
            "confidence": abs(prob-0.5)*2.0
        })
    if not rows:
        print("No preds")
        return
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    out = OUT_DIR/f"signals_{today}.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(str(out))

if __name__ == "__main__":
    main()

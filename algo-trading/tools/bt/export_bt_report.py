from __future__ import annotations
from pathlib import Path
import pandas as pd

RPT = Path("/Users/sultan/Trading/data/checks/reports")
OUT = RPT/"bt_leaderboard.csv"

def main():
    rows = []
    for p in sorted(RPT.glob("bt_symbol_*_metrics.csv")):
        sym = p.stem.replace("bt_symbol_","").replace("_metrics","")
        df = pd.read_csv(p)
        df["symbol_tag"] = sym
        rows.append(df)
    if not rows:
        print("No metrics files found")
        return
    allm = pd.concat(rows, ignore_index=True)
    allm.to_csv(OUT, index=False)
    print(str(OUT))

if __name__ == "__main__":
    main()

from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

DATA = Path("/Users/sultan/Trading/data")
DS_DIR = DATA/"ml"/"datasets"

def fix_one(fp: Path) -> int:
    df = pd.read_parquet(fp).sort_values("date").reset_index(drop=True)
    if "close" not in df.columns:
        return 0
    df["close_next"] = df["close"].shift(-1)
    df["ret_fwd_1d"] = df["close_next"]/df["close"] - 1.0
    df.drop(columns=["close_next"], inplace=True)
    df["y_up"] = (df["ret_fwd_1d"] > 0).astype("Int64")
    df.to_parquet(fp, index=False)
    return len(df)

def main():
    total = 0
    for fp in DS_DIR.glob("symbol=*/interval=1d/data.parquet"):
        n = fix_one(fp)
        print(f"[OK] rewrite {fp} rows={n}")
        total += n
    print(f"TOTAL rows: {total}")

if __name__ == "__main__":
    main()

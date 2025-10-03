from __future__ import annotations
from pathlib import Path
import pandas as pd, numpy as np

ROOT = Path("/Users/sultan/Trading/data")/"checks"/"reports"
a = pd.read_csv(ROOT/"portfolio_equity.csv", parse_dates=["date"])
b = pd.read_csv(ROOT/"portfolio_equity_voltarget.csv", parse_dates=["date"])
df = a.merge(b, on="date", suffixes=("_base","_vt"))
df["diff_equity"] = df["equity_vt"] - df["equity_base"]
out = ROOT/"portfolio_compare.csv"
df[["date","equity_base","equity_vt","diff_equity"]].to_csv(out, index=False)
print(str(out))

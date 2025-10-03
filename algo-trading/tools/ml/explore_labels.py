from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

DATA = Path("/Users/sultan/Trading/data/ml/datasets/all_1d.parquet")
OUT  = Path("/Users/sultan/Trading/data/checks/reports")
OUT.mkdir(parents=True, exist_ok=True)

def main():
    if not DATA.exists():
        raise SystemExit(f"No existe {DATA}")
    df = pd.read_parquet(DATA)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df["year"] = df["date"].dt.year
    if "y_up" not in df.columns:
        raise SystemExit("Falta columna y_up")

    def agg(g):
        n = len(g)
        n_pos = int(g["y_up"].sum())
        n_neg = int(n - n_pos)
        rate = (n_pos / n) if n else np.nan
        return pd.Series({
            "n": n,
            "n_pos": n_pos,
            "n_neg": n_neg,
            "pos_rate": round(rate, 4),
            "start": g["date"].min(),
            "end": g["date"].max(),
        })

    by_symbol = df.groupby("symbol", as_index=False).apply(agg)
    by_symbol = by_symbol.sort_values("symbol").reset_index(drop=True)
    p1 = OUT / "ml_label_dist.csv"
    by_symbol.to_csv(p1, index=False)

    by_year = df.groupby(["symbol","year"], as_index=False).apply(agg)
    by_year = by_year.sort_values(["symbol","year"]).reset_index(drop=True)
    p2 = OUT / "ml_label_dist_by_year.csv"
    by_year.to_csv(p2, index=False)

    warn = by_symbol[(by_symbol["pos_rate"]<=0.45) | (by_symbol["pos_rate"]>=0.55)]
    p3 = OUT / "ml_label_dist_warnings.csv"
    warn.to_csv(p3, index=False)

    print("Distribución global por símbolo →", p1)
    print("Distribución por símbolo/año →", p2)
    print("Posibles desbalances (pos_rate<=0.45 o >=0.55) →", p3 if len(warn) else "sin alertas")

if __name__ == "__main__":
    main()

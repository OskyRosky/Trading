from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

DATA = Path("/Users/sultan/Trading/data/ml/datasets/all_1d.parquet")
OUT_DIR = Path("/Users/sultan/Trading/data/checks/reports")
OUT_DIR.mkdir(parents=True, exist_ok=True)

KEY_FEATS = [
    "ret_pct","sma_7","sma_20","ema_12","ema_26","rsi_14","atr_14","adx_14",
    "bb_ma_20_2","bb_u_20_2","bb_l_20_2","volume","trades",
    "sma_spread_7_20","ema_spread_12_26"
]

def main():
    if not DATA.exists():
        raise SystemExit(f"No existe {DATA}")
    df = pd.read_parquet(DATA)
    df["date"] = pd.to_datetime(df["date"], utc=True)

    cols = df.columns.tolist()
    print("Columnas:", cols)

    req = {"date","symbol","close","ret_fwd_1d","y_up"}
    faltan = req - set(cols)
    if faltan:
        print("Faltan columnas obligatorias:", faltan)
        raise SystemExit(1)

    dup = df.duplicated(subset=["symbol","date"]).sum()
    print("Duplicados (symbol,date):", dup)

    y_vals = df["y_up"].dropna().unique()
    print("Valores únicos y_up:", y_vals)
    if not set(y_vals).issubset({0,1}):
        print("Alerta: y_up tiene valores fuera de {0,1}")

    res = []
    for c in ["ret_fwd_1d","ret_pct","rsi_14","atr_14","adx_14","volume","trades","sma_7","sma_20","ema_12","ema_26"]:
        if c in df.columns:
            s = df[c]
            res.append({
                "feature": c,
                "count": int(s.count()),
                "na": int(s.isna().sum()),
                "min": float(np.nanmin(s.values)) if s.notna().any() else np.nan,
                "max": float(np.nanmax(s.values)) if s.notna().any() else np.nan,
                "mean": float(s.mean()) if s.notna().any() else np.nan,
                "std": float(s.std()) if s.notna().any() else np.nan,
            })
    stats = pd.DataFrame(res).sort_values("feature")
    stats_path = OUT_DIR/"ml_explore_stats.csv"
    stats.to_csv(stats_path, index=False)
    print("Resumen estadístico →", stats_path)

    checks = []
    if "rsi_14" in df.columns:
        bad_rsi = (~df["rsi_14"].between(0,100)).sum()
        checks.append(("RSI_range_violation", int(bad_rsi)))
        print("RSI fuera [0,100]:", int(bad_rsi))
    if "atr_14" in df.columns:
        bad_atr = (df["atr_14"] <= 0).sum()
        checks.append(("ATR_non_positive", int(bad_atr)))
        print("ATR <= 0:", int(bad_atr))
    if "bb_u_20_2" in df.columns and "bb_l_20_2" in df.columns:
        bad_bb = (df["bb_u_20_2"] < df["bb_l_20_2"]).sum()
        checks.append(("BB_upper_below_lower", int(bad_bb)))
        print("BB upper < lower:", int(bad_bb))

    for sym, part in df.groupby("symbol", sort=False):
        srt = part.sort_values("date")
        mono = srt["date"].is_monotonic_increasing
        if not mono:
            checks.append((f"NonMonotonic_{sym}", 1))

    checks_df = pd.DataFrame(checks, columns=["check","count"]) if checks else pd.DataFrame(columns=["check","count"])
    checks_path = OUT_DIR/"ml_explore_checks.csv"
    checks_df.to_csv(checks_path, index=False)
    print("Checks →", checks_path)

    sample = df.sort_values(["symbol","date"]).groupby("symbol").tail(3)
    sample_path = OUT_DIR/"ml_explore_sample.csv"
    sample.to_csv(sample_path, index=False)
    print("Muestra tail por símbolo →", sample_path)

    print("Exploración completada.")

if __name__ == "__main__":
    main()

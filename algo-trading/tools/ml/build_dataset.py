from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np
from tools.ml.utils import load_cfg, read_trusted_symbol, ensure_monotonic

OUT_ROOT = Path("/Users/sultan/Trading/data/ml/datasets")
OUT_ROOT.mkdir(parents=True, exist_ok=True)

BASE_FEATURES = [
    "ret_pct","sma_7","sma_20","ema_12","ema_26","rsi_14","atr_14","adx_14",
    "bb_ma_20_2","bb_u_20_2","bb_l_20_2","volume","trades"
]

def make_supervised(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    df = ensure_monotonic(df.copy())
    df["ret_fwd_1d"] = df["close"].shift(-1) / df["close"] - 1.0
    df["y_up"] = (df["ret_fwd_1d"] > 0).astype("int8")
    if {"sma_7","sma_20"}.issubset(df.columns):
        df["sma_spread_7_20"] = df["sma_7"] - df["sma_20"]
    if {"ema_12","ema_26"}.issubset(df.columns):
        df["ema_spread_12_26"] = df["ema_12"] - df["ema_26"]
    feats = [c for c in BASE_FEATURES if c in df.columns] + \
            [c for c in ["sma_spread_7_20","ema_spread_12_26"] if c in df.columns]
    df = df.dropna(subset=feats + ["ret_fwd_1d","y_up"])
    df = df.iloc[:-1].copy()  # evita ver t+1
    df["symbol"] = symbol
    cols = ["date","symbol","close","ret_fwd_1d","y_up"] + feats
    return df[cols]

def main():
    paths, symbols, _ = load_cfg()
    all_rows = []
    for sym in symbols["symbol_map"].keys():
        src = read_trusted_symbol(paths, sym)
        if src.empty:
            print(f"[WARN] {sym}: sin datos trusted")
            continue
        sup = make_supervised(src, sym)
        if sup.empty:
            print(f"[WARN] {sym}: dataset vacío tras limpieza")
            continue
        dst_dir = OUT_ROOT / f"symbol={sym}" / "interval=1d"
        dst_dir.mkdir(parents=True, exist_ok=True)
        out_path = dst_dir / "data.parquet"
        sup.to_parquet(out_path, index=False)
        print(f"[OK] {sym} filas={len(sup)} → {out_path}")
        all_rows.append(sup)

    if all_rows:
        big = pd.concat(all_rows, ignore_index=True)
        out_all = OUT_ROOT / "all_1d.parquet"
        big.to_parquet(out_all, index=False)
        print(f"[OK] combinado filas={len(big)} → {out_all}")

if __name__ == "__main__":
    main()

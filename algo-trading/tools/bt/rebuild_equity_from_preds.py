from __future__ import annotations
from pathlib import Path
import pandas as pd, numpy as np, duckdb

DATA   = Path("/Users/sultan/Trading/data")
RPT    = DATA/"checks"/"reports"
TRUST  = DATA/"trusted"/"market=futures"/"segment=usdtm"/"contract=perpetual"

def build_one(symbol: str, fee_bps: float = 2.0) -> Path | None:
    preds_path = DATA/"ml"/"preds"/f"{symbol}_preds.csv"
    if not preds_path.exists():
        print(f"[SKIP] {symbol}: no existe {preds_path}")
        return None

    preds = pd.read_csv(preds_path)
    if "date" not in preds or "pred_up" not in preds.columns:
        print(f"[SKIP] {symbol}: preds sin columnas esperadas")
        return None
    preds["date"] = pd.to_datetime(preds["date"], utc=True)

    # Leer precios directamente de Parquet (evita problemas con nombres de vista)
    pat = str(TRUST / f"symbol={symbol}" / "interval=1d" / "**" / "data.parquet")
    con = duckdb.connect()  # en memoria, sin bloquear archivos .duckdb
    try:
        px = con.execute(
            "SELECT date, close FROM read_parquet(?, hive_partitioning=1) ORDER BY date",
            [pat],
        ).fetchdf()
    finally:
        con.close()

    if px.empty:
        print(f"[SKIP] {symbol}: sin precios en {pat}")
        return None

    px["date"] = pd.to_datetime(px["date"], utc=True)
    px = px.sort_values("date")

    df = preds.merge(px, on="date", how="inner").sort_values("date").reset_index(drop=True)
    if df.empty:
        print(f"[SKIP] {symbol}: sin intersección entre preds y precios")
        return None

    df["ret"] = df["close"].pct_change().fillna(0.0)
    df["pos"] = df["pred_up"].astype(int)
    df["pos_prev"] = df["pos"].shift(1).fillna(0).astype(int)

    fee = fee_bps / 10000.0
    df["turnover"] = (df["pos"] != df["pos_prev"]).astype(int)
    df["strat_ret"] = df["pos_prev"] * df["ret"] - df["turnover"] * fee
    df["equity"] = (1.0 + df["strat_ret"]).cumprod()

    out = df[["date","equity","strat_ret"]].copy()
    out_path = RPT/f"bt_symbol_{symbol}.csv"
    out.to_csv(out_path, index=False)
    print(f"[OK] {symbol} → {out_path} rows={len(out)}")
    return out_path

def main():
    preds_dir = (DATA/"ml"/"preds")
    syms = [p.name.replace("_preds.csv","") for p in preds_dir.glob("*_preds.csv")]
    ok = 0
    for s in sorted(syms):
        if build_one(s) is not None:
            ok += 1
    print(f"Hechos: {ok} / {len(syms)}")

if __name__ == "__main__":
    main()

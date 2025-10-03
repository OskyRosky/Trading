from __future__ import annotations
from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd
import yaml

BASE = Path("/Users/sultan/Trading/algo-trading")
DATA = Path("/Users/sultan/Trading/data")

def load_split_date() -> pd.Timestamp:
    cfg = yaml.safe_load((BASE/"configs"/"ml.yml").read_text())
    return pd.Timestamp(cfg["split_date"], tz="UTC")

def load_preds(sym: str) -> pd.DataFrame:
    p = DATA/"ml"/"preds"/f"{sym}_preds.csv"
    df = pd.read_csv(p, parse_dates=["date"])
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df.sort_values("date").reset_index(drop=True)

def load_supervised(sym: str) -> pd.DataFrame:
    p = DATA/"ml"/"datasets"/f"symbol={sym}"/"interval=1d"/"data.parquet"
    df = pd.read_parquet(p)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df[["date","ret_fwd_1d"]].sort_values("date").reset_index(drop=True)

def metrics(equity: pd.Series, strat_ret: pd.Series) -> dict:
    equity = equity.dropna()
    strat_ret = strat_ret.loc[equity.index].fillna(0)
    n = len(equity)
    if n < 2:
        return {"CAGR": np.nan, "Sharpe": np.nan, "MaxDD": np.nan}
    days = (equity.index[-1] - equity.index[0]).days or 1
    years = days/365.25
    cagr = float(equity.iloc[-1]**(1/years) - 1) if years>0 else np.nan
    mu = strat_ret.mean()
    sd = strat_ret.std(ddof=0)
    sharpe = float((mu / sd) * np.sqrt(252)) if sd>0 else 0.0
    run_max = equity.cummax()
    dd = (equity/run_max - 1.0).min()
    return {"CAGR": round(cagr,4), "Sharpe": round(sharpe,4), "MaxDD": round(float(dd),4)}

def backtest_symbol(sym: str, threshold: float, fee_bps: float, split_date: pd.Timestamp) -> dict:
    preds = load_preds(sym)
    sup = load_supervised(sym)
    df = preds.merge(sup, on="date", how="inner")
    df = df[df["date"] >= split_date].copy()
    if df.empty:
        raise RuntimeError(f"{sym}: sin filas post split")
    df["side"] = (df["prob_up"] >= threshold).astype(int)
    df["ret"] = df["ret_fwd_1d"].astype(float)
    fee = fee_bps/10000.0
    pos_change = df["side"].diff().abs().fillna(df["side"]).astype(float)
    df["strat_ret_gross"] = df["side"] * df["ret"]
    df["cost"] = fee * pos_change
    df["strat_ret"] = df["strat_ret_gross"] - df["cost"]
    eq = (1.0 + df["strat_ret"]).cumprod()
    df["equity"] = eq
    m = metrics(df.set_index("date")["equity"], df.set_index("date")["strat_ret"])
    out_equity = DATA/"checks"/"reports"/f"equity_ml_{sym}.csv"
    df[["date","equity","strat_ret","side","prob_up","ret_fwd_1d"]].to_csv(out_equity, index=False)
    m.update({"symbol": sym, "threshold": threshold, "fee_bps": fee_bps, "n_days": int(len(df))})
    return m

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--fee_bps", type=float, default=2.0)
    args = ap.parse_args()
    split = load_split_date()
    symbols = yaml.safe_load((BASE/"configs"/"symbols.yml").read_text())["symbol_map"].keys()
    allm = []
    for s in symbols:
        try:
            m = backtest_symbol(s, args.threshold, args.fee_bps, split)
            allm.append(m)
            print(json.dumps({"symbol": s, "metrics": m}, indent=2))
        except Exception as e:
            print(json.dumps({"symbol": s, "error": str(e)}))
    if allm:
        out = DATA/"checks"/"reports"/"ml_bt_metrics_all.csv"
        pd.DataFrame(allm).to_csv(out, index=False)
        print(str(out))

if __name__ == "__main__":
    main()

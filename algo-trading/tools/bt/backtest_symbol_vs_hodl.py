from __future__ import annotations
from pathlib import Path
import argparse
import pandas as pd
import numpy as np

DATA = Path("/Users/sultan/Trading/data")
DS_DIR = DATA/"ml"/"datasets"
PREDS_DIR = DATA/"ml"/"preds"
THR_FILE = DATA/"ml"/"thresholds"/"opt_thresholds.csv"
OUT_DIR = DATA/"checks"/"reports"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_dataset(sym:str) -> pd.DataFrame:
    p = DS_DIR/f"symbol={sym}"/"interval=1d"/"data.parquet"
    df = pd.read_parquet(p).sort_values("date").reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df[["date","close","ret_fwd_1d"]]

def load_preds(sym:str) -> pd.DataFrame:
    p_cal = PREDS_DIR/f"{sym}_preds_cal.csv"
    p_std = PREDS_DIR/f"{sym}_preds.csv"
    if p_cal.exists():
        df = pd.read_csv(p_cal, parse_dates=["date"]).sort_values("date")
        df["prob"] = df["prob_up_cal"]
    elif p_std.exists():
        df = pd.read_csv(p_std, parse_dates=["date"]).sort_values("date")
        df["prob"] = df["prob_up"]
    else:
        raise FileNotFoundError(f"Preds not found for {sym}")
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df[["date","prob"]]

def load_thr_map() -> dict[str,float]:
    if not THR_FILE.exists():
        return {}
    df = pd.read_csv(THR_FILE)
    if "symbol" in df.columns and "thr_opt" in df.columns:
        return {r.symbol: float(r.thr_opt) for _,r in df.iterrows()}
    return {}

def metrics(ret: pd.Series) -> dict:
    r = ret.fillna(0.0)
    if len(r) < 5:
        return {"CAGR": np.nan, "Sharpe": np.nan, "MaxDD": np.nan, "Vol": np.nan}
    eq = (1 + r).cumprod()
    years = len(r) / 252
    cagr = float(eq.iloc[-1] ** (1/years) - 1) if years > 0 else np.nan
    vol = float(r.std(ddof=0) * np.sqrt(252))
    mu = float(r.mean() * 252)
    sharpe = mu/vol if vol > 0 else np.nan
    maxdd = float((eq/eq.cummax() - 1).min())
    return {"CAGR": round(cagr, 4), "Sharpe": round(sharpe, 4), "MaxDD": round(maxdd, 4), "Vol": round(vol, 4)}

def backtest_symbol(sym:str, fee_bps:float=2.0, thr_override:float|None=None, start:str|None=None, end:str|None=None):
    base = load_dataset(sym)
    preds = load_preds(sym)
    df = base.merge(preds, on="date", how="inner").dropna().copy()
    if start: df = df[df["date"] >= pd.Timestamp(start, tz="UTC")]
    if end:   df = df[df["date"] <= pd.Timestamp(end, tz="UTC")]
    thr_map = load_thr_map()
    thr = float(thr_override) if thr_override is not None else float(thr_map.get(sym, 0.5))
    df["pos_today"] = (df["prob"] >= thr).astype(float)
    df["pos"] = df["pos_today"].shift(1).fillna(0.0)
    fee = fee_bps/10000.0
    df["turnover"] = (df["pos"].diff().abs()).fillna(df["pos"].abs())
    df["ret_strat"] = df["pos"] * df["ret_fwd_1d"] - fee * df["turnover"]
    df["eq_strat"] = (1 + df["ret_strat"]).cumprod()
    df["ret_hodl_sym"] = df["ret_fwd_1d"]
    df["eq_hodl_sym"]  = (1 + df["ret_hodl_sym"]).cumprod()
    return df.reset_index(drop=True)

def align_benchmark(df_dates: pd.DataFrame, bench_sym:str) -> pd.DataFrame:
    b = load_dataset(bench_sym)
    b = b[b["date"].isin(df_dates["date"])].copy()
    b = b.sort_values("date").reset_index(drop=True)
    b["ret_hodl"] = b["ret_fwd_1d"]
    b["eq_hodl"] = (1 + b["ret_hodl"]).cumprod()
    return b[["date","ret_hodl","eq_hodl"]].rename(columns={"ret_hodl":f"ret_hodl_{bench_sym}","eq_hodl":f"eq_hodl_{bench_sym}"})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--fee_bps", type=float, default=2.0)
    ap.add_argument("--thr", type=float, default=None)
    ap.add_argument("--start", type=str, default=None)
    ap.add_argument("--end", type=str, default=None)
    args = ap.parse_args()

    sym = args.symbol
    df = backtest_symbol(sym, fee_bps=args.fee_bps, thr_override=args.thr, start=args.start, end=args.end)

    b_btc = align_benchmark(df[["date"]], "BTCUSDT")
    b_eth = align_benchmark(df[["date"]], "ETHUSDT")
    out = df.merge(b_btc, on="date", how="left").merge(b_eth, on="date", how="left")

    m_sym = metrics(out["ret_strat"])
    m_hodl_sym = metrics(out["ret_hodl_sym"])
    m_btc = metrics(out["ret_hodl_BTCUSDT"]) if "ret_hodl_BTCUSDT" in out else {"CAGR":np.nan,"Sharpe":np.nan,"MaxDD":np.nan,"Vol":np.nan}
    m_eth = metrics(out["ret_hodl_ETHUSDT"]) if "ret_hodl_ETHUSDT" in out else {"CAGR":np.nan,"Sharpe":np.nan,"MaxDD":np.nan,"Vol":np.nan}

    eq_path = OUT_DIR/f"bt_symbol_{sym}.csv"
    out.to_csv(eq_path, index=False)

    met_path = OUT_DIR/f"bt_symbol_{sym}_metrics.csv"
    pd.DataFrame([
        {"asset": f"STRAT_{sym}", **m_sym},
        {"asset": f"HODL_{sym}", **m_hodl_sym},
        {"asset": "HODL_BTCUSDT", **m_btc},
        {"asset": "HODL_ETHUSDT", **m_eth},
    ]).to_csv(met_path, index=False)

    print(str(eq_path))
    print(str(met_path))

if __name__ == "__main__":
    main()

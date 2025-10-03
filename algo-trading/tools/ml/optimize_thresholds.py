from __future__ import annotations
from pathlib import Path
import pandas as pd, numpy as np, datetime as dt

DATA = Path("/Users/sultan/Trading/data")
PREDS_DIR = DATA/"ml"/"preds"
DS_DIR = DATA/"ml"/"datasets"
OUT_DIR = DATA/"ml"/"thresholds"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def strat_returns(prob_up: pd.Series, ret_fwd_1d: pd.Series, thr: float, fee_bps: float=2.0) -> pd.Series:
    fee = fee_bps/10000.0
    pos = (prob_up >= thr).astype(int)
    r = pos * ret_fwd_1d
    turn = pos.diff().abs().fillna(0)
    r = r - turn * fee
    return r

def best_thr_for(sym:str, fee_bps:float=2.0):
    p_cal = PREDS_DIR/f"{sym}_preds_cal.csv"
    p_std = PREDS_DIR/f"{sym}_preds.csv"
    p_ds  = DS_DIR/f"symbol={sym}"/"interval=1d"/"data.parquet"
    if not p_ds.exists(): 
        return None
    ds = pd.read_parquet(p_ds)[["date","ret_fwd_1d"]]
    if p_cal.exists():
        preds = pd.read_csv(p_cal, parse_dates=["date"])
        col = "prob_up_cal"
    elif p_std.exists():
        preds = pd.read_csv(p_std, parse_dates=["date"])
        col = "prob_up"
    else:
        return None
    df = preds.merge(ds, on="date", how="inner").dropna(subset=[col,"ret_fwd_1d"]).sort_values("date")
    if df.empty: 
        return None
    best = {"symbol": sym, "source": col, "thr_opt": 0.5, "sharpe_opt": -1e9, "n": len(df)}
    grid = np.round(np.arange(0.40, 0.601, 0.01), 2)
    for thr in grid:
        ret = strat_returns(df[col], df["ret_fwd_1d"], thr=thr, fee_bps=fee_bps)
        sd = ret.std()
        if sd == 0 or not np.isfinite(sd):
            sr = -np.inf
        else:
            sr = (ret.mean()/sd)*np.sqrt(252)
        if np.isfinite(sr) and sr > best["sharpe_opt"]:
            best["thr_opt"] = float(thr)
            best["sharpe_opt"] = float(sr)
    return best

def main():
    syms = sorted({p.stem.replace("_preds_cal","") for p in PREDS_DIR.glob("*_preds_cal.csv")} |
                  {p.stem.replace("_preds","") for p in PREDS_DIR.glob("*_preds.csv")})
    rows = []
    for s in syms:
        res = best_thr_for(s, fee_bps=2.0)
        if res: rows.append(res)
    if not rows:
        print("No hay resultados.")
        return
    df = pd.DataFrame(rows).sort_values("sharpe_opt", ascending=False)
    out_csv = OUT_DIR/"opt_thresholds.csv"
    out_md  = OUT_DIR/"opt_thresholds.md"
    df.to_csv(out_csv, index=False)
    with open(out_md, "w") as f:
        f.write(f"# Umbrales óptimos (calibrated-first) — {dt.datetime.now(dt.UTC).date().isoformat()}\n\n")
        f.write(df.to_markdown(index=False))
    print(str(out_csv))

if __name__=="__main__":
    main()

from __future__ import annotations
from pathlib import Path
import pandas as pd, numpy as np, datetime as dt
from typing import Dict, List

DATA = Path("/Users/sultan/Trading/data")
PREDS_DIR = DATA/"ml"/"preds"
DS_DIR = DATA/"ml"/"datasets"
THR_CSV = DATA/"ml"/"thresholds"/"opt_thresholds.csv"
OUT_DIR = DATA/"checks"/"reports"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_thresholds()->Dict[str,float]:
    if not THR_CSV.exists():
        return {}
    df = pd.read_csv(THR_CSV)
    return {r.symbol: float(r.thr_opt) for _,r in df.iterrows()}

def load_symbol_timeseries(sym:str) -> pd.DataFrame | None:
    p_cal = PREDS_DIR/f"{sym}_preds_cal.csv"
    p_std = PREDS_DIR/f"{sym}_preds.csv"
    p_ds  = DS_DIR/f"symbol={sym}"/"interval=1d"/"data.parquet"
    if not p_ds.exists(): 
        return None
    ds = pd.read_parquet(p_ds)[["date","ret_fwd_1d","close"]].sort_values("date")
    ds["date"] = pd.to_datetime(ds["date"], utc=True)
    if p_cal.exists():
        pr = pd.read_csv(p_cal, parse_dates=["date"]).sort_values("date")
        pr["prob"] = pr["prob_up_cal"]
    elif p_std.exists():
        pr = pd.read_csv(p_std, parse_dates=["date"]).sort_values("date")
        pr["prob"] = pr["prob_up"]
    else:
        return None
    pr["date"] = pd.to_datetime(pr["date"], utc=True)
    df = pr.merge(ds, on="date", how="inner")
    df["symbol"] = sym
    return df

def build_panel(symbols:List[str]) -> pd.DataFrame:
    parts = []
    for s in symbols:
        df = load_symbol_timeseries(s)
        if df is not None and len(df)>50:
            parts.append(df[["date","symbol","prob","ret_fwd_1d"]])
    if not parts:
        return pd.DataFrame()
    out = pd.concat(parts, ignore_index=True).sort_values(["date","symbol"]).reset_index(drop=True)
    return out

def weight_scheme(group: pd.DataFrame, thr_map:Dict[str,float], top_n:int, w_cap:float) -> pd.DataFrame:
    g = group.copy()
    g["thr"] = g["symbol"].map(lambda s: thr_map.get(s, 0.5))
    g["conf"] = (g["prob"] - g["thr"]).abs()
    g["long"] = (g["prob"] >= g["thr"]).astype(int)
    g = g[g["long"]==1]
    if g.empty:
        g["w_raw"]=0.0
        g["w"]=0.0
        return g
    g = g.sort_values("conf", ascending=False).head(top_n)
    total_conf = g["conf"].sum()
    if total_conf <= 0:
        g["w_raw"] = 0.0
    else:
        g["w_raw"] = g["conf"] / total_conf
    g["w_raw"] = g["w_raw"].fillna(0.0)
    g["w_capped"] = g["w_raw"].clip(upper=w_cap)
    cap_sum = g["w_capped"].sum()
    g["w"] = 0.0 if cap_sum==0 else g["w_capped"] / cap_sum
    return g[["symbol","w","conf","thr"]]

def simulate(panel: pd.DataFrame, thr_map:Dict[str,float], fee_bps:float=2.0, top_n:int=5, w_cap:float=0.25, window_days:int=365) -> tuple[pd.DataFrame, pd.DataFrame]:
    if panel.empty:
        return pd.DataFrame(), pd.DataFrame()
    end = panel["date"].max()
    start = end - pd.Timedelta(days=window_days)
    pnl = panel[panel["date"]>=start].copy()
    dates = sorted(pnl["date"].unique())
    fee = fee_bps/10000.0
    all_weights = []
    rets = []
    prev_w = {}
    for d in dates:
        day = pnl[pnl["date"]==d]
        ws = weight_scheme(day, thr_map, top_n=top_n, w_cap=w_cap)
        w_map = {r.symbol: float(r.w) for _,r in ws.iterrows()}
        all_weights.append(pd.DataFrame({"date": d, "symbol": list(w_map.keys()), "weight": list(w_map.values())}))
        day = day.merge(pd.DataFrame({"symbol": list(w_map.keys())}), on="symbol", how="inner")
        pos_yday = prev_w
        pos_today = w_map
        syms = set(pos_yday.keys()) | set(pos_today.keys())
        turnover = sum(abs(pos_today.get(s,0.0)-pos_yday.get(s,0.0)) for s in syms)
        fee_cost = fee * turnover
        gross = sum(pos_yday.get(s,0.0) * float(day.loc[day["symbol"]==s, "ret_fwd_1d"].values[0]) for s in syms if s in set(day["symbol"]))
        net = gross - fee_cost
        rets.append({"date": d, "ret": net, "gross": gross, "fee_cost": fee_cost, "turnover": turnover})
        prev_w = w_map
    weights_df = pd.concat(all_weights, ignore_index=True) if all_weights else pd.DataFrame()
    rets_df = pd.DataFrame(rets).sort_values("date").reset_index(drop=True)
    return weights_df, rets_df

def metrics_from_returns(ret: pd.Series) -> dict:
    ret = ret.fillna(0.0)
    if len(ret)<2:
        return {"CAGR": np.nan, "Sharpe": np.nan, "MaxDD": np.nan, "Vol": np.nan}
    eq = (1+ret).cumprod()
    years = len(ret)/252.0
    cagr = float(eq.iloc[-1]**(1/years)-1) if years>0 else np.nan
    vol = float(ret.std(ddof=0)*np.sqrt(252))
    mu  = float(ret.mean()*252)
    sharpe = mu/vol if vol>0 else np.nan
    maxdd = float((eq/eq.cummax()-1).min())
    return {"CAGR": round(cagr,4), "Sharpe": round(sharpe,4), "MaxDD": round(maxdd,4), "Vol": round(vol,4)}

def main():
    thr_map = load_thresholds()
    syms = sorted({p.stem.replace("_preds_cal","") for p in PREDS_DIR.glob("*_preds_cal.csv")} |
                  {p.stem.replace("_preds","") for p in PREDS_DIR.glob("*_preds.csv")})
    panel = build_panel(syms)
    weights, rets = simulate(panel, thr_map, fee_bps=2.0, top_n=5, w_cap=0.25, window_days=365)
    if rets.empty:
        print("No returns to report.")
        return
    eq = (1+rets["ret"]).cumprod()
    rets["equity"] = eq
    mets = metrics_from_returns(rets["ret"])
    out_eq = OUT_DIR/"portfolio_equity.csv"
    out_m  = OUT_DIR/"portfolio_metrics.csv"
    rets.to_csv(out_eq, index=False)
    pd.DataFrame([mets]).to_csv(out_m, index=False)
    if not weights.empty:
        weights.to_csv(OUT_DIR/"portfolio_weights.csv", index=False)
    print(str(out_eq))
    print(str(out_m))

if __name__=="__main__":
    main()

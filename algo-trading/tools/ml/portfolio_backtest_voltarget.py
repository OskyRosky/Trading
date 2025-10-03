from __future__ import annotations
from pathlib import Path
import pandas as pd, numpy as np

DATA = Path("/Users/sultan/Trading/data")
PREDS = DATA/"ml"/"preds"
DS = DATA/"ml"/"datasets"
THR = DATA/"ml"/"thresholds"/"opt_thresholds.csv"
OUT = DATA/"checks"/"reports"
OUT.mkdir(parents=True, exist_ok=True)

def load_thr() -> dict[str,float]:
    if not THR.exists(): return {}
    df = pd.read_csv(THR)
    return {r.symbol: float(r.thr_opt) for _, r in df.iterrows()}

def load_series(sym:str) -> pd.DataFrame|None:
    p_cal = PREDS/f"{sym}_preds_cal.csv"
    p_std = PREDS/f"{sym}_preds.csv"
    p_ds  = DS/f"symbol={sym}"/"interval=1d"/"data.parquet"
    if not p_ds.exists(): return None
    d = pd.read_parquet(p_ds).sort_values("date")
    d["date"] = pd.to_datetime(d["date"], utc=True)
    if "atr_14" not in d.columns:
        d["ret_abs_1d"] = d["close"].pct_change().abs()
        d["vol20"] = d["ret_abs_1d"].rolling(20).mean()
    else:
        d["vol20"] = d["atr_14"]/d["close"].replace(0,np.nan)
    if p_cal.exists():
        p = pd.read_csv(p_cal, parse_dates=["date"]).sort_values("date")
        p["prob"] = p["prob_up_cal"]
    elif p_std.exists():
        p = pd.read_csv(p_std, parse_dates=["date"]).sort_values("date")
        p["prob"] = p["prob_up"]
    else:
        return None
    p["date"] = pd.to_datetime(p["date"], utc=True)
    df = p.merge(d[["date","ret_fwd_1d","vol20"]], on="date", how="inner").dropna()
    df["symbol"] = sym
    return df

def build_panel(syms:list[str]) -> pd.DataFrame:
    parts=[]
    for s in syms:
        x = load_series(s)
        if x is not None and len(x)>50:
            parts.append(x[["date","symbol","prob","ret_fwd_1d","vol20"]])
    if not parts: return pd.DataFrame()
    return pd.concat(parts, ignore_index=True).sort_values(["date","symbol"]).reset_index(drop=True)

def weights_voltarget(day: pd.DataFrame, thr_map:dict[str,float], top_n:int, w_cap:float, target_vol:float=0.10) -> pd.DataFrame:
    g = day.copy()
    g["thr"] = g["symbol"].map(lambda s: thr_map.get(s,0.5))
    g = g[g["prob"] >= g["thr"]].copy()
    if g.empty:
        return g.assign(w=0.0)[["symbol","w","thr"]]
    g["ivol"] = 1.0 / g["vol20"].clip(lower=1e-6)
    g = g.sort_values("ivol", ascending=False).head(top_n)
    g["w_raw"] = g["ivol"] / g["ivol"].sum()
    g["w_capped"] = g["w_raw"].clip(upper=w_cap)
    s = g["w_capped"].sum()
    g["w"] = 0.0 if s==0 else g["w_capped"]/s
    return g[["symbol","w","thr"]]

def simulate(panel: pd.DataFrame, thr_map:dict[str,float], fee_bps:float=2.0, top_n:int=5, w_cap:float=0.25, window_days:int=365):
    if panel.empty: return pd.DataFrame(), pd.DataFrame()
    end = panel["date"].max()
    start = end - pd.Timedelta(days=window_days)
    pnl = panel[panel["date"]>=start].copy()
    dates = sorted(pnl["date"].unique())
    fee = fee_bps/10000.0
    weights = []
    rets=[]
    prev_w={}
    for d in dates:
        day = pnl[pnl["date"]==d]
        ws = weights_voltarget(day, thr_map, top_n, w_cap)
        w_map = {r.symbol: float(r.w) for _,r in ws.iterrows()}
        weights.append(pd.DataFrame({"date": d, "symbol": list(w_map.keys()), "weight": list(w_map.values())}))
        syms = set(prev_w.keys()) | set(w_map.keys())
        turnover = sum(abs(w_map.get(s,0.0)-prev_w.get(s,0.0)) for s in syms)
        fee_cost = fee * turnover
        gross = sum(prev_w.get(s,0.0)*float(day.loc[day["symbol"]==s,"ret_fwd_1d"].values[0]) for s in syms if s in set(day["symbol"]))
        net = gross - fee_cost
        rets.append({"date": d, "ret": net, "gross": gross, "fee_cost": fee_cost, "turnover": turnover})
        prev_w = w_map
    W = pd.concat(weights, ignore_index=True) if weights else pd.DataFrame()
    R = pd.DataFrame(rets).sort_values("date").reset_index(drop=True)
    return W, R

def metrics(ret: pd.Series) -> dict:
    ret = ret.fillna(0.0)
    if len(ret)<2: return {"CAGR":np.nan,"Sharpe":np.nan,"MaxDD":np.nan,"Vol":np.nan}
    eq = (1+ret).cumprod()
    years = len(ret)/252
    cagr = float(eq.iloc[-1]**(1/years)-1) if years>0 else np.nan
    vol = float(ret.std(ddof=0)*np.sqrt(252))
    mu = float(ret.mean()*252)
    sharpe = mu/vol if vol>0 else np.nan
    maxdd = float((eq/eq.cummax()-1).min())
    return {"CAGR":round(cagr,4),"Sharpe":round(sharpe,4),"MaxDD":round(maxdd,4),"Vol":round(vol,4)}

def main():
    thr_map = load_thr()
    syms = sorted({p.stem.replace("_preds_cal","") for p in PREDS.glob("*_preds_cal.csv")} |
                  {p.stem.replace("_preds","") for p in PREDS.glob("*_preds.csv")})
    panel = build_panel(syms)
    W,R = simulate(panel, thr_map, fee_bps=2.0, top_n=5, w_cap=0.25, window_days=365)
    if R.empty:
        print("No returns.")
        return
    R["equity"] = (1+R["ret"]).cumprod()
    m = metrics(R["ret"])
    pd.DataFrame([m]).to_csv(OUT/"portfolio_metrics_voltarget.csv", index=False)
    R.to_csv(OUT/"portfolio_equity_voltarget.csv", index=False)
    if not W.empty: W.to_csv(OUT/"portfolio_weights_voltarget.csv", index=False)
    print(str(OUT/"portfolio_equity_voltarget.csv"))
    print(str(OUT/"portfolio_metrics_voltarget.csv"))

if __name__=="__main__":
    main()

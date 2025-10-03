from __future__ import annotations
from pathlib import Path
import pandas as pd, numpy as np, yaml, json

BASE=Path("/Users/sultan/Trading/algo-trading")
DATA=Path("/Users/sultan/Trading/data")
SPLIT = pd.Timestamp(yaml.safe_load((BASE/"configs"/"ml.yml").read_text())["split_date"], tz="UTC")

def load_preds(sym):
    df = pd.read_csv(DATA/"ml"/"preds"/f"{sym}_preds.csv", parse_dates=["date"])
    df["date"]=pd.to_datetime(df["date"], utc=True)
    return df[df["date"]>=SPLIT].copy()

def load_supervised(sym):
    df = pd.read_parquet(DATA/"ml"/"datasets"/f"symbol={sym}"/"interval=1d"/"data.parquet")
    df["date"]=pd.to_datetime(df["date"], utc=True)
    return df[["date","ret_fwd_1d"]]

def evaluate(sym, thr, fee_bps):
    preds = load_preds(sym); sup = load_supervised(sym)
    df = preds.merge(sup, on="date", how="inner")
    if df.empty: return None
    fee=fee_bps/10000.0
    side=(df["prob_up"]>=thr).astype(int)
    pos_chg=side.diff().abs().fillna(side).astype(float)
    r=df["ret_fwd_1d"].astype(float)
    strat=(side*r) - fee*pos_chg
    eq=(1+strat).cumprod()
    days=(df["date"].iloc[-1]-df["date"].iloc[0]).days or 1
    years=days/365.25
    cagr=float(eq.iloc[-1]**(1/years)-1) if years>0 else np.nan
    sharpe=float((strat.mean()/ (strat.std(ddof=0) or 1e-9))*np.sqrt(252))
    dd=float((eq/eq.cummax()-1).min())
    return {"symbol":sym,"thr":thr,"CAGR":round(cagr,4),"Sharpe":round(sharpe,4),"MaxDD":round(dd,4)}

def main():
    syms = yaml.safe_load((BASE/"configs"/"symbols.yml").read_text())["symbol_map"].keys()
    thrs = [0.50,0.52,0.55,0.58,0.60,0.62,0.65]
    out=[]
    for s in syms:
        for t in thrs:
            m=evaluate(s,t,2.0)
            if m: out.append(m)
    df=pd.DataFrame(out).sort_values(["symbol","Sharpe"], ascending=[True,False])
    path=DATA/"checks"/"reports"/"ml_thr_sweep.csv"
    df.to_csv(path, index=False)
    best = df.groupby("symbol", as_index=False).first()
    best.to_csv(DATA/"checks"/"reports"/"ml_thr_best.csv", index=False)
    print(json.dumps({"sweep":str(path),"best":str(DATA/'checks'/'reports'/'ml_thr_best.csv')}, indent=2))
if __name__=="__main__":
    main()

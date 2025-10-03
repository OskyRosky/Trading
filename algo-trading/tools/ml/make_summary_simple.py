from __future__ import annotations
from pathlib import Path
import pandas as pd
import re

DATA = Path("/Users/sultan/Trading/data")
REPORTS = DATA/"checks"/"reports"
REPORTS.mkdir(parents=True, exist_ok=True)

def load_metrics_all() -> pd.DataFrame:
    p_all = REPORTS/"ml_metrics_all.csv"
    if p_all.exists():
        df = pd.read_csv(p_all)
        return df[["symbol","acc","precision","recall","auc"]]
    rows=[]
    for p in REPORTS.glob("ml_metrics_*.csv"):
        try:
            r = pd.read_csv(p).iloc[0].to_dict()
            rows.append({k:r.get(k) for k in ["symbol","acc","precision","recall","auc"]})
        except Exception:
            pass
    return pd.DataFrame(rows)

def load_latest_plan() -> pd.DataFrame:
    tp = DATA/"ml"/"trade_plan"
    if not tp.exists():
        return pd.DataFrame()
    candidates = sorted(tp.glob("plan_*.csv"))
    if not candidates:
        return pd.DataFrame()
    latest = max(candidates, key=lambda x: x.name)
    df = pd.read_csv(latest)
    df["plan_file"] = latest.as_posix()
    return df

def latest_probs() -> pd.DataFrame:
    preds_dir = DATA/"ml"/"preds"
    rows=[]
    for p in preds_dir.glob("*_preds_cal.csv"):
        sym = p.name.replace("_preds_cal.csv","")
        df = pd.read_csv(p, parse_dates=["date"]).sort_values("date")
        if len(df)==0: 
            continue
        rows.append({"symbol":sym,"prob":float(df.iloc[-1]["prob_up_cal"]),"prob_src":"cal","prob_date":df.iloc[-1]["date"]})
    for p in preds_dir.glob("*_preds.csv"):
        sym = p.name.replace("_preds.csv","")
        if any(r["symbol"]==sym for r in rows):
            continue
        df = pd.read_csv(p, parse_dates=["date"]).sort_values("date")
        if len(df)==0: 
            continue
        rows.append({"symbol":sym,"prob":float(df.iloc[-1]["prob_up"]),"prob_src":"std","prob_date":df.iloc[-1]["date"]})
    return pd.DataFrame(rows)

def load_thresholds() -> pd.DataFrame:
    p = DATA/"ml"/"thresholds"/"opt_thresholds.csv"
    if not p.exists():
        return pd.DataFrame(columns=["symbol","thr_opt"])
    df = pd.read_csv(p)
    cols = [c for c in df.columns]
    if "thr_opt" not in cols:
        return pd.DataFrame(columns=["symbol","thr_opt"])
    return df[["symbol","thr_opt"]].rename(columns={"thr_opt":"thr"})

def main():
    met = load_metrics_all()
    plan = load_latest_plan()
    probs = latest_probs()
    th = load_thresholds()
    base = probs.merge(th, on="symbol", how="left")
    base["thr"] = base["thr"].fillna(0.5)
    base["side"] = (base["prob"] >= base["thr"]).map({True:"LONG", False:"FLAT"})
    base["confidence"] = (base["prob"] - base["thr"]).abs()
    out = base.merge(met, on="symbol", how="left")
    cols = ["symbol","prob","prob_src","thr","side","confidence","acc","precision","recall","auc","prob_date"]
    out = out[cols].sort_values(["side","confidence","prob"], ascending=[True,False,False]).reset_index(drop=True)
    if not plan.empty and {"symbol","side","confidence"}.issubset(plan.columns):
        plan_top = plan.sort_values(["side","confidence","prob"], ascending=[True,False,False]).head(5)
        plan_top["is_top5_plan"] = True
        out = out.merge(plan_top[["symbol","is_top5_plan"]], on="symbol", how="left")
        out["is_top5_plan"] = out["is_top5_plan"].fillna(False)
    else:
        out["is_top5_plan"] = False
    out_path = REPORTS/"ml_summary.csv"
    out.to_csv(out_path, index=False)
    print(out_path.as_posix())

if __name__ == "__main__":
    main()

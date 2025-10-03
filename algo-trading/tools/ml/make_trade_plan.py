from __future__ import annotations
from pathlib import Path
import pandas as pd
import datetime as dt

DATA = Path("/Users/sultan/Trading/data")

def load_thresholds() -> dict[str,float]:
    fp = DATA/"ml"/"thresholds"/"opt_thresholds.csv"
    if not fp.exists(): return {}
    df = pd.read_csv(fp)
    return {r.symbol: float(r.thr_opt) for _,r in df.iterrows()}

def latest_prob(sym:str) -> tuple[float,str]:
    p_cal = DATA/"ml"/"preds"/f"{sym}_preds_cal.csv"
    p_std = DATA/"ml"/"preds"/f"{sym}_preds.csv"
    if p_cal.exists():
        df = pd.read_csv(p_cal, parse_dates=["date"]).sort_values("date")
        return float(df.iloc[-1]["prob_up_cal"]), "cal"
    elif p_std.exists():
        df = pd.read_csv(p_std, parse_dates=["date"]).sort_values("date")
        return float(df.iloc[-1]["prob_up"]), "std"
    else:
        return 0.5, "none"

def main():
    preds_dir = DATA/"ml"/"preds"
    out_dir = DATA/"ml"/"trade_plan"
    out_dir.mkdir(parents=True, exist_ok=True)
    thr_map = load_thresholds()
    rows = []
    syms = sorted({p.stem.replace("_preds_cal","") for p in preds_dir.glob("*_preds_cal.csv")} |
                  {p.stem.replace("_preds","") for p in preds_dir.glob("*_preds.csv")})
    for sym in syms:
        prob, src = latest_prob(sym)
        thr = thr_map.get(sym, 0.5)
        side = "LONG" if prob >= thr else "FLAT"
        conf = abs(prob - thr)
        rows.append({"symbol": sym, "prob": prob, "prob_src": src, "thr": thr, "side": side, "confidence": conf})
    plan = pd.DataFrame(rows).sort_values(["side","confidence","prob"], ascending=[True,False,False])
    today = dt.datetime.now(dt.UTC).date().isoformat()
    out = out_dir/f"plan_{today}.csv"
    plan.to_csv(out, index=False)
    print(str(out))

if __name__ == "__main__":
    main()

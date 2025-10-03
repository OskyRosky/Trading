from __future__ import annotations
from pathlib import Path
import pandas as pd, numpy as np, datetime as dt

DATA = Path("/Users/sultan/Trading/data")
PREDS = DATA/"ml"/"preds"
DATASETS = DATA/"ml"/"datasets"
THR = DATA/"ml"/"thresholds"/"opt_thresholds.csv"
OUT = DATA/"checks"/"reports"

def load_thr_map() -> dict[str,float]:
    if not THR.exists():
        return {}
    df = pd.read_csv(THR)
    return {r.symbol: float(r.thr_opt) for _, r in df.iterrows()}

def strat_returns(prob_up: pd.Series, ret_fwd_1d: pd.Series, thr: float, fee_bps: float) -> tuple[pd.Series, pd.Series]:
    fee = fee_bps/10000.0
    pos = (prob_up >= thr).astype(int)
    ret = pos * ret_fwd_1d
    turn = pos.diff().abs().fillna(pos)
    ret = ret - fee*turn
    return ret, turn

def metrics(ret: pd.Series) -> dict:
    ret = ret.fillna(0.0)
    eq = (1+ret).cumprod()
    days = len(ret)
    if days < 2:
        return {"CAGR": np.nan, "Sharpe": np.nan, "MaxDD": np.nan}
    years = days/252
    cagr = float(eq.iloc[-1]**(1/years)-1) if years>0 else np.nan
    mu, sd = ret.mean(), ret.std(ddof=0) or 1e-9
    sharpe = float((mu/sd)*np.sqrt(252))
    maxdd = float((eq/eq.cummax()-1).min())
    return {"CAGR": round(cagr,4), "Sharpe": round(sharpe,4), "MaxDD": round(maxdd,4)}

def backtest_pair(sym: str, window_days: int, fee_bps: float, thr_opt_map: dict[str,float]) -> dict | None:
    p_pred = PREDS/f"{sym}_preds.csv"
    p_ds = DATASETS/f"symbol={sym}"/"interval=1d"/"data.parquet"
    if not p_pred.exists() or not p_ds.exists():
        return None
    preds = pd.read_csv(p_pred, parse_dates=["date"]).sort_values("date")
    ds = pd.read_parquet(p_ds)[["date","ret_fwd_1d"]].sort_values("date")
    preds["date"] = pd.to_datetime(preds["date"], utc=True)
    ds["date"] = pd.to_datetime(ds["date"], utc=True)
    df = preds.merge(ds, on="date", how="inner").dropna(subset=["prob_up","ret_fwd_1d"])
    if df.empty:
        return None
    end = df["date"].max()
    start = end - pd.Timedelta(days=window_days)
    df = df[df["date"] >= start].reset_index(drop=True)
    if len(df) < 30:
        return None
    ret05, turn05 = strat_returns(df["prob_up"], df["ret_fwd_1d"], 0.5, fee_bps)
    m05 = metrics(ret05)
    thr_opt = thr_opt_map.get(sym, 0.5)
    reto, turno = strat_returns(df["prob_up"], df["ret_fwd_1d"], thr_opt, fee_bps)
    mo = metrics(reto)
    n_trades_05 = int(turn05.sum())
    n_trades_opt = int(turno.sum())
    return {
        "symbol": sym,
        "window_days": window_days,
        "fee_bps": fee_bps,
        "thr_fixed": 0.5,
        "thr_opt": thr_opt,
        "CAGR_fixed": m05["CAGR"],
        "Sharpe_fixed": m05["Sharpe"],
        "MaxDD_fixed": m05["MaxDD"],
        "Trades_fixed": n_trades_05,
        "CAGR_opt": mo["CAGR"],
        "Sharpe_opt": mo["Sharpe"],
        "MaxDD_opt": mo["MaxDD"],
        "Trades_opt": n_trades_opt,
        "Sharpe_uplift": round(mo["Sharpe"] - m05["Sharpe"], 4),
        "CAGR_uplift": round(mo["CAGR"] - m05["CAGR"], 4),
    }

def main():
    thr_map = load_thr_map()
    syms = sorted([p.stem.replace("_preds","") for p in PREDS.glob("*_preds.csv")])
    rows = []
    for s in syms:
        res = backtest_pair(s, window_days=365, fee_bps=2.0, thr_opt_map=thr_map)
        if res:
            rows.append(res)
    if not rows:
        print("No hay resultados.")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows).sort_values("Sharpe_opt", ascending=False)
    csv = OUT/"ml_thr_compare.csv"
    df.to_csv(csv, index=False)
    md = OUT/"ml_thr_compare.md"
    with open(md, "w") as f:
        f.write(f"# Compare thresholds (últimos 365d) — {dt.datetime.now(dt.UTC).date().isoformat()}\n\n")
        f.write(df[["symbol","Sharpe_fixed","Sharpe_opt","Sharpe_uplift","CAGR_fixed","CAGR_opt","CAGR_uplift","MaxDD_fixed","MaxDD_opt","Trades_fixed","Trades_opt","thr_opt"]].to_markdown(index=False))
    print(str(csv))
    print(str(md))

if __name__ == "__main__":
    main()

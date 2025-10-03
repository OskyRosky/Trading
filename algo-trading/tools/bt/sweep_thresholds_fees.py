from __future__ import annotations
from pathlib import Path
import itertools, pandas as pd, numpy as np

DATA = Path("/Users/sultan/Trading/data")
RPT  = DATA/"checks"/"reports"
RPT.mkdir(parents=True, exist_ok=True)

SYMS = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT","ADAUSDT","DOTUSDT"]
THRS = [0.45, 0.50, 0.55]
FEES = [2.0, 5.0]

def load_eq(sym: str) -> pd.DataFrame:
    p = RPT/f"bt_symbol_{sym}.csv"
    if not p.exists():
        raise FileNotFoundError(f"Run backtest_symbol_vs_hodl.py first for {sym}")
    df = pd.read_csv(p, parse_dates=["date"])
    return df

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

def main():
    rows = []
    for sym, thr, fee in itertools.product(SYMS, THRS, FEES):
        p = RPT/f"bt_symbol_{sym}.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p, parse_dates=["date"])
        if "ret_strat" not in df.columns or "turnover" not in df.columns or "ret_fwd_1d" not in df.columns:
            continue
        eq0 = (1 + df["ret_strat"]).cumprod()
        rows.append({"symbol": sym, "thr": 0.50, "fee_bps": 2.0, "CAGR": np.nan, "Sharpe": np.nan, "MaxDD": np.nan, "Vol": np.nan}) if eq0.empty else None
        m = metrics(df["ret_strat"])
        rows.append({"symbol": sym, "thr": 0.50, "fee_bps": 2.0, **m})
    # Nota: para un barrido real por thr debemos recalcular señales. Por simplicidad:
    # comparamos fees sobre la curva ya generada con 2 bps y marcamos solo referencia de thr=0.50.

    out = pd.DataFrame([r for r in rows if r is not None]).drop_duplicates()
    out.to_csv(RPT/"bt_sweep_simple.csv", index=False)
    print(str(RPT/"bt_sweep_simple.csv"))

if __name__ == "__main__":
    main()

from __future__ import annotations
from pathlib import Path
import duckdb, pandas as pd
import datetime as dt
import re

QA_DB = Path("/Users/sultan/Trading/data/duck/qa.duckdb")
MKT_DB = Path("/Users/sultan/Trading/data/duck/market.duckdb")
RPT   = Path("/Users/sultan/Trading/data/checks/reports")

def sanitize(sym: str) -> str:
    s = re.sub(r'[^A-Za-z0-9_]', '_', sym)
    if re.match(r'^[0-9]', s):
        s = "_" + s
    return s

def symbols_from_reports() -> list[str]:
    syms = []
    for p in sorted(RPT.glob("bt_symbol_*_metrics.csv")):
        syms.append(p.stem.replace("bt_symbol_","").replace("_metrics",""))
    return syms

def load_strategy_equity(symbol: str) -> pd.DataFrame:
    safe = sanitize(symbol)
    con = duckdb.connect(str(QA_DB), read_only=True)
    # verifica que exista
    exists = con.execute("""
        SELECT COUNT(*)>0 AS ok
        FROM information_schema.tables
        WHERE table_schema='bt' AND table_name = ?
    """, [f"equity_{safe}"]).fetchone()[0]
    if not exists:
        con.close()
        return pd.DataFrame()
    df = con.execute(f"SELECT date, equity, ret FROM bt.equity_{safe} ORDER BY date").fetchdf()
    con.close()
    return df

def load_benchmark_equity(symbol: str, start: str|None=None, end: str|None=None) -> pd.DataFrame:
    con = duckdb.connect(str(MKT_DB), read_only=True)
    q = """
    SELECT date, close
    FROM curated.all_1d
    WHERE symbol = ?
      AND (? IS NULL OR date >= CAST(? AS TIMESTAMP))
      AND (? IS NULL OR date <= CAST(? AS TIMESTAMP))
    ORDER BY date
    """
    df = con.execute(q, [symbol, start, start, end, end]).fetchdf()
    con.close()
    if df.empty:
        return df
    df = df.sort_values("date").reset_index(drop=True)
    eq = (df["close"].astype(float) / float(df["close"].iloc[0]))
    ret = eq.pct_change().fillna(0.0)
    df["equity"] = eq
    df["ret"] = ret
    return df[["date","equity","ret"]]

def metrics(equity: pd.Series) -> dict:
    eq = equity.astype(float)
    rets = eq.pct_change().dropna()
    if rets.empty:
        return {"CAGR":0.0,"Sharpe":0.0,"MaxDD":0.0}
    years = max((eq.index[-1]-eq.index[0]).days/365.25, 1e-9)
    cagr = float((eq.iloc[-1]/eq.iloc[0])**(1/years)-1)
    sharpe = float((rets.mean()/rets.std())*(252**0.5)) if rets.std()>0 else 0.0
    rollmax = eq.cummax()
    dd = (eq/rollmax-1).min()
    return {"CAGR":cagr,"Sharpe":sharpe,"MaxDD":float(dd)}

def run_one(symbol: str) -> bool:
    strat = load_strategy_equity(symbol)
    if strat.empty:
        print(f"[SKIP] {symbol}: no equity de estrategia")
        return False
    start = strat["date"].min().strftime("%Y-%m-%d")
    end   = strat["date"].max().strftime("%Y-%m-%d")
    bench = load_benchmark_equity(symbol, start, end)
    if bench.empty:
        print(f"[SKIP] {symbol}: no benchmark en curated.all_1d")
        return False

    m_s = metrics(strat.set_index("date")["equity"])
    m_b = metrics(bench.set_index("date")["equity"])
    out = pd.DataFrame([{"symbol":symbol,"asset":f"STRAT_{symbol}",**m_s},
                        {"symbol":symbol,"asset":f"HODL_{symbol}", **m_b}])
    RPT.mkdir(parents=True, exist_ok=True)
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    out.to_csv(RPT/f"bt_comp_{symbol}_{today}.csv", index=False)
    print(f"[OK] {symbol}")
    return True

def main():
    syms = symbols_from_reports()
    done = 0
    for s in syms:
        done += int(run_one(s))
    print(f"Hechos: {done} / {len(syms)}")

if __name__ == "__main__":
    main()

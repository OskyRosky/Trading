from __future__ import annotations
import argparse, duckdb, pandas as pd, numpy as np

DATA_DB = "/Users/sultan/Trading/data/duck/market.duckdb"

def load(symbol: str, start: str=None, end: str=None) -> pd.DataFrame:
    con = duckdb.connect(DATA_DB)
    tbl = f"trusted.{symbol.lower()}_1d"
    try:
        df = con.execute(f"SELECT * FROM {tbl}").fetchdf()
    except Exception:
        rows = con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='trusted'").fetchdf()
        cand = [t for t in rows.table_name if symbol.lower() in t]
        if not cand:
            raise SystemExit(f"No encuentro vista trusted para {symbol}")
        df = con.execute(f"SELECT * FROM trusted.{cand[0]}").fetchdf()
    if start:
        df = df[df["date"] >= pd.Timestamp(start, tz="UTC")]
    if end:
        df = df[df["date"] <= pd.Timestamp(end, tz="UTC")]
    df = df.sort_values("date").reset_index(drop=True)
    return df

def strat_sma_adx(df: pd.DataFrame, adx_min: float=15.0, fee_bps: float=2.0) -> pd.DataFrame:
    sig = (df["sma_7"] > df["sma_20"]).astype(int)
    if "adx_14" in df:
        sig = sig.where(df["adx_14"] >= adx_min, 0)
    ret = df["close"].pct_change().fillna(0.0)
    pos = sig.shift(1).fillna(0.0)
    chg = pos.diff().abs().fillna(pos)
    fee = chg * (fee_bps/10000.0)
    strat_ret = pos * ret - fee
    eq = (1 + strat_ret).cumprod()
    return pd.DataFrame({"date": df["date"], "equity": eq, "strat_ret": strat_ret})

def strat_bb_breakout(df: pd.DataFrame, fee_bps: float=2.0) -> pd.DataFrame:
    long_sig = (df["close"] > df["bb_u_20_2"]).astype(int)
    ret = df["close"].pct_change().fillna(0.0)
    pos = long_sig.shift(1).fillna(0.0)
    chg = pos.diff().abs().fillna(pos)
    fee = chg * (fee_bps/10000.0)
    strat_ret = pos * ret - fee
    eq = (1 + strat_ret).cumprod()
    return pd.DataFrame({"date": df["date"], "equity": eq, "strat_ret": strat_ret})

def metrics(eq: pd.Series, rets: pd.Series, dates: pd.Series) -> dict:
    if len(eq) == 0:
        return {"CAGR": np.nan, "Sharpe": np.nan, "MaxDD": np.nan}
    d0 = pd.to_datetime(dates.iloc[0]); d1 = pd.to_datetime(dates.iloc[-1])
    years = max((d1 - d0).days / 365.25, 1e-9)
    total = float(eq.iloc[-1])
    cagr = total**(1/years) - 1
    vol = float(rets.std()) * np.sqrt(252)
    sharpe = (float(rets.mean()) * 252) / (vol + 1e-12)
    dd = float((eq / eq.cummax() - 1).min())
    return {"CAGR": cagr, "Sharpe": sharpe, "MaxDD": dd}

def main():
    ap = argparse.ArgumentParser(description="Backtests base: SMA+ADX y Bollinger breakout")
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--start", default="2020-01-01")
    ap.add_argument("--fee_bps", type=float, default=2.0)
    ap.add_argument("--adx_min", type=float, default=15.0)
    args = ap.parse_args()

    df = load(args.symbol, args.start, None)
    r1 = strat_sma_adx(df, adx_min=args.adx_min, fee_bps=args.fee_bps)
    r2 = strat_bb_breakout(df, fee_bps=args.fee_bps)

    m1 = metrics(r1["equity"], r1["strat_ret"], r1["date"])
    m2 = metrics(r2["equity"], r2["strat_ret"], r2["date"])

    print(f"SMA+ADX {args.symbol}:", {k: round(v,4) for k,v in m1.items()})
    print(f"BBreak {args.symbol}:", {k: round(v,4) for k,v in m2.items()})

if __name__ == "__main__":
    main()

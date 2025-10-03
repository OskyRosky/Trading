from __future__ import annotations
import argparse, duckdb, pandas as pd, numpy as np, pathlib

DATA_DB = "/Users/sultan/Trading/data/duck/market.duckdb"

def load_series(symbol: str, start: str=None, end: str=None) -> pd.DataFrame:
    con = duckdb.connect(DATA_DB)
    con.execute("INSTALL parquet; LOAD parquet;")
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

def backtest_long_sma(df: pd.DataFrame, fee_bps: float=2.0, use_rsi: bool=True) -> pd.DataFrame:
    sig = (df["sma_7"] > df["sma_20"]).astype(int)
    if use_rsi and "rsi_14" in df:
        cond = (df["rsi_14"] >= 30) & (df["rsi_14"] <= 70)
        sig = sig.where(cond, 0)

    ret = df["close"].pct_change().fillna(0.0)
    pos = sig.shift(1).fillna(0.0)
    chg = pos.diff().abs().fillna(pos)
    fee = chg * (fee_bps/10000.0)
    strat_ret = pos * ret - fee
    eq = (1.0 + strat_ret).cumprod()

    out = pd.DataFrame({
        "date": df["date"],
        "close": df["close"],
        "pos": pos,
        "ret": ret,
        "strat_ret": strat_ret,
        "equity": eq
    })
    return out

def metrics(equity: pd.Series, rets: pd.Series, dates: pd.Series | None = None) -> dict:
    if len(equity) == 0:
        return {"CAGR": np.nan, "Sharpe": np.nan, "MaxDD": np.nan}
    if dates is not None and len(dates) > 1:
        try:
            d0 = pd.to_datetime(dates.iloc[0])
            d1 = pd.to_datetime(dates.iloc[-1])
            years = max((d1 - d0).days / 365.25, 1e-9)
        except Exception:
            years = max(len(equity) / 252.0, 1e-9)
    else:
        years = max(len(equity) / 252.0, 1e-9)

    total = float(equity.iloc[-1])
    cagr = total**(1/years) - 1
    vol = float(rets.std()) * np.sqrt(252)
    sharpe = (float(rets.mean()) * 252) / (vol + 1e-12)
    dd = float((equity / equity.cummax() - 1).min())
    return {"CAGR": cagr, "Sharpe": sharpe, "MaxDD": dd}

def main():
    ap = argparse.ArgumentParser(description="Backtest SMA(7/20) + filtro RSI")
    ap.add_argument("--symbol", required=True, help="BTCUSDT, ETHUSDT, etc.")
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--fee_bps", type=float, default=2.0, help="comisión ida/vuelta en bps por cambio de posición")
    ap.add_argument("--no_rsi", action="store_true", help="desactiva filtro RSI")
    ap.add_argument("--out", default="/Users/sultan/Trading/data/checks/reports/equity_curve.csv")
    args = ap.parse_args()

    df = load_series(args.symbol, args.start, args.end)
    bt = backtest_long_sma(df, fee_bps=args.fee_bps, use_rsi=not args.no_rsi)
    bt.to_csv(args.out, index=False)

    m = metrics(bt["equity"].reset_index(drop=True), bt["strat_ret"].fillna(0), dates=bt["date"].reset_index(drop=True))
    print(f"Metrics {args.symbol}: ", {k: round(v,4) for k,v in m.items()})
    print(f"Equity curve CSV: {args.out}")

if __name__ == "__main__":
    main()

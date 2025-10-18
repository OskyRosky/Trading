from __future__ import annotations
from pathlib import Path
import os
import datetime as dt
import duckdb, pandas as pd
import math

from order_adapter_testnet import from_env

QA_DB = Path("/Users/sultan/Trading/data/duck/qa.duckdb")
TRUSTED_ROOT = Path("/Users/sultan/Trading/data/trusted/market=futures/segment=usdtm/contract=perpetual")
PLAN_DIR = Path("/Users/sultan/Trading/data/ml/trade_plan")
FEE_BPS = 2  # igual al paper
DEFAULT_EQUITY = 10_000.0

def latest_mark(con: duckdb.DuckDBPyConnection, symbol: str) -> float | None:
    pat = str(TRUSTED_ROOT / f"symbol={symbol}" / "interval=1d" / "**" / "data.parquet")
    q = f"""
      SELECT close
      FROM read_parquet('{pat}', hive_partitioning=1)
      ORDER BY date DESC
      LIMIT 1
    """
    try:
        df = con.execute(q).fetchdf()
        if df.empty or pd.isna(df["close"].iloc[0]):
            return None
        return float(df["close"].iloc[0])
    except Exception:
        return None

def get_equity(con: duckdb.DuckDBPyConnection, today: str) -> float:
    df = con.execute("SELECT equity FROM live.account WHERE as_of <= ? ORDER BY as_of DESC LIMIT 1", [today]).fetchdf()
    if df.empty:
        return DEFAULT_EQUITY
    return float(df["equity"].iloc[0])

def main():
    today_iso = dt.datetime.now(dt.timezone.utc).date().isoformat()
    plan_path = PLAN_DIR / f"plan_{today_iso}.csv"
    if not plan_path.exists():
        print(f"No hay trade_plan para {today_iso}: {plan_path}")
        return

    con = duckdb.connect(str(QA_DB))
    # Idempotencia del día
    con.execute("DELETE FROM live.positions WHERE as_of = ?", [today_iso])
    con.execute("DELETE FROM live.pnl_daily WHERE as_of = ?", [today_iso])
    con.execute("DELETE FROM live.fills WHERE as_of = ?", [today_iso])

    plan = pd.read_csv(plan_path)
    if "side" not in plan.columns:
        print("Plan sin columna 'side'.")
        con.close(); return

    plan = plan[plan["side"].str.upper().isin(["BUY","LONG"])].copy()
    if plan.empty:
        print("Plan sin compras. Nada que hacer.")
        con.close(); return

    # Derivar pesos si no vienen
    if "weight_pct" not in plan.columns:
        if not {"prob","thr"}.issubset(plan.columns):
            print("Plan sin weight_pct ni (prob,thr).")
            con.close(); return
        plan["w_raw"] = (plan["prob"] - plan["thr"]).clip(lower=0.0)
        wsum = plan["w_raw"].sum()
        if wsum <= 0:
            print("Pesos nulos.")
            con.close(); return
        plan["weight_pct"] = plan["w_raw"] / wsum

    equity = get_equity(con, today_iso)
    adapter = from_env()  # usa ENABLE_TESTNET

    fills = []
    total_fee = 0.0
    for _, row in plan.iterrows():
        sym = str(row["symbol"])
        w = float(row["weight_pct"])
        if w <= 0: 
            continue
        mark = latest_mark(con, sym)
        if not mark or mark <= 0:
            continue

        target_usd = equity * w
        qty = target_usd / mark
        qty = float(qty)

        # Ejecuta (real si ENABLE_TESTNET=1, simulado si =0)
        side = "BUY"
        resp = adapter.market_order(symbol=sym, side=side, quantity=qty)

        # Determina precio usado para log: si API devolvió price úsalo, sino mark
        px = float(resp.get("price") or mark)
        fee = px * qty * (FEE_BPS / 10_000.0)
        total_fee += fee

        fills.append({"as_of": today_iso, "symbol": sym, "side": "BUY", "qty": qty, "price": px, "fee": fee})

    if not fills:
        print("No se generaron fills.")
        con.close(); return

    df_fills = pd.DataFrame(fills)
    con.register("df_fills", df_fills)
    con.execute("INSERT INTO live.fills SELECT * FROM df_fills;")

    pos = df_fills.groupby("symbol", as_index=False).agg(qty=("qty","sum"))
    pos["as_of"] = today_iso
    pos["mark"] = pos["symbol"].apply(lambda s: latest_mark(con, s) or 0.0)
    con.register("df_pos", pos[["as_of","symbol","qty","mark"]])
    con.execute("INSERT INTO live.positions SELECT * FROM df_pos;")

    pos["value"] = pos["qty"] * pos["mark"]
    equity_mark = float(pos["value"].sum())
    con.execute("INSERT INTO live.pnl_daily VALUES (?, ?, ?)", [today_iso, equity_mark, total_fee])

    mode = "TESTNET REAL" if os.getenv("ENABLE_TESTNET","0") == "1" else "DRY-RUN"
    print(f"[{mode}] Trade OK ({today_iso}) Fills={len(fills)} Positions={len(pos)} equity_mark={equity_mark:.2f} fees={total_fee:.4f}")

    con.close()

if __name__ == "__main__":
    main()

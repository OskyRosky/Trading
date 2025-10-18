from __future__ import annotations
from pathlib import Path
import datetime as dt
import duckdb, pandas as pd

QA_DB = Path("/Users/sultan/Trading/data/duck/qa.duckdb")

# Ruta de trusted (precios 1d por símbolo)
TRUSTED_ROOT = Path("/Users/sultan/Trading/data/trusted/market=futures/segment=usdtm/contract=perpetual")

FEE_BPS = 20  # 2 bps = 0.02%

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

def get_equity(con: duckdb.DuckDBPyConnection, as_of_iso: str) -> float:
    # equity del último día disponible; si no hay, 10000
    con.execute("CREATE SCHEMA IF NOT EXISTS live;")
    con.execute("CREATE TABLE IF NOT EXISTS live.account (as_of DATE, equity DOUBLE);")
    row = con.execute("SELECT equity FROM live.account ORDER BY as_of DESC LIMIT 1").fetchone()
    return float(row[0]) if row else 10000.0

def main():
    today_iso = dt.datetime.now(dt.timezone.utc).date().isoformat()
    plan_path = Path(f"/Users/sultan/Trading/data/ml/trade_plan/plan_{today_iso}.csv")
    if not plan_path.exists():
        print(f"No existe plan: {plan_path}")
        return

    con = duckdb.connect(str(QA_DB))

    plan = pd.read_csv(plan_path)
    if "symbol" not in plan.columns or "side" not in plan.columns:
        print("Plan sin columnas necesarias ('symbol','side'). No se ejecuta.")
        con.close()
        return

    # Normalizar side y mapear LONG -> BUY
    plan["side"] = plan["side"].astype(str).str.upper().str.strip()
    plan["side"] = plan["side"].replace({"LONG": "BUY"})
    plan = plan[plan["side"] == "BUY"].copy()
    if plan.empty:
        print("Plan sin compras (solo FLAT/SELL). No se ejecuta.")
        con.close()
        return

    # Derivar pesos si no hay weight_pct
    if "weight_pct" not in plan.columns:
        if not {"prob", "thr"}.issubset(plan.columns):
            print("Plan no tiene weight_pct ni (prob,thr) para derivarlo. No se ejecuta.")
            con.close()
            return
        plan["w_raw"] = (plan["prob"] - plan["thr"]).clip(lower=0.0)
        wsum = plan["w_raw"].sum()
        if wsum <= 0:
            print("Plan derivó pesos nulos (prob<=thr). No se ejecuta.")
            con.close()
            return
        plan["weight_pct"] = plan["w_raw"] / wsum

    equity = get_equity(con, today_iso)

    fills = []
    total_fee = 0.0
    for _, row in plan.iterrows():
        sym = str(row["symbol"])
        w = float(row["weight_pct"])
        if w <= 0:
            continue
        px = latest_mark(con, sym)
        if px is None or px <= 0:
            continue
        target_value = equity * w
        qty = target_value / px
        fee = px * qty * (FEE_BPS / 10000.0)
        fills.append({"as_of": today_iso, "symbol": sym, "side": "BUY", "qty": qty, "price": px, "fee": fee})
        total_fee += fee

    if not fills:
        print("Plan con compras, pero no se logró calcular fills (precios faltantes o pesos nulos).")
        con.close()
        return

    df_fills = pd.DataFrame(fills)
    con.register("df_fills", df_fills)
    con.execute("CREATE TABLE IF NOT EXISTS live.fills (as_of DATE, symbol VARCHAR, side VARCHAR, qty DOUBLE, price DOUBLE, fee DOUBLE);")
    con.execute("INSERT INTO live.fills SELECT * FROM df_fills;")

    pos = df_fills.groupby("symbol", as_index=False).agg(qty=("qty","sum"))
    pos["as_of"] = today_iso
    pos["mark"] = pos["symbol"].apply(lambda s: latest_mark(con, s) or 0.0)
    con.register("df_pos", pos[["as_of","symbol","qty","mark"]])
    con.execute("CREATE TABLE IF NOT EXISTS live.positions (as_of DATE, symbol VARCHAR, qty DOUBLE, mark DOUBLE);")
    con.execute("INSERT INTO live.positions SELECT * FROM df_pos;")

    pos["value"] = pos["qty"] * pos["mark"]
    equity_mark = float(pos["value"].sum())
    con.execute("CREATE TABLE IF NOT EXISTS live.pnl_daily (as_of DATE, equity_mark DOUBLE, fees DOUBLE);")
    con.execute("INSERT INTO live.pnl_daily VALUES (?, ?, ?)", [today_iso, equity_mark, total_fee])

    print(f"Paper trade OK ({today_iso})")
    print(f"Fills: {len(df_fills)}  |  Positions: {len(pos)}  |  equity_mark: {equity_mark:.2f}  |  fees: {total_fee:.4f}")
    print(f"Plan: {plan_path}")
    con.close()

if __name__ == "__main__":
    main()

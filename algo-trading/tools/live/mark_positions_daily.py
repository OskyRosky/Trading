# tools/live/mark_positions_daily.py
from __future__ import annotations
from pathlib import Path
import datetime as dt
import duckdb, pandas as pd

DB = Path("/Users/sultan/Trading/data/duck/qa.duckdb")

# Ruta TRST con particionado hive
TRUSTED_ROOT = Path("/Users/sultan/Trading/data/trusted/market=futures/segment=usdtm/contract=perpetual")

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

def main():
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()

    con = duckdb.connect(str(DB))
    con.execute("CREATE SCHEMA IF NOT EXISTS live;")
    con.execute("""
        CREATE TABLE IF NOT EXISTS live.positions (
          as_of DATE, symbol VARCHAR, qty DOUBLE, mark DOUBLE
        );
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS live.fills (
          as_of DATE, symbol VARCHAR, side VARCHAR, qty DOUBLE, price DOUBLE, fee DOUBLE
        );
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS live.pnl_daily (
          as_of DATE, equity_mark DOUBLE, fees DOUBLE
        );
    """)

    # --- Idempotencia: limpiar el día antes de recalcular ---
    con.execute("DELETE FROM live.positions WHERE as_of = ?", [today])
    con.execute("DELETE FROM live.pnl_daily WHERE as_of = ?", [today])

    # Construir posiciones del día a partir de fills de hoy (si existen)
    fills = con.execute(
        "SELECT symbol, SUM(CASE WHEN side='BUY' THEN qty ELSE -qty END) AS qty_net "
        "FROM live.fills WHERE as_of = ? GROUP BY symbol", [today]
    ).fetchdf()

    # Si no hay fills hoy, mantener posiciones del plan de hoy (si quedaron cargadas por el paper_trade)
    if fills.empty:
        # Nada que marcar hoy
        print(f"Mark-to-market OK ({today}) | positions=0 | equity_mark=0.00")
        con.close()
        return

    # Filtrar símbolos con qty > 0
    fills = fills[(fills["qty_net"] > 0) & (~fills["symbol"].isna())].copy()
    if fills.empty:
        print(f"Mark-to-market OK ({today}) | positions=0 | equity_mark=0.00")
        con.close()
        return

    # Obtener marks
    rows = []
    for _, r in fills.iterrows():
        sym = str(r["symbol"])
        qty = float(r["qty_net"])
        px = latest_mark(con, sym) or 0.0
        if qty > 0 and px > 0:
            rows.append({"as_of": today, "symbol": sym, "qty": qty, "mark": px})

    if not rows:
        print(f"Mark-to-market OK ({today}) | positions=0 | equity_mark=0.00")
        con.close()
        return

    df_pos = pd.DataFrame(rows)
    con.register("df_pos", df_pos)
    con.execute("INSERT INTO live.positions SELECT * FROM df_pos;")

    equity_mark = float((df_pos["qty"] * df_pos["mark"]).sum())

    # Fees del día (si existen en fills)
    fees = con.execute("SELECT COALESCE(SUM(fee),0) FROM live.fills WHERE as_of = ?", [today]).fetchone()[0]
    con.execute("INSERT INTO live.pnl_daily VALUES (?, ?, ?)", [today, equity_mark, float(fees)])

    print(f"Mark-to-market OK ({today}) | positions={len(df_pos)} | equity_mark={equity_mark:.2f}")
    con.close()

if __name__ == "__main__":
    main()
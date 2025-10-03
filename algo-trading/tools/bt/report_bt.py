from __future__ import annotations
from pathlib import Path
import datetime as dt
import duckdb
import pandas as pd

DB = Path("/Users/sultan/Trading/data/duck/qa.duckdb")
RPT = Path("/Users/sultan/Trading/data/checks/reports")

def main() -> None:
    RPT.mkdir(parents=True, exist_ok=True)
    today = dt.datetime.utcnow().strftime("%Y-%m-%d")
    md = RPT / f"bt_report_{today}.md"

    # Abrimos en modo solo-lectura para evitar bloqueos si DBeaver está abierto.
    con = duckdb.connect(str(DB), read_only=True)

    # --- bt.metrics_all (síntesis por símbolo/activo) ---
    try:
        bt = con.execute("""
            SELECT symbol, asset, CAGR, Sharpe, MaxDD, Vol
            FROM bt.metrics_all
            ORDER BY Sharpe DESC, CAGR DESC
        """).fetchdf()
    except Exception:
        bt = pd.DataFrame(columns=["symbol","asset","CAGR","Sharpe","MaxDD","Vol"])

    # Guardamos comparación a CSV (por trazabilidad)
    comp_csv = RPT / f"bt_comp_{today}.csv"
    bt.to_csv(comp_csv, index=False)

    # --- métricas de portafolio (si existen) ---
    try:
        pm = con.execute("SELECT * FROM ml.portfolio_metrics").fetchdf()
    except Exception:
        pm = pd.DataFrame(columns=["CAGR","Sharpe","MaxDD","Vol"])

    con.close()

    # --- Markdown simple ---
    with open(md, "w", encoding="utf-8") as f:
        f.write(f"# Backtesting summary — {today}\n\n")

        f.write("## Portfolio metrics\n\n")
        if pm.empty:
            f.write("_No portfolio metrics found._\n\n")
        else:
            f.write(pm.to_markdown(index=False))
            f.write("\n\n")

        f.write("## Symbols ranking (Sharpe desc)\n\n")
        if bt.empty:
            f.write("_No bt.metrics_all data found._\n\n")
        else:
            top = bt.head(30)
            f.write(top.to_markdown(index=False))
            f.write("\n\n")

        f.write("## Row counts\n\n")
        f.write(f"- bt.metrics_all: {len(bt)} filas\n")
        f.write(f"- portfolio_metrics: {len(pm)} filas\n")

    print(f"Reporte generado:\n- {md}\n- {comp_csv}")

if __name__ == "__main__":
    main()

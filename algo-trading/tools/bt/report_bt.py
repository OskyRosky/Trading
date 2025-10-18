from __future__ import annotations
import datetime as dt
from pathlib import Path
import duckdb, pandas as pd

DB = Path("/Users/sultan/Trading/data/duck/qa.duckdb")
RPT = Path("/Users/sultan/Trading/data/checks/reports")

def main():
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    md = RPT / f"bt_report_{today}.md"
    csv_comp_all = RPT / f"bt_comp_{today}.csv"  # opcional: comparativa agregada si existiera

    con = duckdb.connect(str(DB), read_only=True)

    # ----- Sección 1: métricas de cartera (si existen) -----
    try:
        pm = con.execute("SELECT * FROM ml.portfolio_metrics").fetchdf()
    except Exception:
        pm = pd.DataFrame()

    # ----- Sección 2: métricas backtest (bt.metrics_all) -----
    # vista larga: symbol, asset, CAGR, Sharpe, MaxDD, Vol
    try:
        mt_all = con.execute("""
            SELECT symbol, asset, CAGR, Sharpe, MaxDD, Vol
            FROM bt.metrics_all
            ORDER BY symbol, asset
        """).fetchdf()
    except Exception:
        mt_all = pd.DataFrame()

    # ----- Sección 3: alertas deduplicadas -----
    # UNDER_HODL = HODL supera notoriamente a la estrategia
    # DEEP_DD    = drawdown peor que -60%
    # NEG_SHARPE = Sharpe < 0
    try:
        alerts = con.execute("""
            SELECT symbol, alert, value, benchmark_value, detail
            FROM bt.alerts_dedup
            ORDER BY
              CASE alert
                WHEN 'DEEP_DD' THEN 1
                WHEN 'NEG_SHARPE' THEN 2
                WHEN 'UNDER_HODL' THEN 3
                ELSE 4
              END,
              symbol
        """).fetchdf()
        alerts_count = con.execute("""
            SELECT alert, COUNT(*) AS n
            FROM bt.alerts_dedup
            GROUP BY 1 ORDER BY 2 DESC
        """).fetchdf()
    except Exception:
        alerts = pd.DataFrame()
        alerts_count = pd.DataFrame()

    # ----- Render MD -----
    with open(md, "w", encoding="utf-8") as f:
        f.write(f"# Backtesting Report — {today}\n\n")

        # Cartera
        f.write("## 1) Portfolio (si disponible)\n\n")
        if not pm.empty:
            f.write(pm.to_markdown(index=False))
        else:
            f.write("_Sin tabla ml.portfolio_metrics._")
        f.write("\n\n")

        # Métricas por símbolo/asset
        f.write("## 2) Métricas por símbolo/asset (bt.metrics_all)\n\n")
        if not mt_all.empty:
            f.write(mt_all.to_markdown(index=False))
        else:
            f.write("_Sin métricas en bt.metrics_all._")
        f.write("\n\n")

        # Alertas
        f.write("## 3) Semáforo de alertas (deduplicado)\n\n")
        if not alerts_count.empty:
            f.write("**Resumen por tipo**\n\n")
            f.write(alerts_count.to_markdown(index=False))
            f.write("\n\n**Detalle**\n\n")
            f.write(alerts.to_markdown(index=False))
        else:
            f.write("_Sin alertas._")
        f.write("\n")

    con.close()
    print(f"{md}")

if __name__ == "__main__":
    main()

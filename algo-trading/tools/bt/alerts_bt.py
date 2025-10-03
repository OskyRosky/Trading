from __future__ import annotations
import datetime as dt
from pathlib import Path
import duckdb, pandas as pd

QA_DB = Path("/Users/sultan/Trading/data/duck/qa.duckdb")
RPT   = Path("/Users/sultan/Trading/data/checks/reports")
RPT.mkdir(parents=True, exist_ok=True)

TODAY = dt.datetime.utcnow().strftime("%Y-%m-%d")

def load_metrics(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    q = """
      SELECT symbol, asset, CAGR, Sharpe, MaxDD, Vol
      FROM bt.metrics_all
    """
    return con.execute(q).fetchdf()

def build_alerts(df: pd.DataFrame) -> pd.DataFrame:
    # Tomamos una fila por símbolo para STRAT y otra para HODL
    strat = (df[df["asset"].str.startswith("STRAT_")]
             .set_index("symbol")[["CAGR","Sharpe","MaxDD","Vol"]]
             .rename(columns=lambda c: f"strat_{c.lower()}"))
    hodl  = (df[df["asset"].str.startswith("HODL_")]
             .set_index("symbol")[["CAGR","Sharpe","MaxDD","Vol"]]
             .rename(columns=lambda c: f"hodl_{c.lower()}"))
    j = strat.join(hodl, how="left")

    alerts = []

    for sym, row in j.reset_index().iterrows():
        # Regla 1: Sharpe < 0
        if pd.notna(row["strat_sharpe"]) and row["strat_sharpe"] < 0:
            alerts.append({
                "symbol": row["symbol"],
                "alert": "NEG_SHARPE",
                "value": float(row["strat_sharpe"]),
                "benchmark_value": None,
                "detail": "Sharpe < 0"
            })

        # Regla 2: MaxDD < -60%
        if pd.notna(row["strat_maxdd"]) and row["strat_maxdd"] < -0.60:
            alerts.append({
                "symbol": row["symbol"],
                "alert": "DEEP_DD",
                "value": float(row["strat_maxdd"]),
                "benchmark_value": None,
                "detail": "MaxDD < -60%"
            })

        # Regla 3: HODL mucho mejor que la estrategia (por CAGR)
        if pd.notna(row.get("hodl_cagr")) and pd.notna(row.get("strat_cagr")):
            if row["hodl_cagr"] > row["strat_cagr"] + 0.05:
                alerts.append({
                    "symbol": row["symbol"],
                    "alert": "UNDER_HODL",
                    "value": float(row["strat_cagr"]),
                    "benchmark_value": float(row["hodl_cagr"]),
                    "detail": "HODL CAGR supera STRAT por > 5pp"
                })

    return pd.DataFrame(alerts, columns=["symbol","alert","value","benchmark_value","detail"])

def main():
    con = duckdb.connect(str(QA_DB))
    con.execute("CREATE SCHEMA IF NOT EXISTS bt;")

    metrics = load_metrics(con)
    if metrics.empty:
        print("Sin métricas en bt.metrics_all; no hay alertas.")
        return

    alerts = build_alerts(metrics)
    out_csv = RPT / f"bt_alerts_{TODAY}.csv"
    alerts.to_csv(out_csv, index=False)

    con.execute("CREATE TABLE IF NOT EXISTS bt.alerts(symbol TEXT, alert TEXT, value DOUBLE, benchmark_value DOUBLE, detail TEXT, report_date DATE);")
    con.execute("DELETE FROM bt.alerts;")
    if not alerts.empty:
        alerts["report_date"] = TODAY
        con.register("alert_df", alerts)
        con.execute("INSERT INTO bt.alerts SELECT * FROM alert_df;")
        con.unregister("alert_df")

    con.close()
    print(str(out_csv))

if __name__ == "__main__":
    main()

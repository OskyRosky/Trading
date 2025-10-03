from __future__ import annotations
import duckdb, pathlib, datetime

DB = "/Users/sultan/Trading/data/duck/qa.duckdb"
CSV = "/Users/sultan/Trading/data/checks/reports/backtest_metrics.csv"

def main():
    con = duckdb.connect(DB)
    con.execute("CREATE SCHEMA IF NOT EXISTS bt;")
    con.execute("""
      CREATE TABLE IF NOT EXISTS bt.metrics(
        as_of DATE,
        symbol TEXT,
        CAGR DOUBLE,
        Sharpe DOUBLE,
        MaxDD DOUBLE
      );
    """)
    as_of = datetime.datetime.utcnow().date().isoformat()
    con.execute(f"""
      INSERT INTO bt.metrics
      SELECT DATE '{as_of}' AS as_of, *
      FROM read_csv_auto('{CSV}', header=True);
    """)
    con.close()
    print("Métricas insertadas en qa.duckdb schema bt")
if __name__ == "__main__":
    main()

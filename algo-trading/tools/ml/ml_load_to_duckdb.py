from __future__ import annotations
from pathlib import Path
import duckdb, pandas as pd

DB=Path("/Users/sultan/Trading/data/duck/qa.duckdb")
REP=Path("/Users/sultan/Trading/data/checks/reports")
SIG=Path("/Users/sultan/Trading/data/ml/signals")

con = duckdb.connect(str(DB))
con.execute("CREATE SCHEMA IF NOT EXISTS ml;")

m1 = REP/"ml_metrics_all.csv"
if m1.exists():
    con.execute("CREATE TABLE IF NOT EXISTS ml.metrics AS SELECT * FROM read_csv_auto(?) LIMIT 0;", [str(m1)])
    con.execute("INSERT INTO ml.metrics SELECT * FROM read_csv_auto(?);", [str(m1)])

m2 = REP/"ml_bt_metrics_all.csv"
if m2.exists():
    con.execute("CREATE TABLE IF NOT EXISTS ml.bt_metrics AS SELECT * FROM read_csv_auto(?) LIMIT 0;", [str(m2)])
    con.execute("INSERT INTO ml.bt_metrics SELECT * FROM read_csv_auto(?);", [str(m2)])

from glob import glob
files = sorted(glob(str(SIG/"signals_*.csv")))
if files:
    con.execute("CREATE TABLE IF NOT EXISTS ml.signals AS SELECT * FROM read_csv_auto(?) LIMIT 0;", [files[-1]])
    for f in files:
        con.execute("INSERT INTO ml.signals SELECT * FROM read_csv_auto(?);", [f])

print("Loaded into DuckDB: ml.metrics, ml.bt_metrics, ml.signals")

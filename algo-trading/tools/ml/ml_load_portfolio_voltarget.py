from __future__ import annotations
from pathlib import Path
import duckdb

DB = Path("/Users/sultan/Trading/data/duck/qa.duckdb")
ROOT = Path("/Users/sultan/Trading/data")
EQ = ROOT/"checks"/"reports"/"portfolio_equity_voltarget.csv"
MT = ROOT/"checks"/"reports"/"portfolio_metrics_voltarget.csv"
WT = ROOT/"checks"/"reports"/"portfolio_weights_voltarget.csv"

con = duckdb.connect(str(DB))
con.execute("CREATE SCHEMA IF NOT EXISTS ml;")

if EQ.exists():
    con.execute("CREATE TABLE IF NOT EXISTS ml.portfolio_equity_voltarget AS SELECT * FROM read_csv_auto(?) LIMIT 0;", [str(EQ)])
    con.execute("DELETE FROM ml.portfolio_equity_voltarget;")
    con.execute("INSERT INTO ml.portfolio_equity_voltarget SELECT * FROM read_csv_auto(?);", [str(EQ)])

if MT.exists():
    con.execute("CREATE TABLE IF NOT EXISTS ml.portfolio_metrics_voltarget AS SELECT * FROM read_csv_auto(?) LIMIT 0;", [str(MT)])
    con.execute("DELETE FROM ml.portfolio_metrics_voltarget;")
    con.execute("INSERT INTO ml.portfolio_metrics_voltarget SELECT * FROM read_csv_auto(?);", [str(MT)])

if WT.exists():
    con.execute("CREATE TABLE IF NOT EXISTS ml.portfolio_weights_voltarget AS SELECT * FROM read_csv_auto(?) LIMIT 0;", [str(WT)])
    con.execute("DELETE FROM ml.portfolio_weights_voltarget;")
    con.execute("INSERT INTO ml.portfolio_weights_voltarget SELECT * FROM read_csv_auto(?);", [str(WT)])

print("Loaded voltarget: equity, metrics, weights")

from __future__ import annotations
from pathlib import Path
import duckdb

DB = Path("/Users/sultan/Trading/data/duck/qa.duckdb")
ROOT = Path("/Users/sultan/Trading/data")
EQ = ROOT/"checks"/"reports"/"portfolio_equity.csv"
MT = ROOT/"checks"/"reports"/"portfolio_metrics.csv"
WT = ROOT/"checks"/"reports"/"portfolio_weights.csv"

con = duckdb.connect(str(DB))
con.execute("CREATE SCHEMA IF NOT EXISTS ml;")

if EQ.exists():
    con.execute("CREATE TABLE IF NOT EXISTS ml.portfolio_equity AS SELECT * FROM read_csv_auto(?) LIMIT 0;", [str(EQ)])
    con.execute("DELETE FROM ml.portfolio_equity;")
    con.execute("INSERT INTO ml.portfolio_equity SELECT * FROM read_csv_auto(?);", [str(EQ)])

if MT.exists():
    con.execute("CREATE TABLE IF NOT EXISTS ml.portfolio_metrics AS SELECT * FROM read_csv_auto(?) LIMIT 0;", [str(MT)])
    con.execute("DELETE FROM ml.portfolio_metrics;")
    con.execute("INSERT INTO ml.portfolio_metrics SELECT * FROM read_csv_auto(?);", [str(MT)])

if WT.exists():
    con.execute("CREATE TABLE IF NOT EXISTS ml.portfolio_weights AS SELECT * FROM read_csv_auto(?) LIMIT 0;", [str(WT)])
    con.execute("DELETE FROM ml.portfolio_weights;")
    con.execute("INSERT INTO ml.portfolio_weights SELECT * FROM read_csv_auto(?);", [str(WT)])

print("Loaded: ml.portfolio_equity, ml.portfolio_metrics, ml.portfolio_weights")

from __future__ import annotations
from pathlib import Path
import duckdb

DB = Path("/Users/sultan/Trading/data/duck/qa.duckdb")
ROOT = Path("/Users/sultan/Trading/data")
THR = ROOT/"ml"/"thresholds"/"opt_thresholds.csv"
CMP = ROOT/"checks"/"reports"/"ml_thr_compare.csv"

con = duckdb.connect(str(DB))
con.execute("CREATE SCHEMA IF NOT EXISTS ml;")

if THR.exists():
    con.execute("CREATE TABLE IF NOT EXISTS ml.opt_thresholds AS SELECT * FROM read_csv_auto(?) LIMIT 0;", [str(THR)])
    con.execute("DELETE FROM ml.opt_thresholds;")
    con.execute("INSERT INTO ml.opt_thresholds SELECT * FROM read_csv_auto(?);", [str(THR)])

if CMP.exists():
    con.execute("CREATE TABLE IF NOT EXISTS ml.thr_compare AS SELECT * FROM read_csv_auto(?) LIMIT 0;", [str(CMP)])
    con.execute("DELETE FROM ml.thr_compare;")
    con.execute("INSERT INTO ml.thr_compare SELECT * FROM read_csv_auto(?);", [str(CMP)])

con.execute("""
CREATE OR REPLACE VIEW ml.thr_compare_latest AS
SELECT *
FROM ml.thr_compare
QUALIFY row_number() OVER (PARTITION BY symbol ORDER BY window_days DESC, fee_bps DESC) = 1;
""")

print("Loaded: ml.opt_thresholds, ml.thr_compare; View: ml.thr_compare_latest")

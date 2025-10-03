from __future__ import annotations
from pathlib import Path
import duckdb, glob

DB = Path("/Users/sultan/Trading/data/duck/qa.duckdb")
REP = Path("/Users/sultan/Trading/data/checks/reports")
SIG = Path("/Users/sultan/Trading/data/ml/signals")
PLAN = Path("/Users/sultan/Trading/data/ml/trade_plan")

con = duckdb.connect(str(DB))
con.execute("CREATE SCHEMA IF NOT EXISTS ml;")

p = REP/"ml_metrics_all.csv"
if p.exists():
    con.execute("CREATE TABLE IF NOT EXISTS ml.metrics AS SELECT * FROM read_csv_auto(?) LIMIT 0;", [str(p)])
    con.execute("DELETE FROM ml.metrics;")
    con.execute("INSERT INTO ml.metrics SELECT * FROM read_csv_auto(?);", [str(p)])

p = REP/"ml_bt_metrics_all.csv"
if p.exists():
    con.execute("CREATE TABLE IF NOT EXISTS ml.bt_metrics AS SELECT * FROM read_csv_auto(?) LIMIT 0;", [str(p)])
    con.execute("DELETE FROM ml.bt_metrics;")
    con.execute("INSERT INTO ml.bt_metrics SELECT * FROM read_csv_auto(?);", [str(p)])

p = REP/"ml_thr_sweep.csv"
if p.exists():
    con.execute("CREATE TABLE IF NOT EXISTS ml.thr_sweep AS SELECT * FROM read_csv_auto(?) LIMIT 0;", [str(p)])
    con.execute("DELETE FROM ml.thr_sweep;")
    con.execute("INSERT INTO ml.thr_sweep SELECT * FROM read_csv_auto(?);", [str(p)])

p = REP/"ml_thr_best.csv"
if p.exists():
    con.execute("CREATE TABLE IF NOT EXISTS ml.thr_best AS SELECT * FROM read_csv_auto(?) LIMIT 0;", [str(p)])
    con.execute("DELETE FROM ml.thr_best;")
    con.execute("INSERT INTO ml.thr_best SELECT * FROM read_csv_auto(?);", [str(p)])

fs = sorted(glob.glob(str(SIG/"signals_*.csv")))
if fs:
    con.execute("CREATE TABLE IF NOT EXISTS ml.signals AS SELECT * FROM read_csv_auto(?) LIMIT 0;", [fs[-1]])
    con.execute("DELETE FROM ml.signals;")
    for f in fs:
        con.execute("INSERT INTO ml.signals SELECT * FROM read_csv_auto(?);", [f])

fp = sorted(glob.glob(str(PLAN/"plan_*.csv")))
if fp:
    con.execute("CREATE TABLE IF NOT EXISTS ml.trade_plan AS SELECT * FROM read_csv_auto(?) LIMIT 0;", [fp[-1]])
    con.execute("DELETE FROM ml.trade_plan;")
    for f in fp:
        con.execute("INSERT INTO ml.trade_plan SELECT * FROM read_csv_auto(?);", [f])

con.execute("CREATE OR REPLACE VIEW ml.latest_signals AS SELECT * FROM ml.signals WHERE date = (SELECT MAX(date) FROM ml.signals);")
con.execute("CREATE OR REPLACE VIEW ml.latest_plan AS SELECT * FROM ml.trade_plan WHERE date = (SELECT MAX(date) FROM ml.trade_plan);")
print("Loaded: ml.metrics, ml.bt_metrics, ml.thr_sweep, ml.thr_best, ml.signals, ml.trade_plan; Views: ml.latest_signals, ml.latest_plan")

from __future__ import annotations
from pathlib import Path
import duckdb, pandas as pd

DB  = Path("/Users/sultan/Trading/data/duck/qa.duckdb")
RPT = Path("/Users/sultan/Trading/data/checks/reports")

con = duckdb.connect(str(DB))
con.execute("CREATE SCHEMA IF NOT EXISTS bt;")

p = RPT/"bt_sweep_simple.csv"
if p.exists():
    df = pd.read_csv(p)
    con.execute("CREATE TABLE IF NOT EXISTS bt.metrics_sweep AS SELECT * FROM df LIMIT 0;")
    con.execute("DELETE FROM bt.metrics_sweep;")
    con.execute("INSERT INTO bt.metrics_sweep SELECT * FROM df;")
    print("Loaded bt.metrics_sweep")
else:
    print("bt_sweep_simple.csv not found")

con.close()

from __future__ import annotations
from pathlib import Path
import duckdb, pandas as pd

DB = Path("/Users/sultan/Trading/data/duck/qa.duckdb")
RPT = Path("/Users/sultan/Trading/data/checks/reports")

con = duckdb.connect(str(DB))
con.execute("CREATE SCHEMA IF NOT EXISTS bt;")

for p in sorted(RPT.glob("bt_symbol_*_metrics.csv")):
    df = pd.read_csv(p)
    sym = p.stem.replace("bt_symbol_", "").replace("_metrics", "")
    con.execute(f"CREATE TABLE IF NOT EXISTS bt.metrics_{sym} AS SELECT * FROM df LIMIT 0;")
    con.execute(f"DELETE FROM bt.metrics_{sym};")
    con.execute(f"INSERT INTO bt.metrics_{sym} SELECT * FROM df;")

for p in sorted(RPT.glob("bt_symbol_*.csv")):
    if p.name.endswith("_metrics.csv"):
        continue
    df = pd.read_csv(p)
    if "date" not in df.columns:
        continue
    df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
    df = df.dropna(subset=["date"])
    sym = p.stem.replace("bt_symbol_", "")
    con.execute(f"CREATE TABLE IF NOT EXISTS bt.equity_{sym} AS SELECT * FROM df LIMIT 0;")
    con.execute(f"DELETE FROM bt.equity_{sym};")
    con.execute(f"INSERT INTO bt.equity_{sym} SELECT * FROM df;")

print("Loaded bt.* tables")

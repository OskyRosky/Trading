from __future__ import annotations
from pathlib import Path
import duckdb

DB = Path("/Users/sultan/Trading/data/duck/qa.duckdb")

con = duckdb.connect(str(DB))
con.execute("CREATE SCHEMA IF NOT EXISTS live;")

con.execute("""
CREATE TABLE IF NOT EXISTS live.account (
  as_of DATE,
  equity DOUBLE
);
""")

con.execute("""
CREATE TABLE IF NOT EXISTS live.positions (
  as_of DATE,
  symbol VARCHAR,
  qty DOUBLE,
  mark DOUBLE
);
""")

con.execute("""
CREATE TABLE IF NOT EXISTS live.fills (
  as_of DATE,
  symbol VARCHAR,
  side VARCHAR,
  qty DOUBLE,
  price DOUBLE,
  fee DOUBLE
);
""")

con.execute("""
CREATE TABLE IF NOT EXISTS live.pnl_daily (
  as_of DATE,
  equity_mark DOUBLE,
  fees DOUBLE
);
""")

print("live.* ready")

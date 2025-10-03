from __future__ import annotations
import duckdb, yaml, pathlib, re

DB="/Users/sultan/Trading/data/duck/market.duckdb"
DATA="/Users/sultan/Trading/data/trusted/market=futures/segment=usdtm/contract=perpetual"
CFG="/Users/sultan/Trading/algo-trading/configs/symbols.yml"

def sanitize(name: str) -> str:
    alias = re.sub(r'[^A-Za-z0-9_]', '_', name.lower())
    if re.match(r'^[0-9]', alias):
        alias = "v_" + alias
    return alias

con = duckdb.connect(DB)
con.execute("CREATE SCHEMA IF NOT EXISTS trusted;")
cfg = yaml.safe_load(pathlib.Path(CFG).read_text())

for shown, api in cfg["symbol_map"].items():
    view = f"trusted.{sanitize(shown)}_1d"
    pat = f"{DATA}/symbol={shown}/interval=1d/**/data.parquet"
    sql = f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM read_parquet('{pat}', hive_partitioning=1);"
    con.execute(sql)

con.execute(f"""
  CREATE OR REPLACE VIEW trusted.all_1d AS
  SELECT * FROM read_parquet('{DATA}/symbol=*/interval=1d/**/data.parquet', hive_partitioning=1);
""")
print("Trusted views created in market.duckdb (schema trusted)")

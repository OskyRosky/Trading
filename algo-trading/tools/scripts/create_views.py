from __future__ import annotations
import duckdb, yaml, pathlib, re

DB="/Users/sultan/Trading/data/duck/market.duckdb"
DATA="/Users/sultan/Trading/data/curated/market=futures/segment=usdtm/contract=perpetual"
CFG="configs/symbols.yml"

def safe_view_name(symbol_folder: str) -> str:
    s = symbol_folder.lower().replace('.', '_')
    s = re.sub(r'[^a-z0-9_]', '_', s)
    if s[0].isdigit():
        s = 'v_' + s
    return s

con = duckdb.connect(DB)
con.execute("CREATE SCHEMA IF NOT EXISTS curated;")
cfg = yaml.safe_load(pathlib.Path(CFG).read_text())

for shown, api in cfg["symbol_map"].items():
    view_name = safe_view_name(shown) + "_1d"
    pat = f"{DATA}/symbol={shown}/interval=1d/**/data.parquet"
    sql = f"CREATE OR REPLACE VIEW curated.{view_name} AS SELECT * FROM read_parquet('{pat}', hive_partitioning=1);"
    con.execute(sql)

sql_all = f"CREATE OR REPLACE VIEW curated.all_1d AS SELECT * FROM read_parquet('{DATA}/symbol=*/interval=1d/**/data.parquet', hive_partitioning=1);"
con.execute(sql_all)

print("Views refreshed.")

from __future__ import annotations
from pathlib import Path
import yaml, duckdb, pandas as pd

BASE = Path("/Users/sultan/Trading/algo-trading")
DATA = Path("/Users/sultan/Trading/data")

def load_cfg():
    paths = yaml.safe_load((BASE/"configs"/"data_paths.yml").read_text())
    symbols = yaml.safe_load((BASE/"configs"/"symbols.yml").read_text())
    ml = yaml.safe_load((BASE/"configs"/"ml.yml").read_text())
    return paths, symbols, ml

def read_trusted_symbol(paths: dict, symbol: str) -> pd.DataFrame:
    pat = f"{paths['trusted_root']}/market=futures/segment=usdtm/contract=perpetual/symbol={symbol}/interval=1d/**/data.parquet"
    con = duckdb.connect()
    df = con.execute(f"SELECT * FROM read_parquet('{pat}', hive_partitioning=1) ORDER BY date").fetchdf()
    return df

def ensure_monotonic(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
    return df

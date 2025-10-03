from __future__ import annotations
from pathlib import Path
import argparse
import duckdb, yaml, pandas as pd
from services.features.indicators import basic_features

def _load_cfg():
    base = Path(__file__).resolve().parents[2]
    paths = yaml.safe_load((base/"configs"/"data_paths.yml").read_text())
    symbols = yaml.safe_load((base/"configs"/"symbols.yml").read_text())
    return paths, symbols

def _curated_glob(root: str, symbol: str) -> str:
    return f"{root}/market=futures/segment=usdtm/contract=perpetual/symbol={symbol}/interval=1d/**/data.parquet"

def _trusted_glob(root: str, symbol: str) -> str:
    return f"{root}/market=futures/segment=usdtm/contract=perpetual/symbol={symbol}/interval=1d/**/data.parquet"

def _trusted_root(root: str, symbol: str) -> Path:
    return Path(root)/"market=futures"/"segment=usdtm"/"contract=perpetual"/f"symbol={symbol}"/"interval=1d"

def _write_partitioned(df: pd.DataFrame, dst_root: Path) -> int:
    if df.empty:
        return 0
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    total = 0
    for y in sorted(df["date"].dt.year.unique()):
        dfy = df[df["date"].dt.year == y]
        for m in sorted(dfy["date"].dt.month.unique()):
            part = dfy[dfy["date"].dt.month == m]
            part_dir = dst_root/f"year={y}"/f"month={m:02d}"
            part_dir.mkdir(parents=True, exist_ok=True)
            path = part_dir/"data.parquet"
            if path.exists():
                old = pd.read_parquet(path)
                merged = pd.concat([old, part], ignore_index=True)
                merged = merged.sort_values("date").drop_duplicates(subset=["date"], keep="last")
            else:
                merged = part
            merged.to_parquet(path, index=False)
            total += len(part)
    return total

def _last_trusted_date(paths, symbol) -> pd.Timestamp | None:
    con = duckdb.connect()
    pat = _trusted_glob(paths["trusted_root"], symbol)
    try:
        row = con.execute(f"SELECT MAX(date) AS d FROM read_parquet('{pat}', hive_partitioning=1)").fetchone()
        if row and row[0] is not None:
            return pd.to_datetime(row[0], utc=True)
    except Exception:
        pass
    return None

def build_one(symbol: str, delta: bool=False) -> int:
    paths, _ = _load_cfg()
    con = duckdb.connect()
    con.execute("INSTALL parquet; LOAD parquet;")

    cur_pat = _curated_glob(paths["curated_root"], symbol)
    if delta:
        last = _last_trusted_date(paths, symbol)
        if last is not None:
            # re-calcular con colchón (20 días) para evitar bordes de medias
            q = f"""
              SELECT * FROM read_parquet('{cur_pat}', hive_partitioning=1)
              WHERE date >= TIMESTAMP '{(last.tz_convert(None) if hasattr(last,'tz_convert') else last - pd.Timedelta(0)).strftime("%Y-%m-%d %H:%M:%S")}' - INTERVAL 20 DAY
              ORDER BY date
            """
        else:
            q = f"SELECT * FROM read_parquet('{cur_pat}', hive_partitioning=1) ORDER BY date"
    else:
        q = f"SELECT * FROM read_parquet('{cur_pat}', hive_partitioning=1) ORDER BY date"

    df = con.execute(q).fetchdf()
    if df.empty:
        print(f"[WARN] curated vacío para {symbol}")
        return 0

    feat = basic_features(df)
    dst = _trusted_root(paths["trusted_root"], symbol)
    n = _write_partitioned(feat, dst)
    print(f"[OK] features {'delta' if delta else 'full'}: {symbol} rows={n}")
    return n

def main():
    ap = argparse.ArgumentParser(description="Features 1d → trusted")
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--delta", action="store_true", help="procesa sólo lo nuevo (con colchón)")
    args = ap.parse_args()
    build_one(args.symbol, delta=args.delta)

if __name__ == "__main__":
    main()

from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

def save_checkpoint(path: str, last_close_time_ms: int) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"last_close_time": int(last_close_time_ms)}, f)

def load_checkpoint(path: str) -> int | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        obj = json.loads(p.read_text())
        return int(obj.get("last_close_time"))
    except Exception:
        return None

def upsert_parquet_curated(df: pd.DataFrame, curated_root: str, market:str, segment:str, contract:str, symbol:str, interval:str="1d") -> int:
    if df.empty:
        return 0
    root = Path(curated_root) / f"market={market}" / f"segment={segment}" / f"contract={contract}" / f"symbol={symbol}" / f"interval={interval}"
    written = 0
    for y in sorted(df["date"].dt.year.unique()):
        df_y = df[df["date"].dt.year == y]
        for m in sorted(df_y["date"].dt.month.unique()):
            part = df_y[df_y["date"].dt.month == m].copy()
            part = part.sort_values("date").drop_duplicates(subset=["date"], keep="last")
            part_dir = root / f"year={y}" / f"month={m:02d}"
            part_dir.mkdir(parents=True, exist_ok=True)
            path = part_dir / "data.parquet"
            if path.exists():
                old = pd.read_parquet(path)
                merged = pd.concat([old, part], ignore_index=True)
                merged = merged.sort_values("date").drop_duplicates(subset=["date"], keep="last")
            else:
                merged = part
            merged.to_parquet(path, index=False)
            written += len(part)
    return written

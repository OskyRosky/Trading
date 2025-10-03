from __future__ import annotations
from pathlib import Path
import duckdb, pandas as pd
import re

DB = Path("/Users/sultan/Trading/data/duck/qa.duckdb")
RPT = Path("/Users/sultan/Trading/data/checks/reports")

def sanitize(sym: str) -> str:
    s = re.sub(r'[^A-Za-z0-9_]', '_', sym)
    if re.match(r'^[0-9]', s):
        s = "_" + s
    return s

def load_all_into_duck():
    con = duckdb.connect(str(DB))
    con.execute("CREATE SCHEMA IF NOT EXISTS bt;")

    # --- METRICS: tablas por símbolo ---
    items = []  # [(safe, orig)]
    for p in sorted(RPT.glob("bt_symbol_*_metrics.csv")):
        df = pd.read_csv(p)
        orig = p.stem.replace("bt_symbol_", "").replace("_metrics", "")
        safe = sanitize(orig)

        con.execute(f"CREATE TABLE IF NOT EXISTS bt.metrics_{safe} AS SELECT * FROM df LIMIT 0;")
        con.execute(f"DELETE FROM bt.metrics_{safe};")
        con.execute(f"INSERT INTO bt.metrics_{safe} SELECT * FROM df;")
        items.append((safe, orig))

    # --- Vista unificada de metrics (sin joins, con literal del símbolo) ---
    if items:
        unions = []
        for safe, orig in items:
            unions.append(
                f"SELECT '{orig}' AS symbol, m.* FROM bt.metrics_{safe} m"
            )
        union_sql = "\nUNION ALL\n".join(unions)
        con.execute("DROP VIEW IF EXISTS bt.metrics_all;")
        con.execute(f"CREATE VIEW bt.metrics_all AS {union_sql};")

    # --- EQUITY: DROP + CREATE para forzar esquema (date,equity,ret) ---
    for p in sorted(RPT.glob("bt_symbol_*.csv")):
        if p.name.endswith("_metrics.csv"):
            continue
        df = pd.read_csv(p)
        if "date" not in df.columns:
            continue

        df["date"] = pd.to_datetime(df["date"], utc=True, errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

        cols = df.columns.tolist()
        if "equity" in cols and "ret" not in cols:
            eq = df["equity"].astype(float)
            df["ret"] = eq.pct_change().fillna(0.0)
        elif "ret" in cols and "equity" not in cols:
            ret = df["ret"].astype(float).fillna(0.0)
            df["equity"] = (1.0 * (1.0 + ret)).cumprod()

        keep = [c for c in ["date","equity","ret"] if c in df.columns]
        if set(keep) != {"date","equity","ret"}:
            continue  # si no logro ambas, lo salto

        df_out = df[["date","equity","ret"]].copy()

        orig = p.stem.replace("bt_symbol_", "")
        safe = sanitize(orig)
        con.execute(f"DROP TABLE IF EXISTS bt.equity_{safe};")
        con.execute(f"CREATE TABLE bt.equity_{safe} AS SELECT * FROM df_out;")

    print("Loaded bt.* tables and created bt.metrics_all")
    con.close()

if __name__ == "__main__":
    load_all_into_duck()

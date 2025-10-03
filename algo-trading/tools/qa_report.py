from __future__ import annotations
import duckdb, pathlib
from datetime import datetime, UTC, timedelta

DATA_ROOT = "/Users/sultan/Trading/data"
PARQUET_GLOB = DATA_ROOT + "/curated/market=futures/segment=usdtm/contract=perpetual/symbol=*/interval=1d/**/data.parquet"
OUT_DIR = pathlib.Path(DATA_ROOT) / "checks" / "reports"

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).date().isoformat()
    csv_summary = OUT_DIR / f"daily_qa_summary_{ts}.csv"
    csv_gaps    = OUT_DIR / f"daily_qa_gaps_{ts}.csv"
    csv_dups    = OUT_DIR / f"daily_qa_dups_{ts}.csv"
    csv_missing = OUT_DIR / f"daily_qa_missing_yday_{ts}.csv"

    con = duckdb.connect()
    con.execute("INSTALL parquet; LOAD parquet;")

    con.execute(f"""
      CREATE OR REPLACE TEMP VIEW v_all AS
      SELECT
        symbol,
        date,
        date::DATE AS d
      FROM read_parquet('{PARQUET_GLOB}', hive_partitioning=1);
    """)

    summary = con.execute("""
      SELECT symbol,
             COUNT(*) AS n,
             MIN(date) AS min_d,
             MAX(date) AS max_d
      FROM v_all
      GROUP BY 1
      ORDER BY 1
    """).fetchdf()
    summary.to_csv(csv_summary, index=False)

    gaps = con.execute("""
      WITH span AS (
        SELECT symbol, MIN(d) AS min_d, MAX(d) AS max_d
        FROM v_all GROUP BY symbol
      ),
      cal AS (
        SELECT
          s.symbol,
          (s.min_d + CAST(i AS INTEGER))::DATE AS d
        FROM span s,
             range(0, datediff('day', s.min_d, s.max_d) + 1) AS r(i)
      )
      SELECT cal.symbol, cal.d
      FROM cal
      LEFT JOIN v_all b
        ON cal.symbol = b.symbol AND cal.d = b.d
      WHERE b.d IS NULL
      ORDER BY cal.symbol, cal.d
    """).fetchdf()
    gaps.to_csv(csv_gaps, index=False)

    dups = con.execute("""
      SELECT symbol, d, COUNT(*) AS c
      FROM v_all
      GROUP BY 1,2
      HAVING c > 1
      ORDER BY symbol, d
    """).fetchdf()
    dups.to_csv(csv_dups, index=False)

    yday = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
    missing_yday = con.execute(f"""
      WITH have AS (
        SELECT DISTINCT symbol FROM v_all WHERE d = DATE '{yday}'
      ),
      allsyms AS (
        SELECT DISTINCT symbol FROM v_all
      )
      SELECT a.symbol
      FROM allsyms a
      LEFT JOIN have h USING(symbol)
      WHERE h.symbol IS NULL
      ORDER BY a.symbol
    """).fetchdf()
    missing_yday.to_csv(csv_missing, index=False)

    print("Reportes CSV escritos:")
    print(f"- {csv_summary}")
    print(f"- {csv_gaps}")
    print(f"- {csv_dups}")
    print(f"- {csv_missing}")

if __name__ == "__main__":
    main()

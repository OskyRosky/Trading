from __future__ import annotations
import duckdb, pathlib, re
from datetime import datetime, UTC

DATA_ROOT = pathlib.Path("/Users/sultan/Trading/data")
REPORTS = DATA_ROOT / "checks" / "reports"
DB = "/Users/sultan/Trading/data/duck/qa.duckdb"

def latest_for(prefix: str) -> pathlib.Path | None:
    candidates = sorted(REPORTS.glob(f"{prefix}_*.csv"))
    return candidates[-1] if candidates else None

def date_from_name(p: pathlib.Path) -> str:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", p.name)
    if not m:
        return datetime.now(UTC).date().isoformat()
    return m.group(1)

def main():
    con = duckdb.connect(DB)
    con.execute("CREATE SCHEMA IF NOT EXISTS qa;")
    con.execute("SET schema 'qa';")

    p_sum = latest_for("daily_qa_summary")
    if p_sum:
        rep_date = date_from_name(p_sum)
        con.execute("""
          CREATE TABLE IF NOT EXISTS summary(
            report_date DATE,
            symbol TEXT,
            n BIGINT,
            min_d TIMESTAMP,
            max_d TIMESTAMP
          );
        """)
        con.execute(f"""
          INSERT INTO summary
          SELECT DATE '{rep_date}' AS report_date, *
          FROM read_csv_auto('{p_sum}', HEADER=TRUE);
        """)

    p_gaps = latest_for("daily_qa_gaps")
    if p_gaps:
        rep_date = date_from_name(p_gaps)
        con.execute("""
          CREATE TABLE IF NOT EXISTS gaps(
            report_date DATE,
            symbol TEXT,
            d DATE
          );
        """)
        con.execute(f"""
          INSERT INTO gaps
          SELECT DATE '{rep_date}' AS report_date, *
          FROM read_csv_auto('{p_gaps}', HEADER=TRUE);
        """)

    p_dups = latest_for("daily_qa_dups")
    if p_dups:
        rep_date = date_from_name(p_dups)
        con.execute("""
          CREATE TABLE IF NOT EXISTS dups(
            report_date DATE,
            symbol TEXT,
            d DATE,
            c BIGINT
          );
        """)
        con.execute(f"""
          INSERT INTO dups
          SELECT DATE '{rep_date}' AS report_date, *
          FROM read_csv_auto('{p_dups}', HEADER=TRUE);
        """)

    p_miss = latest_for("daily_qa_missing_yday")
    if p_miss:
        rep_date = date_from_name(p_miss)
        con.execute("""
          CREATE TABLE IF NOT EXISTS missing_yday(
            report_date DATE,
            symbol TEXT
          );
        """)
        con.execute(f"""
          INSERT INTO missing_yday
          SELECT DATE '{rep_date}' AS report_date, *
          FROM read_csv_auto('{p_miss}', HEADER=TRUE);
        """)

    con.execute("""
      CREATE OR REPLACE VIEW alerts AS
      WITH a AS (
        SELECT report_date, 'gaps' AS alert, symbol, COUNT(*) AS n
        FROM gaps GROUP BY 1,2,3
      ),
      b AS (
        SELECT report_date, 'dups' AS alert, symbol, COUNT(*) AS n
        FROM dups GROUP BY 1,2,3
      ),
      c AS (
        SELECT report_date, 'missing_yday' AS alert, symbol, 1 AS n
        FROM missing_yday
      )
      SELECT * FROM a
      UNION ALL
      SELECT * FROM b
      UNION ALL
      SELECT * FROM c
      ORDER BY report_date DESC, alert, symbol;
    """)

    con.execute("""
      CREATE TABLE IF NOT EXISTS daily_status(
        report_date DATE PRIMARY KEY,
        total_alerts BIGINT,
        gaps BIGINT,
        dups BIGINT,
        missing_yday BIGINT
      );
    """)

    con.execute("""
      INSERT OR REPLACE INTO daily_status
      SELECT rd.rd AS report_date,
             COALESCE(c.total_alerts, 0) AS total_alerts,
             COALESCE(c.gaps, 0) AS gaps,
             COALESCE(c.dups, 0) AS dups,
             COALESCE(c.missing_yday, 0) AS missing_yday
      FROM (SELECT MAX(report_date) AS rd FROM summary) rd
      LEFT JOIN (
        SELECT report_date,
               SUM(n) AS total_alerts,
               SUM(CASE WHEN alert='gaps' THEN n ELSE 0 END) AS gaps,
               SUM(CASE WHEN alert='dups' THEN n ELSE 0 END) AS dups,
               SUM(CASE WHEN alert='missing_yday' THEN n ELSE 0 END) AS missing_yday
        FROM alerts
        GROUP BY 1
      ) c
      ON c.report_date = rd.rd;
    """)

    con.close()
    print("QA consolidado en qa.duckdb (schema qa) con daily_status")

if __name__ == "__main__":
    main()

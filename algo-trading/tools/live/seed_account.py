from __future__ import annotations
from pathlib import Path
import datetime as dt
import duckdb

DB = Path("/Users/sultan/Trading/data/duck/qa.duckdb")
INIT_EQUITY = 10000.0

def main():
    con = duckdb.connect(str(DB))
    con.execute("CREATE SCHEMA IF NOT EXISTS live;")
    con.execute("CREATE TABLE IF NOT EXISTS live.account (as_of DATE, equity DOUBLE);")
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    con.execute("DELETE FROM live.account WHERE as_of = ?", [today])
    n_total = con.execute("SELECT COUNT(*) FROM live.account").fetchone()[0]
    if n_total == 0:
        con.execute("INSERT INTO live.account VALUES (?, ?)", [today, INIT_EQUITY])
        print(f"Seeded live.account with equity={INIT_EQUITY} at {today}")
    else:
        last_equity = con.execute("SELECT equity FROM live.account ORDER BY as_of DESC LIMIT 1").fetchone()[0]
        con.execute("INSERT INTO live.account VALUES (?, ?)", [today, float(last_equity)])
        print(f"Inserted today's equity={last_equity} at {today}")
    con.close()

if __name__ == "__main__":
    main()

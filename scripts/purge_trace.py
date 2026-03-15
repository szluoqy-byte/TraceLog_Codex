from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path


def default_db_path() -> Path:
    here = Path(__file__).resolve()
    repo = here.parents[1]
    return repo / "backend" / "data" / "tracelog.db"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/purge_trace.py <trace_id>", file=sys.stderr)
        return 2

    trace_id = sys.argv[1]
    db_path = Path(os.getenv("TRACELOG_DB_PATH", str(default_db_path())))
    if not db_path.exists():
        print(f"DB not found: {db_path}", file=sys.stderr)
        return 1

    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        # SQLModel default table names are the lower-cased class names.
        cur.execute("DELETE FROM spanevent WHERE trace_id = ?", (trace_id,))
        cur.execute("DELETE FROM span WHERE trace_id = ?", (trace_id,))
        cur.execute("DELETE FROM trace WHERE trace_id = ?", (trace_id,))
        con.commit()
        print(f"Purged trace_id={trace_id}")
    finally:
        con.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


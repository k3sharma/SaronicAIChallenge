"""
Whereas the view_logs.py file is used when a human wants to look at the logs so far, 
audit_log.py is used to read/write to the database.
It's used by two different files: server.py (record_access) and view_logs.py (fetch_recent).
While the server.py file is running, it needs write access to the database and you need a way to read that data without 
starting the server over again.
Keeping audit_log.py as a separate file ensures nothing is out of sync and no issues with reading/writing from the database

SQLite will be used as a real, structured, queryable database.

gateway_audit.db will be gitignored because it will be produced automatically by the program when ran
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# Path is computed relative to this file's location, not the current working directory
# This means the database always ends up in the same place regardless of where you run `python src/client.py` from
DB_PATH = Path(__file__).parent / "gateway_audit.db"

# Creates the audit log table if it doesn't already exist
def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS access_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            identity TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            tool_args TEXT,
            verdict TEXT NOT NULL,
            detail TEXT
        )
    """)
    conn.commit()
    conn.close()

# Writes one row per tool-call attempt (allowed or denied) every time
# Parameters mirror exactly what the gateway already knows at the point of decision (see server.py)
# This function doesn't compute anything new, it just persists what the gateway already decided
def record_access(
    identity: str,
    tool_name: str,
    tool_args: dict,
    allowed: bool,
    detail: str = "",
) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO access_log (timestamp, identity, tool_name, tool_args, verdict, detail)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            identity,
            tool_name,
            str(tool_args),
            "ALLOWED" if allowed else "DENIED",
            detail,
        ),
    )
    conn.commit()
    conn.close()

# Returns the most recent N rows, newest first.
def fetch_recent(limit: int = 20) -> list[tuple]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT timestamp, identity, tool_name, tool_args, verdict, detail "
        "FROM access_log ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return rows
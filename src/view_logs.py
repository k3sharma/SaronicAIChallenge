"""
A small script for checking the audit trail
Run this any time after using the gateway to see what's actually been recorded
Not part of the agentic loop, just used to view logs
"""
import audit_log
from datetime import datetime
from zoneinfo import ZoneInfo

rows = audit_log.fetch_recent(limit=20)

if not rows:
    print("No audit log entries yet -- run src/client.py first.")
else:
    print(f"{'TIMESTAMP':<28} {'IDENTITY':<10} {'TOOL':<15} {'VERDICT':<8} DETAIL")
    print("-" * 90)
    for timestamp, identity, tool_name, tool_args, verdict, detail in rows:
        utc_dt = datetime.fromisoformat(timestamp)      # Use EST
        local_dt = utc_dt.astimezone(ZoneInfo("America/New_York"))

        formatted_time = local_dt.strftime("%Y-%m-%d %I:%M:%S %p %Z")

        print(f"{formatted_time:<28} " f"{identity:<10} " f"{tool_name:<15} " f"{verdict:<8} " f"{detail}")
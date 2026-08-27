"""
A small script for checking the audit trail
Run this any time after using the gateway to see what's actually been recorded
Not part of the agentic loop, just used to view logs
"""
import audit_log

rows = audit_log.fetch_recent(limit=20)

if not rows:
    print("No audit log entries yet -- run src/client.py first.")
else:
    print(f"{'TIMESTAMP':<28} {'IDENTITY':<10} {'TOOL':<15} {'VERDICT':<8} DETAIL")
    print("-" * 90)
    for timestamp, identity, tool_name, tool_args, verdict, detail in rows:
        print(f"{timestamp:<28} {identity:<10} {tool_name:<15} {verdict:<8} {detail}")
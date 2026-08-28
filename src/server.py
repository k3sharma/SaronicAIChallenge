""" 
This file is building an MCP server that exposes the get_customer tool to any MCP-compatible AI client. 
It acts as the trust boundary for AI tool usage. Tool authorization, audit logging, and data protection controls are enforced
server-side so that every MCP client is subject to the same security policies.
Each tool call now passes through a gateway check first, enforced within the MCP server itself. This means it applies to any client that connects here
"""

import os
import sys
from mcp.server.fastmcp import FastMCP      # FastMCP is a framework used for building MCP applications
import audit_log
import dlp

mcp = FastMCP("SaronicChallengeGateway")    # Instantiate an MCP server called SaronicChallengeGateway

audit_log.init_db()         # Initialize the log table at the start

# Example database with key value pairs
FAKE_CUSTOMER_DATABASE = {
    "cust_001": {"name": "Alice Chen", "plan": "Enterprise", "status": "active", "ssn": "123-45-6789", "email": "alice.chen@example.com", "internal_notes": "API key on file: sk-ant-fakeKeyForTesting1234567890"},
    "cust_002": {"name": "Marcus Webb", "plan": "Starter", "status": "past_due", "ssn": "987-65-4321", "email": "marcus.webb@example.com"},
}

CURRENT_IDENTITY = os.environ.get("AGENT_IDENTITY", "guest")    # Default to the least-privileged role as the identity

# This print statement will confirm what identity the server process received 
# Write to stderr for the purposes of debugging and errors
print(f"[SERVER STARTUP] AGENT_IDENTITY resolved to: '{CURRENT_IDENTITY}'", file=sys.stderr)

# Defines who can call what
ALLOWED_TOOLS = {
    "employee": ["get_customer"],
    "guest": [],
}

# This function keeps the permission check in 1 place (instead of looping it over and over within each tool function)
def is_allowed(identity: str, tool_name: str) -> bool:
    allowed_for_this_identity = ALLOWED_TOOLS.get(identity, [])
    return tool_name in allowed_for_this_identity
 
# Simple logging function 
def log_access_attempt(identity: str, tool_name: str, tool_args: dict, allowed: bool, detail: str="") -> None:
    verdict = "ALLOWED" if allowed else "DENIED"
    print(f"[GATEWAY] {verdict}: identity='{identity}' tool='{tool_name}'", file=sys.stderr)
    
    # Now, persist a row to the audit database
    # Print will show the event once, but this version of the same event will survive
    audit_log.record_access(identity, tool_name, tool_args, allowed, detail)

# Use a decorator so that FastMCP registers it as a tool, thus, clients can discover get_customer and call it
@mcp.tool()
def get_customer(customer_id: str) -> dict:
    # Look up a customer's account information (name, plan tier, and account status) using their unique customer ID
    
    allowed = is_allowed(CURRENT_IDENTITY, "get_customer")      # This is where the gateway check occurs
    log_access_attempt(
            CURRENT_IDENTITY,
            "get_customer",
            {"customer_id": customer_id},       # Which customer was looked up
            allowed,
            detail="" if allowed else "not in ALLOWED_TOOLS for this identity",     # For humans
        )    
    # If the check fails, immediately return an access denied message
    if not allowed:
        return {
            "error": (
                f"Access denied: identity '{CURRENT_IDENTITY}' is not "
                f"permitted to use the 'get_customer' tool."
            )
        }
    
    if customer_id not in FAKE_CUSTOMER_DATABASE:
        return {"error": f"No customer found with id '{customer_id}'"}
    
    raw_result = FAKE_CUSTOMER_DATABASE[customer_id]
 
    # raw_result has the real SSN so use redact_sensitive_data to redact it
    # The real SSN doesn't leave the function
    redacted_result = dlp.redact_sensitive_data(raw_result)
 
    # Now, log which categories were activated (SSN, email, etc.)
    categories = dlp.find_sensitive_categories(raw_result)
    if categories:
        print(f"[DLP] Redacted {sorted(categories)} in response for '{customer_id}'", file=sys.stderr)
 
    return redacted_result

# Start the server, listen to the client
if __name__ == "__main__":
    mcp.run()
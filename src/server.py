""" 
This file is building an MCP server that exposes the get_customer tool to any MCP-compatible AI client. 
It acts as the trust boundary for AI tool usage. Tool authorization, audit logging, and data protection controls are enforced
server-side so that every MCP client is subject to the same security policies.
Each tool call now passes through a gateway check first, enforced within the MCP server itself. This means it applies to any client that connects here
"""

import os
import sys
from mcp.server.fastmcp import FastMCP      # FastMCP is a framework used for building MCP applications

mcp = FastMCP("SaronicChallengeGateway")    # Instantiate an MCP server called SaronicChallengeGateway

# Example database with key value pairs
FAKE_CUSTOMER_DATABASE = {
    "cust_001": {"name": "Alice Chen", "plan": "Enterprise", "status": "active"},
    "cust_002": {"name": "Marcus Webb", "plan": "Starter", "status": "past_due"},
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
def log_access_attempt(identity: str, tool_name: str, allowed: bool) -> None:
    verdict = "ALLOWED" if allowed else "DENIED"
    print(f"[GATEWAY] {verdict}: identity='{identity}' tool='{tool_name}'", file=sys.stderr)
 

# Use a decorator so that FastMCP registers it as a tool, thus, clients can discover get_customer and call it
@mcp.tool()
def get_customer(customer_id: str) -> dict:
    # Look up a customer's account information (name, plan tier, and account status) using their unique customer ID
    
    allowed = is_allowed(CURRENT_IDENTITY, "get_customer")      # This is where the gateway check occurs
    log_access_attempt(CURRENT_IDENTITY, "get_customer", allowed)
    
    # If the check fails, immediately return an access denied message
    if not allowed:
        return {
            "error": (
                f"Access denied: identity '{CURRENT_IDENTITY}' is not "
                f"permitted to use the 'get_customer' tool."
            )
        }
    
    if customer_id in FAKE_CUSTOMER_DATABASE:
        return FAKE_CUSTOMER_DATABASE[customer_id]
    return {"error": f"No customer found with id '{customer_id}'"}

# Start the server, listen to the client
if __name__ == "__main__":
    mcp.run()
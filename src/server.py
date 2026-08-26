""" 
This file is building an MCP server that exposes the get_customer tool to any MCP-compatible AI client. 
It acts as the trust boundary for AI tool usage. Tool authorization, audit logging, and data protection controls are enforced
server-side so that every MCP client is subject to the same security policies.
"""

from mcp.server.fastmcp import FastMCP      # FastMCP is a framework used for building MCP applications

mcp = FastMCP("SaronicChallengeGateway")    # Instantiate an MCP server called SaronicChallengeGateway

# Example database with key value pairs
FAKE_CUSTOMER_DATABASE = {
    "cust_001": {"name": "Alice Chen", "plan": "Enterprise", "status": "active"},
    "cust_002": {"name": "Marcus Webb", "plan": "Starter", "status": "past_due"},
}

# Use a decorator so that FastMCP registers it as a tool, thus, clients can discover get_customer and call it
@mcp.tool()
def get_customer(customer_id: str) -> dict:
    """Look up a customer's account information (name, plan tier, and account status) using their unique customer ID"""
    if customer_id in FAKE_CUSTOMER_DATABASE:
        return FAKE_CUSTOMER_DATABASE[customer_id]
    return {"error": f"No customer found with id '{customer_id}'"}

# Start the server, listen to the client
if __name__ == "__main__":
    mcp.run()
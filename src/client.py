"""
Claude client for the MCP security gateway. 
This file discovers tools exposed by the MCP server, provides them to Claude, executes tool requests through MCP, and
returns tool results back to the model.
"""

import os
from dotenv import load_dotenv
from anthropic import Anthropic

from mcp import ClientSession, StdioServerParameters        # Import MCP client components
from mcp.client.stdio import stdio_client       # Import a helper for launching an MCP server through stdin/stdout

import anyio        # Allows asynchronous code to run smoothly

load_dotenv()
claude = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


# Describes that the client is telling the library to launch the MCP server
server_params = StdioServerParameters(
    command="python",
    args=["src/server.py"],
)

# This function is used to convert MCP tool descriptions to Claude tool descriptions, due to formatting reasons
def mcp_tools_to_claude_format(mcp_tools) -> list[dict]:
    claude_tools = []
    for tool in mcp_tools:  # Loop through each tool
        claude_tools.append({   # Add the key value pairs to the list
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": tool.inputSchema,
        })
    return claude_tools

# Use an async function when communicating with servers
async def main():
    # Launches the server subprocess (python src/server.py) and returns 2 communication pipes (stdin/stdout)
    async with stdio_client(server_params) as (read_stream, write_stream):  
        async with ClientSession(read_stream, write_stream) as session:     # Create an MCP handshake
            await session.initialize()
            
            tools_response = await session.list_tools()            # Ask the server what tools it has
            claude_tools = mcp_tools_to_claude_format(tools_response.tools)     # Converts MCP format to Claude format

            print(f"Discovered tools from server: {[t['name'] for t in claude_tools]}")     # Print the tool names

            # Claude conversation starts
            messages = [
                {
                    "role": "user",
                    "content": "What plan is customer cust_002 on, and are they in good standing?",
                }
            ]

            # API request and choose Claude's model
            response = claude.messages.create(
                model="claude-sonnet-5",
                max_tokens=1024,
                tools=claude_tools,
                messages=messages,
            )

            # Claude response types
            if response.stop_reason == "tool_use":
                for block in response.content:
                    if block.type == "tool_use":        # Process the tool request
                        print(f"\nClaude wants to call: {block.name}({block.input})")   
                        
                        # Send a request across the MCP server which executes the tool. Server receives get_customer, and returns it
                        tool_result = await session.call_tool(
                            block.name, arguments=block.input
                        )

                        # MCP tool results come back as a list of content blocks. Extract the text to hand back to Claude
                        result_text = tool_result.content[0].text

                        messages.append({"role": "assistant", "content": response.content})
                        messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": result_text,
                                }
                            ],
                        })

                # Claude can generate a final answer now since it has the user prompt, tool call, and tool result
                final_response = claude.messages.create(
                    model="claude-sonnet-5",
                    max_tokens=1024,
                    tools=claude_tools,
                    messages=messages,
                )
                # Print
                print(f"\nFinal answer:\n{final_response.content[0].text}")
            else:
                print(f"\nFinal answer:\n{response.content[0].text}")


if __name__ == "__main__":
    anyio.run(main)
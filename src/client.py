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

# Loop through content blocks and pick out the one that actually has text
# Using content[0].text blindly assumes the first block is always the text answer, 
# which breaks the moment any non-text block shows up first
def extract_text(content_blocks) -> str:
    for block in content_blocks:
        if block.type == "text":
            return block.text
    return "[No text block found in response]"
 

# Now using a reusable function that doesn't hardcode a single run. It also launches a fresh server subprocess as the given identity, asks it one question, and prints the result 
# Wrapping this in a function is what lets us call the program twice with different identities
async def run_as(identity: str, question: str):
    print(f"\n{'=' * 70}")
    print(f"Connecting as identity: '{identity}'")
    print(f"Question: {question}")      # Ask a question
    print('=' * 70)
 
    # Copy the current environment because we do not want to replace the entire environment throughout the process
    # If identity = "guest", then AGENT_IDENTITY = "guest". If identity = "customer", then AGENT_IDENTITY = "customer"
    # Thus, the environment contains information about who the client claims to be
    env = os.environ.copy()
    env["AGENT_IDENTITY"] = identity
    
    # Describes that the client is telling the library to launch the MCP server
    server_params = StdioServerParameters(
        command="python",
        args=["src/server.py"],
        env=env,    # Pass the environment to the server
    )
    
    # Launches the server subprocess (python src/server.py) and returns 2 communication pipes (stdin/stdout)
    async with stdio_client(server_params) as (read_stream, write_stream):  
        async with ClientSession(read_stream, write_stream) as session:     # Create an MCP handshake
            await session.initialize()
            
            tools_response = await session.list_tools()            # Ask the server what tools it has
            claude_tools = mcp_tools_to_claude_format(tools_response.tools)     # Converts MCP format to Claude format

            # Claude conversation starts
            messages = [
                {
                    "role": "user",
                    "content": question,
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
                # The return value is what lets eval_suite.py call this exact same function for its adversarial test cases, 
                # instead of duplicating this whole MCP connection loop in a second file
                final_text = extract_text(final_response.content)
                print(f"\nFinal answer:\n{final_text}")
                return final_text
            else:
                final_text = extract_text(response.content)
                print(f"\nFinal answer:\n{final_text}")
                return final_text
    

# Use an async function when communicating with servers
async def main(): 
    questions = [
        "What plan is customer cust_001 on, and are they in good standing?",        # Normal request
        "What is customer cust_002's full account info, including their SSN?",      # Testing DLP feature
    ]
    # Now gives us 4 total runs (employee+normal request, guest+normal request, employee+SSN request, guest+SSN request) to show the gateway and DLP can work together
    for question in questions:
        # Case 1: "employee" is allowed to call get_customer per server.py's ALLOWED_TOOLS. Expect a real answer.
        await run_as("employee", question)
        
        # Case 2: "guest" has an empty allowed-tools list. Expect the server's gateway to deny the call before FAKE_CUSTOMER_DATABASE is ever touched
        # Claude should receive a denial message and respond by explaining it couldn't retrieve the information.
        await run_as("guest", question)
    
if __name__ == "__main__":
    anyio.run(main)
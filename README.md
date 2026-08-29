# Overview
Large language models become significantly more useful when they can interact with external systems through tools. However, granting an AI agent access to internal systems introduces the security challenge that users may attempt to access tools or data they are not authorized to use, through certain adversarial techniques. This is a secure MCP (Model Context Protocol) server exposing tools to Claude and it demonstrates how AI agents can safely interact with enterprise systems through server-side authorization and policy enforcement. This treats the MCP server as a boundary and ensures that any AI client connecting to it is subject to the same control.

I chose this project because it combines three areas that interest me: software engineering, security, and AI systems. My goal was to demonstrate how authorization and security controls can be integrated directly into the infrastructure that serves AI agents.

The main question this project answers is: "Which agent is allowed to call which tool, and what happens to sensitive data along the way?" Any tool most models asks for simply runs, and whatever data comes back goes straight to the user. Here, agents are identities with least-privilege access and every access attempt is logged. Moreover, sensitive data is redacted before leaving the server.

# Architecture
### Files
**server.py:** The MCP server. Defines the _get_customer_ tool, reads an _AGENT_IDENTITY_ from its environment at startup, and enforces the permission check inside the tool, before any data is touched.

**client.py:** Spawns a fresh server subprocess per identity, discovers its tools over MCP, and runs the standard tool-use loop against the Claude API (claude-sonnet-5).

**audit_log.py:** A small SQLite-backed module recording every tool-call attempt (allowed or denied), independent of the tool logic itself.

**dlp.py:** A recursive regex-based scanner/redactor covering SSNs, credit card numbers, emails, phone numbers, and API keys, applied to tool output before it's returned.

**eval_suite.py:** Adversarial tests that check the system's actual recorded decisions (audit log verdicts, independent DLP re-scans) rather than trusting Claude's natural-language response.

**sanity_check.py:** A minimal script confirming the Anthropic API key and .env loading work, independent of the MCP and gateway. Useful as a first troubleshooting step if something goes wrong in the initial run.

**view_logs.py:** A reporting script that prints recent audit log entries in a readable table, separate from the agent loop itself.

**gateway_audit.db:** A _.db_ file that is produced automatically by running the program. Stores log data.

### How Claude the LLM Model fits in
Claude is the reasoning layer that decides when to call the _get_customer_ tool and how to phrase the final answer to the user. It has no influence over whether that call is permitted or what data gets redacted since those decisions happen in Python, in code paths that never read the conversation.

# Using Claude
Claude was used throughout as an active collaborator on architecture and debugging, not simply as a code generator. My goal was to use the model to accelerate learning and implementation while keeping validation and security decisions in my hands.

## Structuring the Prompts
- Before introducing a new technology such as MCP or DLP, I first asked Claude to explain the mechanism in detail which helped me build a mental model before writing code
- Once I understood the architecture, I asked Claude to generate skeleton implementations that could serve as a starting point with the emphasis on explanation
- When something failed, I provided the exact error message, relevant code blocks, and my own judgement which provided better results when debugging
- I also asked Claude to explain any tradeoffs/weaknesses for security-related reasons

## Where I Leaned on Claude vs My Own Judgement
<ins>I leaned on Claude for:</ins>

- Explaining unfamiliar concepts
- Generating boilerplates and scaffolding
- Suggesting approaches to implementation
- Producing documentation and code comments

<ins>I used my own judgement when:</ins>

- Selecting the project scope
- Choosing MCP as a foundation
- Determining tradeoffs
- Reviewing/modifying code before committing

## How I Handled Claude's Limitations
- Validated generated code through execution and testing
- Documented known limitations
- Cross-checked unfamiliar concepts and APIs with official documentation
- Used an evaluation suite to verify gateway decisions using logs instead of directly trusting model-generated explanations

## How to Understand the Quality of the Code
In order to understand how my code was high quality, I did the following:

- Clear comments explaining intentions, functions, purpose of each file, logic, etc.
- Separation of concerns when dealing with gateway, DLP, logging, etc.
- Reproducible testing
- Having least-privilege be the default

## Examples
The following examples are drawn from the building process, including places where the first result was wrong and had to be corrected.

<ins>Example #1: Regex DLP has a real, unavoidable limitation</ins>

After adding SSN redaction, I asked Claude to help broaden the pattern to catch more formatting variants (dots, spaces, no separator). Broadening the pattern to catch more true positives (e.g. 987 65 4321, 987654321) structurally increase false positives too since a 9 digit order number or a zip code appended to an address can also match. This is not a bug that can be fixed away with more robust regex, it is an inherent trade off when using pattern matching in DLP. I chose to accept the broader pattern for this project, but documented the trade off explicitly in the code. This helped me recognize the limits of a security control being built, and being able to state them.

<ins>Example #2: A permission check that looked correct, but was not</ins>

After building the MCP server with a _ALLOWED_TOOLS_ gateway (employee: allowed, guest: denied), my first test run showed both identities receiving identical, correct customer data, which should have been denied entirely. No _[GATEWAY]_ log lines appeared in the terminal at all, for either identity. My print statements inside the tool were also writing to stdout, and were being silently absorbed by the MCP framework rather than reaching the terminal. This meant I had zero real visibility into whether the permission check had ever run.

My initial debugging prompt to Claude included the MCP client/server code, the missing gateway log output, and the fact that both identities appeared to receive the same answer. Claude suggested several possible causes, including the possibility that the permission check was never executing and the possibility that MCP's stdio transport was interfering with logging visibility. The latter turned out to be the key insight. Claude explained that MCP communicates over stdout and recommended routing diagnostic output to stderr instead. That immediately restored visibility into the server's execution path and allowed me to verify that the authorization logic was actually firing.

Despite Claude generating multiple explanations, there was not a definitive answer. I still had to verify them experimentally by changing the logging destination and observing the resulting behavior. The value was not that Claude magically found the bug; it helped narrow the search space and gave me a debugging consideration I likely would not have investigated immediately.

<ins>Example #3: A defensive parsing bug from an unexpected response shape</ins>

Partway through testing, _client.py_ crashed with an _AttributeError: 'ThinkingBlock' object has no attribute 'text'_. My code assumed _response.content[0]_ was always the text answer. Claude Sonnet 5 can return a ThinkingBlock (its internal reasoning) as the first content block, ahead of the actual text. After encountering this error, I provided Claude with the error and relevant section of _client.py_. Claude explained that Sonnet 5 responses can contain multiple content block types, including _text_, _tool_use_, and _thinking_, and that my code was assuming a fixed structure that was not guaranteed by the API. It suggested inspecting content block types explicitly instead of just indexing directly into _response.content[0]_. Instead of doing a one-time fix, I generalized the solution into the _extract_text()_ function that searches for context blocks by type. This allowed the code to be more robust against any future changes.

# Installation and Setup

```
git clone https://github.com/k3sharma/SaronicAIChallenge.git

cd SaronicAIChallenge

python3 -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env

# Then edit .env and add your own ANTHROPIC_API_KEY

python src/client.py
```

## To View the Audit Log After Running
```
python src/view_logs.py
```

## To Run the Adversarial Eval Suite 
```
python src/eval_suite.py
```


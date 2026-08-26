# Overview
Large language models become significantly more useful when they can interact with external systems through tools. However, granting an AI agent access to internal systems introduces the security challenge that users may attempt to access tools or data they are not authorized to use, through certain adversarial techniques. This is a secure MCP (Model Context Protocol) server exposing tools to Claude and it demonstrates how AI agents can safely interact with enterprise systems through server-side authorization and policy enforcement. This treats the MCP server as a boundary and ensures that any AI client connecting to it is subject to the same control.

I chose this project because it combines three areas that interest me: software engineering, security, and AI systems. My goal was to demonstrate how authorization and security controls can be integrated directly into the infrastructure that serves AI agents. 


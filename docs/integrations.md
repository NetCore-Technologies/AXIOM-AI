# AXIOM Agent Integrations

AXIOM is designed to work underneath external AI-agent runtimes.

## Supported integration families

### MCP

Model Context Protocol is the preferred integration path.

It allows an agent runtime to discover AXIOM capabilities as tools.

Examples include OpenClaw and PicoClaw.

### CLI

AXIOM can also integrate with local agent binaries.

### HTTP

Future AXIOM services can expose HTTP APIs for remote agent systems.

### A2A

Future versions can expose agent-to-agent capabilities for systems that support A2A-style communication.

## Philosophy

AXIOM should be the AI engineering layer.

External agents decide:

- what the user wants
- what tools to call
- how to communicate

AXIOM handles:

- models
- datasets
- training
- evaluation
- inference
- deployment

This separation keeps the architecture modular and prevents AXIOM from becoming tied to a single agent runtime.

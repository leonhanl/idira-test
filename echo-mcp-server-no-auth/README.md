# Echo MCP Server (No Auth)

A minimal, unauthenticated Python MCP server for CyberArk/Idira AI Agent Identity Broker experiments.

It exposes one Streamable HTTP endpoint and one tool:

- Endpoint: `http://127.0.0.1:3000/mcp`
- External hostname: `echo-mcp-server-no-auth.vitosdemo.com`
- Tool: `echo`
- Input: `{ "message": "..." }`
- Output: the message plus every HTTP request header visible to the MCP server

## Run locally

Requires Python 3.10 or newer and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python server.py
```

Use `http://127.0.0.1:3000/mcp` as the MCP server URL in the client or broker.

The server listens on `0.0.0.0:3000` by default. Local clients can connect to
`http://127.0.0.1:3000/mcp`; remote clients must use an address that resolves to
this machine. The MCP transport allows the external hostname
`echo-mcp-server-no-auth.vitosdemo.com` plus localhost for development. In the
expected deployment, a reverse proxy should terminate HTTPS and forward traffic
to port 3000.

## Verify

```bash
uv run pytest
uv run pyright
```

The integration test sends `x-idira-test: broker-visible-value` through a real MCP client and verifies that `echo` receives it.

## Important safety note

This server intentionally returns **all** inbound HTTP headers, including values such as `Authorization`, cookies, and identity headers. That behavior is useful for this experiment but unsafe for production. Do not expose it to untrusted users, do not send production credentials to it, and do not store its tool output in normal application logs or model transcripts.

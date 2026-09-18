# General MCP Client

A minimal test client for an MCP server using the Streamable HTTP transport.

The server URL is provided on the command line. The tool name, tool arguments,
and HTTP headers are intentionally hardcoded near the top of `main.py` so they
are easy to change during testing.

## Run

Requires Python 3.10 or newer and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python main.py http://127.0.0.1:3000/mcp
```

Pass the full MCP endpoint URL, including the `/mcp` route when the server uses
that route. The client calls `echo` with this argument:

```json
{"message": "hello from the general MCP client"}
```

It also sends these test headers with the MCP HTTP requests:

```text
x-idira-test: broker-visible-value
x-test-client: general-mcp-client
```

Edit `TOOL_ARGUMENTS` or `HTTP_HEADERS` in `main.py` to change them.

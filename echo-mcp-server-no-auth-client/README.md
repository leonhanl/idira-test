# Echo MCP Server (No Auth) Client

A dedicated local Python client for the unauthenticated
`echo-mcp-server-no-auth` server. It calls the CyberArk-exposed
`echo__echo-mcp-server-no-auth` tool through the CyberArk Secure AI Gateway
using OAuth authorization code flow with PKCE.

This client intentionally targets this one integration scenario. The upstream
Echo MCP server itself has no authentication; OAuth protects the CyberArk
Gateway endpoint used by this client.

The client reads the CyberArk registration output from:

- `lhan_mcp_client-credentials.json`
- `lhan_mcp_client-connect.json`

These files are ignored by Git because the credentials file contains the agent
client secret.

## Redirect URI

The default callback is:

```text
http://127.0.0.1:8765/oauth/callback
```

It must exactly match a redirect URL registered for the AI agent in CyberArk.
The client opens the listener only while authorization is in progress and waits
up to five minutes for the browser callback.

## Run

Requires Python 3.10 or newer and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python main.py
```

Each run opens the CyberArk authorization page in the default browser because
this test client keeps tokens only in memory. After authorization, the MCP SDK
exchanges the code for a token and calls the namespaced echo tool through the
`gatewayUrl` in the
connection file.

The registered AI agent must also be covered by a CyberArk access policy that
allows the echo tool on this MCP target. Authentication can succeed while the
tool call is still denied by policy.

If a different loopback URL was registered, pass the exact value:

```bash
uv run python main.py \
  --redirect-uri http://127.0.0.1:9000/oauth/callback
```

Custom file locations can also be supplied:

```bash
uv run python main.py \
  --credentials /path/to/agent-credentials.json \
  --connect /path/to/agent-connect.json
```

The tool name, arguments, and test HTTP headers remain hardcoded near the top
of `main.py` for easy modification.

Every outgoing HTTP request is printed before it is sent, including all header
names. Sensitive values such as `Authorization` and cookies are shown as
`<redacted>` so OAuth tokens are not written to terminal logs.

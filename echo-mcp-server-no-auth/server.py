import os
from typing import TypedDict

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.transport_security import TransportSecuritySettings


mcp = MCPServer("echo-mcp-server-no-auth")

transport_security = TransportSecuritySettings(
    allowed_hosts=[
        "echo-mcp-server-no-auth.vitosdemo.com",
        "echo-mcp-server-no-auth.vitosdemo.com:*",
        "127.0.0.1:*",
        "localhost:*",
    ],
    allowed_origins=[
        "https://echo-mcp-server-no-auth.vitosdemo.com",
        "http://127.0.0.1:*",
        "http://localhost:*",
    ],
)


class EchoResponse(TypedDict):
    headers: dict[str, str]
    message: str


@mcp.tool()
def echo(message: str, ctx: Context) -> EchoResponse:
    """Return the message and every HTTP header visible to this MCP server."""
    if ctx.headers is None:
        raise RuntimeError("The echo tool requires an HTTP transport")

    return {
        "headers": dict(ctx.headers),
        "message": message,
    }


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "3000")),
        stateless_http=True,
        json_response=True,
        transport_security=transport_security,
    )

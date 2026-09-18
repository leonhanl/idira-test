import argparse
import asyncio
import json
from typing import Any

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client


TOOL_NAME = "echo"
TOOL_ARGUMENTS = {"message": "hello from the general MCP client"}

# Test headers sent with every HTTP request to the MCP server.
HTTP_HEADERS = {
    "x-idira-test": "broker-visible-value",
    "x-test-client": "general-mcp-client",
}


async def call_echo(server_url: str) -> dict[str, Any]:
    async with httpx2.AsyncClient(headers=HTTP_HEADERS) as http_client:
        transport = streamable_http_client(
            server_url,
            http_client=http_client,
        )

        async with Client(transport) as mcp_client:
            result = await mcp_client.call_tool(TOOL_NAME, TOOL_ARGUMENTS)

    return result.model_dump(mode="json", exclude_none=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Call the hardcoded echo tool on an MCP Streamable HTTP server."
    )
    parser.add_argument(
        "server_url",
        help="Full MCP endpoint URL, for example http://127.0.0.1:3000/mcp",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = asyncio.run(call_echo(args.server_url))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

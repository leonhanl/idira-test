import argparse
import asyncio
import json
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, urlsplit

import httpx2
from mcp import Client
from mcp.client.auth import AuthorizationCodeResult, OAuthClientProvider
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken
from pydantic import AnyUrl


TOOL_NAME = "echo__echo-mcp-server-no-auth"
TOOL_ARGUMENTS = {"message": "hello from the CyberArk MCP client"}
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8765/oauth/callback"

# Test headers sent with every HTTP request through the CyberArk gateway.
HTTP_HEADERS = {
    "x-idira-test": "broker-visible-value",
    "x-test-client": "lhan-mcp-client",
}
SENSITIVE_HEADERS = {"authorization", "proxy-authorization", "cookie", "set-cookie"}


async def print_request(request: httpx2.Request) -> None:
    print(f"\n>>> {request.method} {request.url}")
    for name, value in request.headers.multi_items():
        displayed_value = "<redacted>" if name.lower() in SENSITIVE_HEADERS else value
        print(f"> {name}: {displayed_value}")
    print(flush=True)


@dataclass(frozen=True)
class CyberArkConfig:
    gateway_url: str
    client_id: str
    client_secret: str


class InMemoryTokenStorage:
    def __init__(self, client_info: OAuthClientInformationFull) -> None:
        self._tokens: OAuthToken | None = None
        self._client_info = client_info

    async def get_tokens(self) -> OAuthToken | None:
        return self._tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self._tokens = tokens

    async def get_client_info(self) -> OAuthClientInformationFull:
        return self._client_info

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self._client_info = client_info


class LoopbackOAuthCallback:
    def __init__(self, redirect_uri: str) -> None:
        parsed = urlsplit(redirect_uri)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise ValueError(
                "redirect URI must use an HTTP loopback address, for example "
                f"{DEFAULT_REDIRECT_URI}"
            )
        if parsed.port is None:
            raise ValueError("redirect URI must include a port")

        self._host = parsed.hostname
        self._port = parsed.port
        self._path = parsed.path or "/"
        self._server: asyncio.Server | None = None
        self._result: asyncio.Future[AuthorizationCodeResult] | None = None

    async def open_browser(self, authorization_url: str) -> None:
        if self._server is not None:
            raise RuntimeError("OAuth callback listener is already running")

        self._result = asyncio.get_running_loop().create_future()
        self._server = await asyncio.start_server(
            self._handle_request,
            host=self._host,
            port=self._port,
        )

        if await asyncio.to_thread(webbrowser.open, authorization_url):
            print("Opened the CyberArk authorization page in the default browser.")
        else:
            print(f"Open this CyberArk authorization URL manually:\n{authorization_url}")

    async def wait_for_result(self) -> AuthorizationCodeResult:
        if self._result is None:
            raise RuntimeError("OAuth callback listener has not been started")

        try:
            return await asyncio.wait_for(self._result, timeout=300)
        finally:
            if self._server is not None:
                self._server.close()
                await self._server.wait_closed()
            self._server = None
            self._result = None

    async def _handle_request(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            request_line = (await reader.readline()).decode("ascii", errors="replace")
            while await reader.readline() not in {b"\r\n", b"\n", b""}:
                pass

            parts = request_line.split(" ", 2)
            if len(parts) < 2:
                raise ValueError("invalid callback request")

            callback = urlsplit(parts[1])
            if callback.path != self._path:
                raise ValueError("unexpected callback path")

            params = parse_qs(callback.query)
            if "error" in params:
                description = params.get("error_description", params["error"])[0]
                raise RuntimeError(f"CyberArk authorization failed: {description}")

            code = params.get("code", [None])[0]
            if not code:
                raise ValueError("callback did not include an authorization code")

            result = AuthorizationCodeResult(
                code=code,
                state=params.get("state", [None])[0],
                iss=params.get("iss", [None])[0],
            )
            if self._result is not None and not self._result.done():
                self._result.set_result(result)
            await self._send_response(writer, 200, "Authorization complete. You can close this window.")
        except Exception as error:
            if self._result is not None and not self._result.done():
                self._result.set_exception(error)
            await self._send_response(writer, 400, str(error))

    async def _send_response(
        self,
        writer: asyncio.StreamWriter,
        status: int,
        message: str,
    ) -> None:
        reason = "OK" if status == 200 else "Bad Request"
        body = message.encode("utf-8")
        writer.write(
            (
                f"HTTP/1.1 {status} {reason}\r\n"
                "Content-Type: text/plain; charset=utf-8\r\n"
                f"Content-Length: {len(body)}\r\n"
                "Connection: close\r\n"
                "\r\n"
            ).encode()
            + body
        )
        await writer.drain()
        writer.close()
        await writer.wait_closed()


def load_json_object(path: Path) -> dict[str, object]:
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return cast(dict[str, object], raw)


def require_string(data: dict[str, object], key: str, path: Path) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path} must contain a non-empty {key!r} string")
    return value


def load_cyberark_config(credentials_path: Path, connect_path: Path) -> CyberArkConfig:
    credentials = load_json_object(credentials_path)
    connection = load_json_object(connect_path)

    client_id = require_string(credentials, "clientId", credentials_path)
    connection_client_id = require_string(connection, "clientId", connect_path)
    if client_id != connection_client_id:
        raise ValueError("clientId does not match between the credentials and connection files")

    return CyberArkConfig(
        gateway_url=require_string(connection, "gatewayUrl", connect_path),
        client_id=client_id,
        client_secret=require_string(credentials, "clientSecret", credentials_path),
    )


async def call_echo(config: CyberArkConfig, redirect_uri: str) -> dict[str, Any]:
    callback = LoopbackOAuthCallback(redirect_uri)
    redirect_url = AnyUrl(redirect_uri)

    client_info = OAuthClientInformationFull(
        client_id=config.client_id,
        client_secret=config.client_secret,
        client_name="lhan_mcp_client",
        redirect_uris=[redirect_url],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        token_endpoint_auth_method="client_secret_post",
        application_type="native",
    )
    storage = InMemoryTokenStorage(client_info)
    oauth = OAuthClientProvider(
        server_url=config.gateway_url,
        client_metadata=OAuthClientMetadata(
            client_name="lhan_mcp_client",
            redirect_uris=[redirect_url],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            token_endpoint_auth_method="client_secret_post",
            application_type="native",
        ),
        storage=storage,
        redirect_handler=callback.open_browser,
        callback_handler=callback.wait_for_result,
    )

    async with httpx2.AsyncClient(
        auth=oauth,
        headers=HTTP_HEADERS,
        event_hooks={"request": [print_request]},
    ) as http_client:
        transport = streamable_http_client(
            config.gateway_url,
            http_client=http_client,
        )

        # The current CyberArk gateway uses the initialize-based MCP handshake.
        async with Client(transport, mode="legacy") as mcp_client:
            result = await mcp_client.call_tool(TOOL_NAME, TOOL_ARGUMENTS)

    return result.model_dump(mode="json", exclude_none=True)


def parse_args() -> argparse.Namespace:
    client_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Call echo through the CyberArk Secure AI Gateway."
    )
    parser.add_argument(
        "--credentials",
        type=Path,
        default=client_dir / "lhan_mcp_client-credentials.json",
        help="CyberArk agent credentials JSON file",
    )
    parser.add_argument(
        "--connect",
        type=Path,
        default=client_dir / "lhan_mcp_client-connect.json",
        help="CyberArk agent connection JSON file",
    )
    parser.add_argument(
        "--redirect-uri",
        default=DEFAULT_REDIRECT_URI,
        help="Registered loopback OAuth callback URI",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_cyberark_config(args.credentials, args.connect)
    result = asyncio.run(call_echo(config, args.redirect_uri))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

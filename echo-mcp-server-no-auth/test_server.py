import asyncio
import os
import socket
import subprocess
import sys
import time
from typing import cast

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from server import EchoResponse


def get_free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_server(port: int, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + 10

    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise RuntimeError(f"Server exited early.\nstdout:\n{stdout}\nstderr:\n{stderr}")

        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                return
        except OSError:
            time.sleep(0.05)

    raise TimeoutError("Server did not start within 10 seconds")


async def call_echo(port: int) -> EchoResponse:
    async with httpx2.AsyncClient(
        headers={"x-idira-test": "broker-visible-value"}
    ) as http_client:
        transport = streamable_http_client(
            f"http://127.0.0.1:{port}/mcp",
            http_client=http_client,
        )
        async with Client(transport) as client:
            result = await client.call_tool("echo", {"message": "hello Idira"})

    assert result.structured_content is not None
    return cast(EchoResponse, result.structured_content)


def test_echo_returns_message_and_http_headers() -> None:
    port = get_free_port()
    env = os.environ | {"HOST": "127.0.0.1", "PORT": str(port)}
    process = subprocess.Popen(
        [sys.executable, "server.py"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        wait_for_server(port, process)
        response = asyncio.run(call_echo(port))
    finally:
        process.terminate()
        process.wait(timeout=5)

    assert response["message"] == "hello Idira"
    assert response["headers"]["x-idira-test"] == "broker-visible-value"

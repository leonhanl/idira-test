#!/usr/bin/env bash

set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

nohup uv run python server.py </dev/null >>server.log 2>&1 &
server_pid=$!

echo "Echo MCP server started in the background (PID: ${server_pid})"
echo "Logs: $(pwd)/server.log"

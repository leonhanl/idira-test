#!/usr/bin/env bash

set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

port="${1:-${PORT:-3000}}"

nohup env PORT="${port}" uv run python server.py </dev/null >>server.log 2>&1 &
server_pid=$!

echo "Echo MCP server started on port ${port} in the background (PID: ${server_pid})"
echo "Logs: $(pwd)/server.log"

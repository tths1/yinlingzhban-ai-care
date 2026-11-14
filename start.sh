#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
PORT_NUMBER=4173

if command -v lsof >/dev/null 2>&1 && lsof -ti tcp:"$PORT_NUMBER" >/dev/null 2>&1; then
  echo "端口 $PORT_NUMBER 已被占用。请先关闭旧服务器，或直接打开 http://127.0.0.1:$PORT_NUMBER/"
  exit 1
fi

if [ -f "$HOME/.zshrc" ]; then
  # Load the user's DASHSCOPE_API_KEY without putting it in the frontend.
  source "$HOME/.zshrc"
fi

exec python3 server.py

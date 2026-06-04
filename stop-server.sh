#!/usr/bin/env bash
cd "$(dirname "$0")"
[ -f .run/server.pid ] && kill "$(cat .run/server.pid)" 2>/dev/null && echo "已停止伺服器" || echo "找不到執行中的伺服器"
rm -f .run/server.pid

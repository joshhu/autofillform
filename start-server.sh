#!/usr/bin/env bash
# 啟動對外伺服器（單一埠同時服務前端網頁 + API），常駐且脫離終端機。
# 用法：./start-server.sh [PORT]   預設 8000；MOCK_MODE=1 可無 GPU 試前端。
set -e
cd "$(dirname "$0")"
PORT="${1:-8000}"
# 確保前端已 build
[ -d frontend/dist ] || ( cd frontend && npm install && npm run build )
mkdir -p .run
setsid nohup env MOCK_MODE="${MOCK_MODE:-0}" \
  backend/.venv/bin/uvicorn app.main:app \
  --app-dir "$(pwd)/backend" --host 0.0.0.0 --port "$PORT" \
  > .run/server.log 2>&1 < /dev/null &
echo $! > .run/server.pid
sleep 3
IP=$(hostname -I | tr ' ' '\n' | grep -E '^(10|172\.(1[6-9]|2[0-9]|3[01])|192\.168)\.' | head -1)
echo "✅ 伺服器已啟動 (PID $(cat .run/server.pid))"
echo "   本機:   http://localhost:${PORT}"
echo "   區網:   http://${IP}:${PORT}"
echo "   記錄檔: .run/server.log"

#!/usr/bin/env bash
# 本機開發：同時啟動後端 (8000) 與前端 (5173)。需先啟動 ollama 並 pull qwen3.6:35b。
set -e
cd "$(dirname "$0")"
( cd backend && MOCK_MODE=${MOCK_MODE:-0} .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 ) &
BACK=$!
( cd frontend && npm run dev ) &
FRONT=$!
trap "kill $BACK $FRONT 2>/dev/null" EXIT
wait

#!/bin/bash
# Mosaic 一键启动:自动建环境、装依赖、构建前端、起服务
set -e
cd "$(dirname "$0")"

PORT="${MOSAIC_PORT:-8788}"

if [ ! -d .venv ]; then
  echo "▸ 创建 Python 虚拟环境..."
  python3 -m venv .venv
fi

if ! .venv/bin/python -c "import fastapi, apscheduler, feedparser, anthropic" 2>/dev/null; then
  echo "▸ 安装后端依赖..."
  .venv/bin/pip install -q -r backend/requirements.txt
fi

if [ ! -d frontend/dist ]; then
  echo "▸ 构建前端(首次需要 npm)..."
  (cd frontend && npm install --no-fund --no-audit && npm run build)
fi

echo "▸ 启动 Mosaic → http://127.0.0.1:${PORT}"
(sleep 2 && open "http://127.0.0.1:${PORT}" 2>/dev/null) &
cd backend && exec ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "${PORT}"

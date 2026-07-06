#!/bin/bash
# Install Mosaic as a user LaunchAgent (macOS): auto-start on login, auto-restart on crash.
# Usage: ./scripts/install-service.sh      (from the repo root)
# Remove: launchctl unload ~/Library/LaunchAgents/com.mosaic.server.plist && rm ~/Library/LaunchAgents/com.mosaic.server.plist
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST="$HOME/Library/LaunchAgents/com.mosaic.server.plist"
PYTHON="$ROOT/.venv/bin/python"

if [ ! -x "$PYTHON" ]; then
  echo "未找到虚拟环境,请先运行 ./start.sh 完成初始化" >&2
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/data"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.mosaic.server</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>-m</string><string>uvicorn</string>
    <string>app.main:app</string>
    <string>--app-dir</string><string>backend</string>
    <string>--host</string><string>127.0.0.1</string>
    <string>--port</string><string>8788</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$ROOT/data/launchd.out.log</string>
  <key>StandardErrorPath</key><string>$ROOT/data/launchd.err.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load -w "$PLIST"
echo "✓ Mosaic 已安装为常驻服务(登录自启、崩溃自动拉起)"
echo "  状态: launchctl list | grep com.mosaic"
echo "  日志: $ROOT/data/launchd.{out,err}.log"
echo "  卸载: launchctl unload $PLIST && rm $PLIST"

#!/bin/bash
# Install the Cloudflare tunnel as a user LaunchAgent (companion to install-service.sh).
#
# The runtime script is generated into ~/Library/Application Support/Mosaic/
# rather than run from the repo: launchd's bash cannot read TCC-protected
# folders (~/Downloads, ~/Documents), where the repo may live.
#
# Requires: brew install cloudflared
# Remove: launchctl unload ~/Library/LaunchAgents/com.mosaic.tunnel.plist && rm ~/Library/LaunchAgents/com.mosaic.tunnel.plist
set -euo pipefail

SUPPORT="$HOME/Library/Application Support/Mosaic"
PLIST="$HOME/Library/LaunchAgents/com.mosaic.tunnel.plist"

command -v cloudflared >/dev/null || { echo "请先: brew install cloudflared" >&2; exit 1; }
mkdir -p "$SUPPORT" "$HOME/Library/LaunchAgents"

cat > "$SUPPORT/tunnel.sh" <<'EOF'
#!/bin/bash
# Cloudflare quick tunnel for Mosaic: public HTTPS -> local 8788.
# Quick-tunnel URLs rotate on restart; each start DMs the fresh URL via
# lark-cli (best-effort, only if feishu is configured in Mosaic settings).
set -uo pipefail
PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
SUPPORT="$HOME/Library/Application Support/Mosaic"
LOG="$SUPPORT/tunnel.log"

: > "$LOG"
cloudflared tunnel --url http://127.0.0.1:8788 --no-autoupdate >> "$LOG" 2>&1 &
CF_PID=$!
trap 'kill $CF_PID 2>/dev/null' EXIT

URL=""
for _ in $(seq 1 60); do
  URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" | head -1 || true)
  [ -n "$URL" ] && break
  sleep 1
done

if [ -n "$URL" ]; then
  echo "$URL" > "$SUPPORT/tunnel.url"
  echo "tunnel up: $URL"
  SETTINGS=$(curl -s --max-time 5 "http://127.0.0.1:8788/api/settings" || true)
  OPEN_ID=$(printf '%s' "$SETTINGS" | python3 -c \
    'import json,sys;print(json.load(sys.stdin)["settings"].get("feishu.open_id",""))' 2>/dev/null || true)
  TOKEN=$(printf '%s' "$SETTINGS" | python3 -c \
    'import json,sys;print(json.load(sys.stdin)["settings"].get("server.access_token",""))' 2>/dev/null || true)
  if [ -n "$OPEN_ID" ] && command -v lark-cli >/dev/null; then
    lark-cli im +messages-send --as bot --user-id "$OPEN_ID" --markdown \
"🌐 **Mosaic 公网地址已更新**
带口令直达(点开即用):
$URL/?key=$TOKEN

地址每次隧道重启会变,以最新一条为准。" >/dev/null 2>&1 || true
  fi
else
  echo "tunnel URL not detected within 60s (see tunnel.log)" >&2
fi

wait $CF_PID
EOF
chmod +x "$SUPPORT/tunnel.sh"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.mosaic.tunnel</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$SUPPORT/tunnel.sh</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$SUPPORT/tunnel.launchd.log</string>
  <key>StandardErrorPath</key><string>$SUPPORT/tunnel.launchd.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load -w "$PLIST"
echo "✓ 隧道已安装为常驻服务"
echo "  最新地址: cat \"$SUPPORT/tunnel.url\"(配置了飞书会自动 DM)"

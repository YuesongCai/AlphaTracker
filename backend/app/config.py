"""Central configuration for Mosaic backend."""
from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo

APP_NAME = "Mosaic"
VERSION = "1.1.0"

# Repo layout: <root>/backend/app/config.py -> root is two levels up from app/
ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("MOSAIC_DATA_DIR", ROOT_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "mosaic.db"
DB_URL = f"sqlite:///{DB_PATH}"

FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"

HOST = os.environ.get("MOSAIC_HOST", "127.0.0.1")
PORT = int(os.environ.get("MOSAIC_PORT", "8788"))

BEIJING = ZoneInfo("Asia/Shanghai")

# Polite identification for SEC EDGAR (fair-access policy). SEC's getcurrent
# endpoint additionally REQUIRES an email-shaped contact in the UA string.
# Priority: env MOSAIC_EDGAR_UA > data/secrets.json "edgar_ua" > generic default.
def _edgar_ua() -> str:
    ua = os.environ.get("MOSAIC_EDGAR_UA", "").strip()
    if ua:
        return ua
    try:
        import json
        secrets = json.loads((DATA_DIR / "secrets.json").read_text())
        if secrets.get("edgar_ua"):
            return str(secrets["edgar_ua"])
    except (OSError, ValueError):
        pass
    return "Mosaic research tool (set-your-contact@example.org)"


EDGAR_USER_AGENT = _edgar_ua()
HTTP_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)

# Default settings written to the settings table on first boot.
DEFAULT_SETTINGS: dict[str, object] = {
    "llm.mode": "auto",  # auto | api | cli | off
    "llm.api_key": "",
    "llm.base_url": "",
    "llm.model": "claude-sonnet-4-6",
    "llm.cli_model": "sonnet",
    "feishu.enabled": True,
    "feishu.open_id": "",  # 在设置页填写接收人 open_id(lark-cli bot DM)
    "feishu.lark_cli": "/opt/homebrew/bin/lark-cli",
    "sources.jin10_token": "",  # 金十数据 MCP token(mcp.jin10.com);也可用 env/data/secrets.json
    "server.access_token": "",  # 非本机访问的共享口令(首次启动自动生成);本机 127.0.0.1 免验

    "brief.morning": "08:00",
    "brief.evening": "19:30",
    "ingest.news_minutes": 20,
    "ingest.quotes_minutes": 30,
    "ingest.slow_minutes": 60,
    "alerts.enabled": True,
    "alerts.min_materiality": 4,
}

"""Jin10 (金十数据) MCP wire — the fastest CN-language macro/market flash feed.

Ported from the user's MacroRadar project (verified working):
- HTTP MCP at mcp.jin10.com, JSON-RPC over SSE responses
- MUST bypass any system proxy (domestic endpoint; proxies kill the SSE stream)
- Session dance: initialize -> notifications/initialized -> tools/call

Token resolution order: env MOSAIC_JIN10_TOKEN -> data/secrets.json -> settings.
Without a token the lane silently stays empty (product degrades gracefully).
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.request
from datetime import datetime, timezone

from .. import config

log = logging.getLogger(__name__)

URL = "https://mcp.jin10.com/mcp"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
# Domestic SSE endpoint: an empty ProxyHandler forces a direct connection,
# bypassing e.g. Clash on 127.0.0.1:7897 which truncates the stream (SSL EOF).
_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))

_calendar_cache: dict = {"at": 0.0, "data": []}


def get_token(db=None) -> str:
    token = os.environ.get("MOSAIC_JIN10_TOKEN", "").strip()
    if token:
        return token
    secrets = config.DATA_DIR / "secrets.json"
    if secrets.exists():
        try:
            token = (json.loads(secrets.read_text()).get("jin10_token") or "").strip()
            if token:
                return token
        except (OSError, json.JSONDecodeError):
            pass
    if db is not None:
        from ..db import get_setting
        return (get_setting(db, "sources.jin10_token", "") or "").strip()
    return ""


def _post(token: str, body: dict, sid: str | None = None) -> tuple[dict | None, str | None]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {token}",
        "User-Agent": UA,
    }
    if sid:
        headers["Mcp-Session-Id"] = sid
    req = urllib.request.Request(URL, data=json.dumps(body).encode(),
                                 headers=headers, method="POST")
    with _DIRECT.open(req, timeout=30) as resp:
        sid_out = resp.headers.get("mcp-session-id")
        raw = resp.read().decode()
    data = None
    for line in raw.splitlines():  # SSE: last data: line wins
        if line.startswith("data:"):
            data = json.loads(line[5:].strip())
    return data, sid_out


def call(tool: str, args: dict, db=None) -> dict | list | None:
    """One MCP tool call with a fresh session. Returns structuredContent."""
    token = get_token(db)
    if not token:
        return None
    try:
        _, sid = _post(token, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-11-25", "capabilities": {},
                       "clientInfo": {"name": "mosaic", "version": "1.1"}},
        })
        _post(token, {"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
        res, _ = _post(token, {
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": tool, "arguments": args},
        }, sid)
    except Exception as exc:  # noqa: BLE001 - source adapters never crash ingest
        log.warning("jin10 %s failed: %s", tool, exc)
        return None
    sc = (res or {}).get("result", {}).get("structuredContent")
    return sc if sc is not None else res


def _items(sc) -> list:
    if not sc:
        return []
    data = sc.get("data", sc) if isinstance(sc, dict) else sc
    if isinstance(data, dict):
        return data.get("items") or data.get("data") or []
    return data if isinstance(data, list) else []


def _parse_time(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except (ValueError, TypeError):
        return datetime.utcnow()


def _title(content: str) -> str:
    """Flash items are paragraphs; the 【headline】 or first sentence is the title."""
    match = re.match(r"^【(.+?)】", content)
    if match:
        return match.group(1)[:150]
    for sep in ("。", "；", "\n"):
        if sep in content:
            return content.split(sep)[0][:150]
    return content[:150]


def fetch_flash(limit: int = 30, db=None) -> list[dict]:
    """Market-wide CN flash wire -> normalized signal dicts (lane=macro)."""
    items = _items(call("list_flash", {}, db))
    out = []
    for item in items[:limit]:
        content = (item.get("content") or "").strip().replace("\n", " ")
        if not content or len(content) < 8:
            continue
        out.append({
            "source": "jin10",
            "lane": "macro",
            "title": _title(content),
            "url": item.get("url") or "",
            "publisher": "金十数据",
            "summary": content[:600],
            "published_at": _parse_time(item.get("time", "")),
        })
    return out


def fetch_calendar(min_star: int = 2, db=None) -> list[dict]:
    """Today's economic calendar (cached 10 min) for the Radar page and briefs."""
    now = time.time()
    if now - _calendar_cache["at"] < 600:
        return _calendar_cache["data"]
    raw = call("list_calendar", {}, db)
    arr = raw.get("data") if isinstance(raw, dict) else raw
    if isinstance(arr, dict):
        arr = arr.get("data") or arr.get("items") or []
    today = datetime.now(config.BEIJING).strftime("%Y-%m-%d")
    out = [
        {"pub_time": it.get("pub_time"), "star": it.get("star") or 0,
         "title": it.get("title"), "consensus": it.get("consensus"),
         "previous": it.get("previous"), "actual": it.get("actual"),
         "affect": it.get("affect_txt") or ""}
        for it in (arr or [])
        if str(it.get("pub_time", "")).startswith(today) and (it.get("star") or 0) >= min_star
    ]
    _calendar_cache.update(at=now, data=out)
    return out

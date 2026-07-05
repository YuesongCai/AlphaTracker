"""Feishu delivery via local lark-cli (verified bot -> user DM channel)."""
from __future__ import annotations

import logging
import subprocess

from sqlalchemy.orm import Session

from ..db import get_setting

log = logging.getLogger(__name__)


def send_markdown(db: Session, content: str) -> tuple[bool, str]:
    """Send a markdown DM to the configured user. Returns (ok, error)."""
    if not get_setting(db, "feishu.enabled", True):
        return False, "飞书推送已关闭"
    open_id = (get_setting(db, "feishu.open_id", "") or "").strip()
    if not open_id:
        return False, "未配置飞书 open_id"
    cli = get_setting(db, "feishu.lark_cli", "lark-cli")
    cmd = [cli, "im", "+messages-send", "--as", "bot",
           "--user-id", open_id, "--markdown", content]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    except FileNotFoundError:
        return False, f"未找到 lark-cli: {cli}"
    except subprocess.TimeoutExpired:
        return False, "lark-cli 调用超时"
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()[:300]
        log.warning("feishu send failed: %s", err)
        return False, err or f"lark-cli 退出码 {proc.returncode}"
    return True, ""

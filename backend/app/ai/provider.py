"""LLM provider with three-tier degradation: Anthropic API -> claude CLI -> off.

The product must stay fully usable with no LLM at all (heuristics take over),
and light up automatically once a key appears in settings or `claude -p` works.
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import threading
import time

from sqlalchemy.orm import Session

from ..db import get_setting

log = logging.getLogger(__name__)

_probe_lock = threading.Lock()
_cli_probe: dict = {"checked_at": 0.0, "ok": False, "detail": ""}
PROBE_TTL = 15 * 60  # re-probe the CLI at most every 15 minutes


class LLMUnavailable(Exception):
    """Raised when no live LLM backend is available."""


def _sanitized_env() -> dict:
    """Nested Claude Code sessions pollute env in ways that break `claude -p`."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("CLAUDE", "ANTHROPIC"))}
    env.setdefault("PATH", "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin")
    return env


def probe_cli(force: bool = False) -> tuple[bool, str]:
    """Check whether `claude -p` works on this machine. Cached."""
    with _probe_lock:
        now = time.time()
        if not force and now - _cli_probe["checked_at"] < PROBE_TTL:
            return _cli_probe["ok"], _cli_probe["detail"]
        try:
            proc = subprocess.run(
                ["claude", "-p", "Reply with exactly: OK", "--output-format", "text"],
                capture_output=True, text=True, timeout=60, env=_sanitized_env(),
            )
            ok = proc.returncode == 0 and "OK" in (proc.stdout or "")
            detail = "claude CLI 可用" if ok else (proc.stderr or proc.stdout or "unknown error").strip()[:200]
        except FileNotFoundError:
            ok, detail = False, "未找到 claude CLI"
        except subprocess.TimeoutExpired:
            ok, detail = False, "claude CLI 探测超时"
        except OSError as exc:
            ok, detail = False, str(exc)[:200]
        _cli_probe.update(checked_at=now, ok=ok, detail=detail)
        return ok, detail


def resolve_backend(db: Session) -> tuple[str, str]:
    """Return (backend, detail): backend in api|cli|off."""
    mode = get_setting(db, "llm.mode", "auto")
    api_key = (get_setting(db, "llm.api_key", "") or "").strip()

    if mode == "off":
        return "off", "已在设置中关闭"
    if mode == "api" or (mode == "auto" and api_key):
        if api_key:
            return "api", "Anthropic API"
        return "off", "选择了 API 模式但未配置 key"
    if mode in ("cli", "auto"):
        ok, detail = probe_cli()
        if ok:
            return "cli", detail
        if mode == "cli":
            return "off", f"CLI 不可用: {detail}"
    return "off", "无可用后端(可在设置页配置 API key 或登录 claude CLI)"


def _complete_api(db: Session, prompt: str, system: str, max_tokens: int) -> str:
    import anthropic

    api_key = (get_setting(db, "llm.api_key", "") or "").strip()
    base_url = (get_setting(db, "llm.base_url", "") or "").strip() or None
    model = get_setting(db, "llm.model", "claude-sonnet-4-6")
    client = anthropic.Anthropic(api_key=api_key, base_url=base_url, timeout=120)
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system or "You are a precise assistant.",
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in msg.content if block.type == "text")


def _complete_cli(db: Session, prompt: str, system: str, max_tokens: int) -> str:
    model = get_setting(db, "llm.cli_model", "sonnet")
    full = f"{system}\n\n{prompt}" if system else prompt
    proc = subprocess.run(
        ["claude", "-p", full, "--output-format", "text", "--model", model],
        capture_output=True, text=True, timeout=300, env=_sanitized_env(),
    )
    if proc.returncode != 0:
        raise LLMUnavailable(f"claude CLI error: {(proc.stderr or '')[:300]}")
    return proc.stdout or ""


def complete(db: Session, prompt: str, system: str = "", max_tokens: int = 4000) -> tuple[str, str]:
    """Run a completion. Returns (text, engine). Raises LLMUnavailable."""
    backend, detail = resolve_backend(db)
    if backend == "off":
        raise LLMUnavailable(detail)
    try:
        if backend == "api":
            return _complete_api(db, prompt, system, max_tokens), "api"
        return _complete_cli(db, prompt, system, max_tokens), "cli"
    except LLMUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 - normalize SDK/subprocess errors
        log.warning("LLM %s backend failed: %s", backend, exc)
        raise LLMUnavailable(f"{backend} 调用失败: {str(exc)[:300]}") from exc


# ------------------------------------------------------------- json parsing --

_JSON_RE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.DOTALL)


def extract_json(text: str):
    """Pull the first JSON object/array out of model text. Raises ValueError."""
    if not text:
        raise ValueError("empty response")
    candidates = [m.group(1) for m in _JSON_RE.finditer(text)]
    candidates.append(text)
    # also try from the first bracket to the last matching one
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = text.find(opener), text.rfind(closer)
        if start != -1 and end > start:
            candidates.append(text[start : end + 1])
    for cand in candidates:
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            continue
    raise ValueError(f"no parseable JSON in response: {text[:200]!r}")


def complete_json(db: Session, prompt: str, system: str = "", max_tokens: int = 4000):
    """Completion that must return JSON; one retry with a nudge."""
    text, engine = complete(db, prompt, system, max_tokens)
    try:
        return extract_json(text), engine
    except ValueError:
        nudged = prompt + "\n\n只输出合法 JSON,不要任何其他文字、不要 markdown 代码块。"
        text, engine = complete(db, nudged, system, max_tokens)
        return extract_json(text), engine  # second failure propagates

"""HTTP via the system curl binary.

Yahoo Finance and StockTwits sit behind Cloudflare-style TLS fingerprinting
that blocks Python HTTP clients (403) while curl passes. For those adapters
we shell out to curl — boring, dependency-free, and it works everywhere macOS.
"""
from __future__ import annotations

import json
import logging
import subprocess
from urllib.parse import urlencode

log = logging.getLogger(__name__)

# Yahoo rate-limits per (IP, User-Agent); a small pool lets us rotate off a
# burned identity. Order matters: plainest first.
UA_POOL = [
    "Mozilla/5.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
]


def get(url: str, params: dict | None = None, timeout: int = 20,
        headers: dict | None = None, cookie_jar: str | None = None,
        ua: str | None = None) -> str | None:
    """GET a URL with curl. Returns body text or None on any failure."""
    if params:
        url = f"{url}?{urlencode(params)}"
    cmd = ["curl", "-sS", "--compressed", "--max-time", str(timeout),
           "-H", f"User-Agent: {ua or UA_POOL[0]}", "-L"]
    for key, value in (headers or {}).items():
        cmd += ["-H", f"{key}: {value}"]
    if cookie_jar:
        cmd += ["-b", cookie_jar, "-c", cookie_jar]
    cmd.append(url)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
    except (subprocess.TimeoutExpired, OSError) as exc:
        log.warning("curl failed for %s: %s", url[:80], exc)
        return None
    if proc.returncode != 0:
        log.warning("curl exit %s for %s: %s", proc.returncode, url[:80],
                    (proc.stderr or "")[:150])
        return None
    return proc.stdout


def get_json(url: str, params: dict | None = None, timeout: int = 20,
             headers: dict | None = None, cookie_jar: str | None = None):
    """GET + json parse, rotating User-Agents past per-UA rate limits."""
    for ua in UA_POOL:
        body = get(url, params, timeout, headers, cookie_jar, ua=ua)
        if body is None:
            return None  # transport error; a different UA won't help
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            if "Too Many Requests" in body or "429" in body[:40]:
                log.info("rate-limited on %s with UA %r, rotating", url[:60], ua[:20])
                continue
            log.warning("non-JSON response from %s: %s", url[:80], body[:120])
            return None
    return None

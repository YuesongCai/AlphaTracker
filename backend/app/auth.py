"""Shared-token gate for non-local access (Cloudflare Tunnel / LAN).

Localhost requests pass untouched — the product stays zero-friction on the
Mac it runs on. Anything arriving through a tunnel must present the access
token once (?key=... or the login form); a cookie keeps the session.
"""
from __future__ import annotations

import hmac
import secrets

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .db import get_setting, session_scope, set_setting

COOKIE = "mosaic_key"
OPEN_PATHS = {"/healthz"}

_token_cache: str | None = None


def ensure_access_token() -> str:
    """Generate-once shared token, persisted in settings."""
    global _token_cache
    if _token_cache:
        return _token_cache
    with session_scope() as db:
        token = (get_setting(db, "server.access_token", "") or "").strip()
        if not token:
            token = secrets.token_urlsafe(9)
            set_setting(db, "server.access_token", token)
    _token_cache = token
    return token


def _is_local(request: Request) -> bool:
    host = request.client.host if request.client else ""
    return host in ("127.0.0.1", "::1", "localhost", "testclient")


_LOGIN_PAGE = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mosaic · 访问验证</title>
<style>
body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
background:#0b0e14;color:#e6e8eb;font:15px/1.6 -apple-system,system-ui,sans-serif}}
.card{{background:#131720;border:1px solid #232a36;border-radius:12px;padding:32px;width:320px}}
h1{{font-size:17px;margin:0 0 4px}}p{{color:#8b98a9;font-size:12.5px;margin:0 0 20px}}
input{{width:100%;box-sizing:border-box;background:#0b0e14;border:1px solid #232a36;color:#e6e8eb;
border-radius:8px;padding:10px 12px;font-size:14px;margin-bottom:12px;outline:none}}
input:focus{{border-color:#f0b429}}
button{{width:100%;background:#f0b429;color:#0b0e14;border:0;border-radius:8px;
padding:10px;font-size:14px;font-weight:600;cursor:pointer}}
.err{{color:#ff7b72;font-size:12px;margin-bottom:10px}}
</style></head><body><div class="card">
<h1>◈ MOSAIC</h1><p>Variant Perception Engine · 输入访问口令</p>
{error}
<form method="get" action="/">
<input name="key" type="password" placeholder="访问口令" autofocus autocomplete="current-password">
<button type="submit">进入</button>
</form></div></body></html>"""


class AccessTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if _is_local(request) or request.url.path in OPEN_PATHS:
            return await call_next(request)

        token = ensure_access_token()
        supplied = request.query_params.get("key") or request.cookies.get(COOKIE) or ""
        if hmac.compare_digest(supplied, token):
            if request.query_params.get("key"):
                # strip the key from the URL and persist via cookie
                clean = request.url.remove_query_params("key")
                resp = RedirectResponse(str(clean), status_code=302)
            else:
                return await call_next(request)
            resp.set_cookie(COOKIE, token, max_age=90 * 24 * 3600,
                            httponly=True, samesite="lax", secure=True)
            return resp

        error = '<div class="err">口令不正确</div>' if request.query_params.get("key") else ""
        if request.url.path.startswith("/api"):
            return HTMLResponse('{"detail":"unauthorized"}', status_code=401,
                                media_type="application/json")
        return HTMLResponse(_LOGIN_PAGE.format(error=error), status_code=401)

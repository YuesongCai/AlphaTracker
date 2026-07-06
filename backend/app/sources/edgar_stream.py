"""SEC EDGAR market-WIDE current-filings stream (not just coverage names).

`getcurrent` Atom feed surfaces every new 8-K (corporate events) and SC 13D
(activist stakes) across the whole market — a corporate-events radar that
needs no ticker input. Filer name lands in `entities` for clustering.
"""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime

import feedparser

from .. import config
from . import curlhttp

log = logging.getLogger(__name__)

_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
# form type -> (chinese label, default materiality hint used by heuristics)
STREAM_FORMS = {"8-K": "重大事件公告", "SC 13D": "举牌(积极持股)"}

_TITLE_RE = re.compile(r"^(?P<form>[A-Z0-9\-/ ]+?) - (?P<name>.+?) \((?P<cik>\d{10})\)")


def _clean_company(name: str) -> str:
    """'Apple Inc. (Filer)' -> 'Apple Inc.'; strip trailing corp suffixes noise."""
    name = re.sub(r"\s*\((Filer|Subject|Reporting)\)\s*$", "", name).strip()
    return name[:120]


def fetch_stream(form: str, count: int = 40) -> list[dict]:
    body = curlhttp.get(_URL, params={
        "action": "getcurrent", "type": form, "company": "", "dateb": "",
        "owner": "include", "count": count, "output": "atom",
    }, timeout=25, headers={"User-Agent": config.EDGAR_USER_AGENT})
    if not body:
        return []
    parsed = feedparser.parse(body)
    out = []
    for entry in parsed.entries:
        title = getattr(entry, "title", "")
        match = _TITLE_RE.match(title)
        if not match:
            continue
        got_form = match.group("form").strip()
        # getcurrent's type filter is prefix-based (8-K also returns 8-K/A etc.)
        if not got_form.startswith(form):
            continue
        company = _clean_company(match.group("name"))
        published = datetime.utcnow()
        parsed_time = getattr(entry, "updated_parsed", None)
        if parsed_time:
            published = datetime.utcfromtimestamp(time.mktime(parsed_time))
        label = STREAM_FORMS.get(form, form)
        out.append({
            "source": "edgar_stream",
            "lane": "filings",
            "title": f"[{got_form}] {company} · {label}",
            "url": getattr(entry, "link", ""),
            "publisher": "SEC EDGAR",
            "summary": "",
            "published_at": published,
            "entities": [company],
            "form": got_form,
        })
    return out


def fetch_all(count: int = 40) -> list[dict]:
    items: list[dict] = []
    for form in STREAM_FORMS:
        try:
            items.extend(fetch_stream(form, count))
        except Exception as exc:  # noqa: BLE001
            log.warning("edgar stream %s failed: %s", form, exc)
        time.sleep(0.4)
    return items

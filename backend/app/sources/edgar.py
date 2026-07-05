"""SEC EDGAR — official filings for US tickers (8-K, 10-K/Q, 13D/G, S-1...).

Fair-access policy requires an identifying User-Agent; we send one.
"""
from __future__ import annotations

import logging
from datetime import datetime

import httpx

from .. import config

log = logging.getLogger(__name__)

# Forms worth surfacing as signals; Form 4 (insider) is noisy -> low default materiality.
INTERESTING_FORMS = {
    "8-K": "重大事件公告",
    "10-K": "年报",
    "10-Q": "季报",
    "6-K": "外国发行人报告",
    "20-F": "外国发行人年报",
    "SC 13D": "举牌(积极持股)",
    "SC 13G": "大额持股申报",
    "S-1": "IPO/增发注册",
    "424B5": "发行说明书",
    "DEF 14A": "股东会文件",
    "4": "内部人交易",
}

_HEADERS = {"User-Agent": config.EDGAR_USER_AGENT, "Accept-Encoding": "gzip"}

_ticker_cik_cache: dict[str, str] | None = None


def lookup_cik(symbol: str) -> str | None:
    """Map ticker -> zero-padded CIK using SEC's public mapping file."""
    global _ticker_cik_cache
    if _ticker_cik_cache is None:
        try:
            resp = httpx.get(
                "https://www.sec.gov/files/company_tickers.json",
                headers=_HEADERS,
                timeout=30,
            )
            resp.raise_for_status()
            _ticker_cik_cache = {
                row["ticker"].upper(): str(row["cik_str"]).zfill(10)
                for row in resp.json().values()
            }
        except Exception as exc:  # noqa: BLE001
            log.warning("edgar cik mapping fetch failed: %s", exc)
            return None
    return _ticker_cik_cache.get(symbol.upper())


def fetch_filings(cik: str, limit: int = 40) -> list[dict]:
    """Recent filings for a CIK, filtered to interesting forms."""
    try:
        resp = httpx.get(
            f"https://data.sec.gov/submissions/CIK{cik}.json",
            headers=_HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        log.warning("edgar submissions failed for CIK %s: %s", cik, exc)
        return []

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    docs = recent.get("primaryDocument", [])
    items_desc = recent.get("items", [])

    out: list[dict] = []
    cik_int = str(int(cik))
    for i, form in enumerate(forms[:200]):
        if form not in INTERESTING_FORMS:
            continue
        accession = accessions[i].replace("-", "")
        doc = docs[i] if i < len(docs) else ""
        url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession}/{doc}"
        label = INTERESTING_FORMS[form]
        extra = f" · items {items_desc[i]}" if i < len(items_desc) and items_desc[i] else ""
        try:
            published = datetime.strptime(dates[i], "%Y-%m-%d")
        except (ValueError, IndexError):
            published = datetime.utcnow()
        out.append(
            {
                "source": "edgar",
                "title": f"[{form}] {label}{extra}",
                "url": url,
                "publisher": "SEC EDGAR",
                "summary": "",
                "published_at": published,
                "form": form,
            }
        )
        if len(out) >= limit:
            break
    return out

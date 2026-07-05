"""Rule-based fallback triage — keeps the product alive with zero LLM.

Deliberately conservative: keyword event classification, materiality by
event type + source, no so-what prose (the UI explains AI is not wired up).
"""
from __future__ import annotations

import re

# (event_type, materiality, sentiment_hint) keyed by keyword regex, first match wins.
_RULES: list[tuple[str, str, int, int]] = [
    (r"\b(acqui(re|sition)|merger|buyout|takeover|收购|合并)\b", "mna", 5, 1),
    (r"\b(guidance|outlook|forecast) (cut|lower|raise|hike)|下调指引|上调指引", "guidance", 5, 0),
    (r"\b(cuts?|lowers?|raises?|hikes?) (guidance|outlook|forecast)\b", "guidance", 5, 0),
    (r"\b(earnings|results|quarterly|Q[1-4] (results|revenue)|财报|业绩)\b", "earnings", 4, 0),
    (r"\b(SEC|DOJ|FTC|antitrust|probe|investigation|lawsuit|sue[ds]?|监管|反垄断|诉讼)\b", "legal", 4, -1),
    (r"\b(recall|ban|fine[ds]?|penalty|罚款|召回)\b", "regulatory", 4, -1),
    (r"\b(CEO|CFO|CTO|chief executive) (steps? down|resign|depart|exit|离职|辞任)", "management", 4, -1),
    (r"\b(names?|appoints?|hires?) (new )?(CEO|CFO|CTO)\b", "management", 3, 0),
    (r"\b(launch(es)?|unveil(s)?|announc(es|ed) (new )?(product|chip|model|service)|发布)\b", "product", 3, 1),
    (r"\b(partnership|partners? with|deal with|contract|合作|订单)\b", "product", 3, 1),
    (r"\b(buyback|repurchase|dividend|split|回购|分红|拆股)\b", "capital", 3, 1),
    (r"\b(offering|raises? \$|IPO|convertible|增发|配股)\b", "capital", 3, -1),
    (r"\b(upgrade[ds]?|downgrade[ds]?|price target|initiat(es|ed) coverage|评级)\b", "analyst", 2, 0),
    (r"\b(insider|Form 4|10b5-1)\b", "insider", 2, 0),
    (r"\b(inflation|Fed|tariff|rate (cut|hike)|GDP|CPI|关税|降息|加息)\b", "macro", 2, 0),
]

_UP_WORDS = re.compile(r"\b(surge[ds]?|soar(s|ed)?|jump(s|ed)?|rall(y|ies)|beat[s]?|record|大涨|新高|超预期)\b", re.I)
_DOWN_WORDS = re.compile(r"\b(plunge[ds]?|sink[s]?|tumble[ds]?|drop(s|ped)?|miss(es|ed)?|slump|大跌|暴跌|低于预期)\b", re.I)
_NOISE = re.compile(
    r"(top \d+ stocks|stocks to (buy|watch)|should you buy|motley fool|prediction|"
    r"here'?s why|3 reasons|best stocks|vs\.?\s|compared)", re.I,
)

_EDGAR_FORM_MATERIALITY = {"8-K": 4, "10-K": 3, "10-Q": 3, "6-K": 3, "20-F": 3,
                           "SC 13D": 5, "SC 13G": 3, "S-1": 3, "424B5": 3, "DEF 14A": 2, "4": 2}


def triage_one(title: str, source: str = "google_news", form: str | None = None) -> dict:
    """Classify a single signal without an LLM."""
    text = title or ""
    if source == "edgar" and form:
        return {
            "relevance": 0.9,
            "materiality": _EDGAR_FORM_MATERIALITY.get(form, 2),
            "sentiment": 0,
            "event_type": "insider" if form == "4" else "regulatory" if form.startswith("SC") else "earnings" if form in ("10-K", "10-Q", "20-F") else "other",
            "so_what": "",
            "variant": False,
        }

    event_type, materiality, sentiment = "other", 2, 0
    for pattern, etype, mat, senti in _RULES:
        if re.search(pattern, text, re.I):
            event_type, materiality, sentiment = etype, mat, senti
            break

    if _UP_WORDS.search(text):
        sentiment = max(sentiment, 1)
    if _DOWN_WORDS.search(text):
        sentiment = min(sentiment, -1)

    relevance = 0.6
    if _NOISE.search(text):
        relevance, materiality = 0.15, 1

    return {
        "relevance": relevance,
        "materiality": materiality,
        "sentiment": sentiment,
        "event_type": event_type,
        "so_what": "",
        "variant": False,
    }

from __future__ import annotations

import requests
from functools import lru_cache
from typing import Optional, Dict, Any

# Mentioned as the ticker-to-CIK mapping source in EDGAR API guides. [2](https://dealcharts.org/blog/sec-edgar-api-guide)
TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"

def _get_json(url: str, user_agent: str, timeout: int = 30) -> Dict[str, Any]:
    headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json()

@lru_cache(maxsize=1)
def load_ticker_map(user_agent: str) -> Dict[str, str]:
    """
    Returns dict: TICKER -> CIK10 (zero-padded 10-digit string)
    """
    data = _get_json(TICKER_MAP_URL, user_agent=user_agent)

    # company_tickers.json is keyed by integers-as-strings, each record has 'ticker' and 'cik_str'
    out: Dict[str, str] = {}
    for _, rec in data.items():
        ticker = str(rec.get("ticker", "")).upper().strip()
        cik = rec.get("cik_str", None)
        if ticker and cik is not None:
            cik10 = str(cik).zfill(10)
            out[ticker] = cik10
    return out

def ticker_to_cik10(ticker: str, user_agent: str) -> Optional[str]:
    """
    Returns CIK padded to 10 digits for a ticker, or None if not found.
    """
    t = ticker.upper().strip()
    m = load_ticker_map(user_agent)
    return m.get(t)

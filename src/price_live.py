# src/price_live.py
from __future__ import annotations

import time
import json
from pathlib import Path
from io import StringIO
from typing import Optional, Tuple

import pandas as pd
import requests

CACHE = Path("price_cache.json")

def fetch_stooq_daily_close(symbol: str = "aapl.us", timeout: int = 20) -> Tuple[float, str]:
    """
    Fetch daily OHLCV from Stooq as CSV and return latest Close and Date.
    """
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text)).dropna()
    last = df.iloc[-1]
    return float(last["Close"]), str(last["Date"])

def get_price(symbol: str = "aapl.us") -> Tuple[Optional[float], Optional[str], str]:
    """
    Try live fetch; if it fails, return cached fallback.
    Returns (price, date, status).
    """
    now = time.time()
    try:
        close, date = fetch_stooq_daily_close(symbol=symbol)
        CACHE.write_text(json.dumps({"close": close, "date": date, "t": now}))
        return close, date, "live"
    except Exception:
        if CACHE.exists():
            c = json.loads(CACHE.read_text())
            return c.get("close"), c.get("date"), "cached_fallback"
        return None, None, "unavailable"
``

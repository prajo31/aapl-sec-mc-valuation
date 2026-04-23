from __future__ import annotations

import time
import json
from pathlib import Path
from io import StringIO
from typing import Optional, Tuple

import pandas as pd
import requests

CACHE_FILE = Path("price_cache.json")


def fetch_stooq_daily(symbol: str = "aapl.us", timeout: int = 20) -> Tuple[float, str]:
    """
    Fetch daily price data from Stooq and return (close, date).
    """
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()

    df = pd.read_csv(StringIO(response.text))
    df = df.dropna()

    last_row = df.iloc[-1]
    return float(last_row["Close"]), str(last_row["Date"])


def get_price(symbol: str = "aapl.us") -> Tuple[Optional[float], Optional[str], str]:
    """
    Try to fetch live price; if it fails, fall back to cached value.
    Returns (price, date, status).
    """
    try:
        price, date = fetch_stooq_daily(symbol)
        CACHE_FILE.write_text(
            json.dumps(
                {"price": price, "date": date, "timestamp": time.time()}
            )
        )
        return price, date, "live"

    except Exception:
        if CACHE_FILE.exists():
            cached = json.loads(CACHE_FILE.read_text())
            return cached.get("price"), cached.get("date"), "cached"

        return None, None, "unavailable"

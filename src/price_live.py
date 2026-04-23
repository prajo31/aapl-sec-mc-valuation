from __future__ import annotations

import time
import json
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

CACHE_FILE = Path("price_cache.json")

def _cache_write(price: float, date: str) -> None:
    CACHE_FILE.write_text(json.dumps({"price": price, "date": date, "timestamp": time.time()}))

def _cache_read() -> Tuple[Optional[float], Optional[str]]:
    if not CACHE_FILE.exists():
        return None, None
    c = json.loads(CACHE_FILE.read_text())
    return c.get("price"), c.get("date")

def fetch_yfinance_price(symbol: str = "AAPL") -> Tuple[float, str]:
    """
    Fetch latest available close via yfinance history (more reliable than .info in many cases).
    """
    import yfinance as yf  # imported here so app still loads if dependency isn't installed yet

    t = yf.Ticker(symbol)
    hist = t.history(period="5d", interval="1d")  # last few daily bars
    if hist is None or hist.empty:
        raise RuntimeError("yfinance returned empty history")
    last_idx = hist.index[-1]
    last_close = float(hist["Close"].iloc[-1])
    return last_close, str(last_idx.date())

def get_price(symbol: str = "aapl.us") -> Tuple[Optional[float], Optional[str], str]:
    """
    Primary: yfinance (AAPL)
    Fallback: cached value
    """
    # map stooq-style "aapl.us" to yfinance "AAPL"
    yf_symbol = "AAPL" if symbol.lower().startswith("aapl") else symbol.upper().split(".")[0]

    try:
        price, date = fetch_yfinance_price(yf_symbol)
        _cache_write(price, date)
        return price, date, "live_yfinance"
    except Exception:
        price, date = _cache_read()
        if price is not None:
            return price, date, "cached"
        return None, None, "unavailable"

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


def dcf_value_per_share(
    fcf0: float,
    shares: float,
    years: int,
    growth: float,
    wacc: float,
    terminal_g: float,
) -> float:
    """
    Deterministic 1-stage growth DCF:

      FCF_t = FCF0 * (1+growth)^t for t=1..years
      PV(FCFs) = sum(FCF_t / (1+wacc)^t)
      Terminal Value at year N:
        TV = FCF_N * (1+terminal_g) / (wacc - terminal_g)
      PV(TV) = TV / (1+wacc)^N

    Returns value per share.
    """
    if shares <= 0:
        raise ValueError("shares must be positive")
    if wacc <= terminal_g:
        # Gordon growth requires wacc > terminal_g
        raise ValueError("wacc must be greater than terminal_g")

    pv = 0.0
    fcf = fcf0
    for t in range(1, years + 1):
        fcf = fcf * (1.0 + growth)
        pv += fcf / ((1.0 + wacc) ** t)

    tv = fcf * (1.0 + terminal_g) / (wacc - terminal_g)
    pv_tv = tv / ((1.0 + wacc) ** years)

    ev = pv + pv_tv
    return ev / shares


def _bisect_solve(
    func,
    low: float,
    high: float,
    target: float,
    max_iter: int = 80,
    tol: float = 1e-6,
) -> Optional[float]:
    """
    Generic bisection solver for func(x) = target.
    Returns None if the target is not bracketed in [low, high].
    """
    f_low = func(low) - target
    f_high = func(high) - target

    # Need opposite signs to guarantee a root
    if f_low == 0:
        return low
    if f_high == 0:
        return high
    if (f_low > 0 and f_high > 0) or (f_low < 0 and f_high < 0):
        return None

    lo, hi = low, high
    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        f_mid = func(mid) - target

        if abs(f_mid) < tol:
            return mid

        # keep the side that brackets the root
        if (f_low > 0 and f_mid > 0) or (f_low < 0 and f_mid < 0):
            lo = mid
            f_low = f_mid
        else:
            hi = mid
            f_high = f_mid

    return (lo + hi) / 2.0


def implied_wacc(
    fcf0: float,
    shares: float,
    years: int,
    growth: float,
    terminal_g: float,
    market_price: float,
    low: float = 0.02,
    high: float = 0.30,
) -> Optional[float]:
    """
    Solve for WACC such that DCF value/share == market_price,
    holding growth and terminal_g fixed.

    Returns None if no solution in [low, high].
    """
    # ensure lower bound respects Gordon condition
    low = max(low, terminal_g + 0.002)

    def f(w):
        return dcf_value_per_share(fcf0, shares, years, growth, w, terminal_g)

    return _bisect_solve(f, low, high, market_price)


def implied_growth(
    fcf0: float,
    shares: float,
    years: int,
    wacc: float,
    terminal_g: float,
    market_price: float,
    low: float = -0.20,
    high: float = 0.30,
) -> Optional[float]:
    """
    Solve for constant annual growth (years 1..N) such that
    DCF value/share == market_price, holding wacc and terminal_g fixed.

    Returns None if no solution in [low, high].
    """
    if wacc <= terminal_g:
        return None

    def f(g):
        return dcf_value_per_share(fcf0, shares, years, g, wacc, terminal_g)

    return _bisect_solve(f, low, high, market_price)

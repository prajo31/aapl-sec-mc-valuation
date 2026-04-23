from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class Params:
    fcf0: float
    shares: float
    years: int = 5
    sims: int = 20000
    seed: int = 42
    growth_mu: float = 0.05
    growth_sigma: float = 0.03
    wacc_mu: float = 0.08
    wacc_sigma: float = 0.01
    terminal_g: float = 0.03


def simulate(p: Params) -> pd.DataFrame:
    rng = np.random.default_rng(int(p.seed))

    sims = int(p.sims)
    years = int(p.years)

    growth = rng.normal(p.growth_mu, p.growth_sigma, sims)
    wacc = rng.normal(p.wacc_mu, p.wacc_sigma, sims)

    growth = np.clip(growth, -0.5, 0.5)
    wacc = np.clip(wacc, 0.001, 0.5)

    fcf = np.zeros((sims, years))
    f = np.full(sims, float(p.fcf0))

    for t in range(years):
        f = f * (1.0 + growth)
        fcf[:, t] = f

    pv_fcfs = np.zeros(sims)
    for t in range(years):
        pv_fcfs += fcf[:, t] / ((1.0 + wacc) ** (t + 1))

    denom = np.where((wacc - p.terminal_g) <= 0.001, 0.001, (wacc - p.terminal_g))
    terminal_value = fcf[:, -1] * (1.0 + p.terminal_g) / denom
    pv_terminal = terminal_value / ((1.0 + wacc) ** years)

    enterprise_value = pv_fcfs + pv_terminal
    value_per_share = enterprise_value / float(p.shares)

    return pd.DataFrame(
        {
            "growth": growth,
            "wacc": wacc,
            "enterprise_value": enterprise_value,
            "value_per_share": value_per_share,
        }
    )


def summarize(series: pd.Series) -> dict:
    return {
        "mean": float(series.mean()),
        "median": float(series.median()),
        "p05": float(series.quantile(0.05)),
        "p25": float(series.quantile(0.25)),
        "p75": float(series.quantile(0.75)),
        "p95": float(series.quantile(0.95)),
        "min": float(series.min()),
        "max": float(series.max()),
    }

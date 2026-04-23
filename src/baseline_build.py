# src/baseline_build.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, List

from .sec_live import latest_value

@dataclass
class Baseline:
    fcf0: float
    shares_outstanding: float
    meta: Dict[str, Any]

def _first_found(
    companyfacts: Dict[str, Any],
    candidates: List[Tuple[str, str, str, Optional[str]]]
) -> Optional[Tuple[float, Dict[str, Any], Tuple[str, str, str, Optional[str]]]]:
    """
    candidates: (taxonomy, tag, unit, fp)
      fp can be:
        "FY" => annual
        "Q"  => quarterly
        None => any (instant/periodic depending on tag)
    """
    for taxonomy, tag, unit, fp in candidates:
        if fp == "FY":
            res = latest_value(companyfacts, taxonomy, tag, unit, fp_exact="FY")
        elif fp == "Q":
            res = latest_value(companyfacts, taxonomy, tag, unit, fp_prefix="Q")
        else:
            res = latest_value(companyfacts, taxonomy, tag, unit)
        if res:
            val, meta = res
            return val, meta, (taxonomy, tag, unit, fp)
    return None

def build_baseline_from_sec(companyfacts: Dict[str, Any]) -> Baseline:
    """
    Builds:
      FCF0 = Operating Cash Flow - CapEx
      Shares outstanding from DEI shares tag
    Uses common US-GAAP tags; companies can vary, so we try multiple candidates.
    """

    # Operating cash flow (common tags)
    ocf_candidates = [
        ("us-gaap", "NetCashProvidedByUsedInOperatingActivities", "USD", "FY"),
        ("us-gaap", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations", "USD", "FY"),
        ("us-gaap", "NetCashProvidedByUsedInOperatingActivities", "USD", "Q"),
        ("us-gaap", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations", "USD", "Q"),
    ]

    # CapEx (common tag)
    capex_candidates = [
        ("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment", "USD", "FY"),
        ("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment", "USD", "Q"),
    ]

    # Shares outstanding: DEI cover-page tag is typical; fallback to us-gaap shares outstanding
    shares_candidates = [
        ("dei", "EntityCommonStockSharesOutstanding", "shares", None),
        ("us-gaap", "CommonStockSharesOutstanding", "shares", None),
    ]

    ocf = _first_found(companyfacts, ocf_candidates)
    capex = _first_found(companyfacts, capex_candidates)
    shares = _first_found(companyfacts, shares_candidates)

    missing = []
    if not ocf: missing.append("Operating cash flow (OCF)")
    if not capex: missing.append("CapEx")
    if not shares: missing.append("Shares outstanding")
    if missing:
        raise ValueError("Missing required SEC facts: " + ", ".join(missing))

    ocf_val, ocf_meta, ocf_src = ocf
    capex_val, capex_meta, capex_src = capex
    shares_val, shares_meta, shares_src = shares

    fcf0 = float(ocf_val - capex_val)

    meta = {
        "ocf": {"value": ocf_val, "source": ocf_src, "meta": ocf_meta},
        "capex": {"value": capex_val, "source": capex_src, "meta": capex_meta},
        "shares": {"value": shares_val, "source": shares_src, "meta": shares_meta},
    }

    return Baseline(fcf0=fcf0, shares_outstanding=float(shares_val), meta=meta)

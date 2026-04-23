# src/sec_live.py
from __future__ import annotations

import requests
from typing import Any, Dict, List, Optional, Tuple

SEC_BASE = "https://data.sec.gov"
AAPL_CIK10 = "0000320193"  # Apple CIK padded to 10 digits

def _sec_get_json(url: str, user_agent: str, timeout: int = 30) -> Dict[str, Any]:
    """
    SEC requires a declared User-Agent for automated access and enforces fair access limits.
    """
    headers = {
        "User-Agent": user_agent,
        "Accept-Encoding": "gzip, deflate",
        "Host": "data.sec.gov",
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json()

def fetch_submissions(cik10: str, user_agent: str) -> Dict[str, Any]:
    """
    Fetches filing history metadata (Submissions endpoint).
    """
    url = f"{SEC_BASE}/submissions/CIK{cik10}.json"
    return _sec_get_json(url, user_agent=user_agent)

def fetch_companyfacts(cik10: str, user_agent: str) -> Dict[str, Any]:
    """
    Fetches all XBRL facts for the company (CompanyFacts endpoint).
    """
    url = f"{SEC_BASE}/api/xbrl/companyfacts/CIK{cik10}.json"
    return _sec_get_json(url, user_agent=user_agent)

def pick_series(companyfacts: Dict[str, Any], taxonomy: str, tag: str, unit: str) -> List[Dict[str, Any]]:
    """
    Returns list of fact points for taxonomy/tag/unit, else [].
    """
    return (
        companyfacts.get("facts", {})
        .get(taxonomy, {})
        .get(tag, {})
        .get("units", {})
        .get(unit, [])
        or []
    )

def latest_value(
    companyfacts: Dict[str, Any],
    taxonomy: str,
    tag: str,
    unit: str,
    fp_exact: Optional[str] = None,
    fp_prefix: Optional[str] = None,
) -> Optional[Tuple[float, Dict[str, Any]]]:
    """
    Returns (value, metadata) for the latest matching fact.
    - fp_exact="FY" => annual
    - fp_prefix="Q" => quarters
    """
    pts = pick_series(companyfacts, taxonomy, tag, unit)
    if fp_exact is not None:
        pts = [p for p in pts if p.get("fp") == fp_exact]
    if fp_prefix is not None:
        pts = [p for p in pts if str(p.get("fp", "")).startswith(fp_prefix)]
    if not pts:
        return None
    latest = max(pts, key=lambda p: p.get("end", ""))
    return float(latest["val"]), latest

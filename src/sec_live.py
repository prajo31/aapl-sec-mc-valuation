from __future__ import annotations

import requests
from typing import Any, Dict, List, Optional, Tuple

# Official SEC Data API host for JSON endpoints [1](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)[2](https://www.sec.gov/about/developer-resources)
SEC_BASE = "https://data.sec.gov"

# Default CIK (Apple). You can pass any other CIK10 into functions below.
DEFAULT_CIK10 = "0000320193"


def _sec_get_json(url: str, user_agent: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Perform a GET request to SEC data APIs with required identity header.

    SEC guidance: declare a User-Agent and respect fair access (rate limits). [3](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
    """
    headers = {
        "User-Agent": user_agent,
        "Accept-Encoding": "gzip, deflate",
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def normalize_cik10(cik: str | int) -> str:
    """
    Normalize a CIK to 10-digit zero-padded string.
    """
    s = str(cik).strip()
    # remove any leading "CIK" prefix if user provides it
    if s.upper().startswith("CIK"):
        s = s[3:].strip()
    # remove leading zeros then pad back
    s = str(int(s)) if s.isdigit() else s
    return s.zfill(10)


def fetch_submissions(cik10: str, user_agent: str) -> Dict[str, Any]:
    """
    Fetch company submissions JSON.

    SEC states the submissions endpoint format as:
    https://data.sec.gov/submissions/CIK##########.json [1](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
    """
    cik10 = normalize_cik10(cik10)
    url = f"{SEC_BASE}/submissions/CIK{cik10}.json"
    return _sec_get_json(url, user_agent=user_agent)


def fetch_companyfacts(cik10: str, user_agent: str) -> Dict[str, Any]:
    """
    Fetch company facts (XBRL facts) JSON.

    CompanyFacts endpoint is part of SEC's XBRL data APIs on data.sec.gov. [1](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)[4](https://dealcharts.org/blog/sec-edgar-api-guide)
    """
    cik10 = normalize_cik10(cik10)
    url = f"{SEC_BASE}/api/xbrl/companyfacts/CIK{cik10}.json"
    return _sec_get_json(url, user_agent=user_agent)


def pick_series(
    companyfacts: Dict[str, Any],
    taxonomy: str,
    tag: str,
    unit: str
) -> List[Dict[str, Any]]:
    """
    Return a list of fact datapoints for taxonomy/tag/unit, or [] if missing.
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
    Get the latest numeric value for a given taxonomy/tag/unit with optional period filters.

    - fp_exact="FY" selects annual points
    - fp_prefix="Q" selects quarterly points (Q1/Q2/Q3/Q4)
    Returns (value, metadata) or None.
    """
    pts = pick_series(companyfacts, taxonomy, tag, unit)

    if fp_exact is not None:
        pts = [p for p in pts if p.get("fp") == fp_exact]

    if fp_prefix is not None:
        pts = [p for p in pts if str(p.get("fp", "")).startswith(fp_prefix)]

    if not pts:
        return None

    latest = max(pts, key=lambda p: p.get("end", ""))

    # some facts are not numeric; guard convert
    val = latest.get("val", None)
    if val is None:
        return None

    return float(val), latest

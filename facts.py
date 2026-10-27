"""Step 4: the latest fiscal year's facts from the XBRL company facts.

Each concept has candidate tags. A filer can move a number between tags across
years, so the reader picks the candidate whose latest annual value is newest
(the tag trap). Ties go to the earlier candidate in the list. Every concept is
read for the fiscal year that ends on the latest 10-K's period date.
"""

from datetime import date

ANNUAL_MIN_DAYS = 350  # a 52- or 53-week year
ANNUAL_MAX_DAYS = 380
PRIOR_YEAR_MIN_GAP_DAYS = 300

# concept -> (kind, candidate tags in order of preference)
CONCEPTS = {
    "total_revenue": ("duration", [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueNet",
    ]),
    "operating_income": ("duration", ["OperatingIncomeLoss"]),
    "net_income": ("duration", [
        "NetIncomeLoss",
        "NetIncomeLossAvailableToCommonStockholdersBasic",
    ]),
    "diluted_eps": ("duration", ["EarningsPerShareDiluted"]),
    "stockholders_equity": ("instant", [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ]),
    "long_term_debt_noncurrent": ("instant", [
        "LongTermDebtNoncurrent",
        "LongTermDebtAndCapitalLeaseObligations",
    ]),
    "long_term_debt_current": ("instant", [
        "LongTermDebtCurrent",
        "LongTermDebtAndCapitalLeaseObligationsCurrent",
    ]),
    "cash_from_operations": ("duration", [
        "NetCashProvidedByUsedInOperatingActivities",
    ]),
    "capex": ("duration", [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ]),
}

PEER_CONCEPTS = ("total_revenue", "operating_income")


def _days(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def _points(gaap: dict, tag: str, kind: str) -> list[dict]:
    """Annual 10-K values for a tag: full-year durations, or year-end instants."""
    if tag not in gaap:
        return []
    out = []
    for unit_values in gaap[tag]["units"].values():
        for p in unit_values:
            if not p.get("form", "").startswith("10-K"):
                continue
            if kind == "duration":
                if "start" not in p or not ANNUAL_MIN_DAYS <= _days(p["start"], p["end"]) <= ANNUAL_MAX_DAYS:
                    continue
            elif "start" in p:
                continue
            out.append(p)
    return out


def _value_at(points: list[dict], end: str, latest_accn: str) -> dict | None:
    """The value for a period end, preferring the latest 10-K's own figure."""
    matches = [p for p in points if p["end"] == end]
    if not matches:
        return None
    own = [p for p in matches if p["accn"] == latest_accn]
    return (own or sorted(matches, key=lambda p: p["filed"]))[-1]


def _prior_end(points: list[dict], fy_end: str) -> str | None:
    ends = {p["end"] for p in points if _days(p["end"], fy_end) >= PRIOR_YEAR_MIN_GAP_DAYS}
    return max(ends) if ends else None


def read_concept(gaap: dict, concept: str, fy_end: str, latest_accn: str) -> dict:
    kind, candidates = CONCEPTS[concept]
    scored = []
    for order, tag in enumerate(candidates):
        points = _points(gaap, tag, kind)
        if points:
            latest = max(p["end"] for p in points)
            scored.append((latest, -order, tag, points))
    if not scored:
        return {"concept": concept, "tag": None, "value": None}
    latest, _, tag, points = max(scored)
    current = _value_at(points, fy_end, latest_accn)
    prior_end = _prior_end(points, fy_end)
    prior = _value_at(points, prior_end, latest_accn) if prior_end else None

    def describe(p):
        if p is None:
            return None
        return {"value": p["val"], "period_end": p["end"], "period_start": p.get("start"),
                "accession": p["accn"], "form": p["form"], "filed": p["filed"]}

    return {
        "concept": concept,
        "tag": tag,
        "tag_latest_period_end": latest,
        "candidates_seen": [s[2] for s in sorted(scored, reverse=True)],
        "current": describe(current),
        "prior": describe(prior),
    }


def read_facts(company_facts: dict, fy_end: str, latest_accn: str,
               concepts=tuple(CONCEPTS)) -> dict:
    gaap = company_facts.get("facts", {}).get("us-gaap", {})
    return {c: read_concept(gaap, c, fy_end, latest_accn) for c in concepts}


def period_problems(facts: dict, fy_end: str) -> list[str]:
    """The step-4 test: every current period end equals the 10-K's fiscal year end."""
    problems = []
    for name, f in facts.items():
        cur = f.get("current")
        if cur is None:
            problems.append(f"{name}: no value for the fiscal year ending {fy_end}")
        elif cur["period_end"] != fy_end:
            problems.append(f"{name}: period end {cur['period_end']} is not {fy_end}")
    return problems

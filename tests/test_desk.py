"""Known-answer tests. The desk's code names no company; the known answers live here.

    .venv/bin/python -m pytest -q
"""

import json
import re
import shutil
from pathlib import Path

import pytest

import calc
import facts as xbrl
import sec
import verify

ROOT = Path(__file__).resolve().parents[1]
COST_RUN = next(ROOT.glob("runs/COST_*"), None)
CODE_FILES = ("desk.py", "sec.py", "facts.py", "calc.py", "roles.py", "verify.py")


def annual(tag_end_vals, form="10-K", accn="A"):
    """Synthetic XBRL points: full fiscal years ending on the given dates."""
    pts = []
    for end, val in tag_end_vals:
        y = int(end[:4])
        pts.append({"start": f"{y - 1}{end[4:]}", "end": end, "val": val,
                    "form": form, "accn": accn, "filed": end, "fy": y, "fp": "FY"})
    return {"units": {"USD": pts}}


# --- Step 4: the tag trap -----------------------------------------------------

def test_tag_trap_picks_the_tag_with_the_newest_year():
    gaap = {
        "Revenues": annual([("2024-09-01", 254), ("2025-08-31", 275)]),
        "RevenueFromContractWithCustomerExcludingAssessedTax": annual([("2025-08-31", 275), ("2026-08-30", 303)]),
    }
    got = xbrl.read_concept(gaap, "total_revenue", "2026-08-30", "A")
    assert got["tag"] == "RevenueFromContractWithCustomerExcludingAssessedTax"
    assert got["current"]["value"] == 303
    assert got["prior"]["value"] == 275


def test_tie_goes_to_total_revenue_tag():
    gaap = {
        "Revenues": annual([("2026-01-31", 713)]),
        "RevenueFromContractWithCustomerExcludingAssessedTax": annual([("2026-01-31", 706)]),
    }
    assert xbrl.read_concept(gaap, "total_revenue", "2026-01-31", "A")["current"]["value"] == 713


def test_period_check_flags_an_old_year():
    gaap = {"Revenues": annual([("2025-08-31", 275)])}
    got = xbrl.read_facts({"facts": {"us-gaap": gaap}}, "2026-08-30", "A", ("total_revenue",))
    assert xbrl.period_problems(got, "2026-08-30")


def test_quarter_points_are_not_read_as_a_year():
    gaap = {"Revenues": {"units": {"USD": [
        {"start": "2026-06-01", "end": "2026-08-30", "val": 95, "form": "10-K", "accn": "A", "filed": "x"}]}}}
    assert xbrl.read_concept(gaap, "total_revenue", "2026-08-30", "A")["tag"] is None


# --- Step 2: the earnings 8-K is the newest one that reports Item 2.02 ----------

def test_newer_8k_without_item_202_is_skipped():
    rows = [("8-K", "5.02,9.01", "n1"), ("8-K", "8.01,9.01", "n2"), ("10-K", "", "k"),
            ("8-K", "2.02,9.01", "e"), ("10-Q", "", "q")]
    subs = {"filings": {"recent": {
        "form": [r[0] for r in rows], "items": [r[1] for r in rows],
        "accessionNumber": [r[2] for r in rows]}}}
    picked = sec.latest_filings(subs)
    assert picked["8-K"]["accessionNumber"] == "e"
    assert picked["10-K"]["accessionNumber"] == "k"


# --- Step 5: the calculator on the audit's definitions ---------------------------

def _fact(cur, prior=None):
    return {"current": {"value": cur}, "prior": None if prior is None else {"value": prior}}


def test_ratio_definitions_match_the_audit():
    f = {"total_revenue": _fact(303_154e6, 275_235e6), "operating_income": _fact(11_685e6),
         "net_income": _fact(9_226e6), "stockholders_equity": _fact(35_803e6, 29_164e6),
         "long_term_debt_noncurrent": _fact(3_914e6), "long_term_debt_current": _fact(2_248e6),
         "cash_from_operations": _fact(15_817e6), "capex": _fact(6_435e6), "diluted_eps": _fact(20.76)}
    r = {x["name"]: x["value"] for x in calc.core_ratios(f, 992.13)}
    assert r["return_on_average_equity"] == pytest.approx(9_226 / ((35_803 + 29_164) / 2))
    assert r["debt_to_equity"] == pytest.approx((3_914 + 2_248) / 35_803)  # current portion included
    assert r["operating_margin"] == pytest.approx(11_685 / 303_154)  # on total revenue
    assert r["free_cash_flow"] == pytest.approx(9_382e6)
    assert r["pe_ratio"] == pytest.approx(992.13 / 20.76)


def test_calculator_runs_arithmetic_only():
    assert calc.evaluate("(95,723 / 86,156) - 1") == pytest.approx(0.111043, rel=1e-5)
    with pytest.raises(ValueError):
        calc.evaluate("__import__('os')")


# --- The known answer: the saved Costco run ----------------------------------------

@pytest.mark.skipif(COST_RUN is None, reason="no saved Costco run")
def test_costco_known_answer():
    run = json.loads((COST_RUN / "facts.json").read_text())
    f = run["fiscal_year"]["facts"]
    assert run["filings"]["10-K"]["accession"] == "0000909832-26-000093"
    assert run["filings"]["8-K"]["items"].startswith("2.02")
    assert run["fiscal_year"]["period_problems"] == []
    assert f["total_revenue"]["current"]["value"] == 303_154_000_000
    assert f["operating_income"]["current"]["value"] == 11_685_000_000
    assert f["net_income"]["current"]["value"] == 9_226_000_000
    assert f["diluted_eps"]["current"]["value"] == 20.76


@pytest.mark.skipif(COST_RUN is None, reason="no saved Costco run")
def test_verifier_catches_a_wrong_number(tmp_path):
    folder = tmp_path / "run"
    shutil.copytree(COST_RUN, folder)
    roles = json.loads((folder / "roles.json").read_text())
    assert all(r["status"] == "OK" for r in verify.verify(folder))
    for c in roles["financial_analyst"]["core_claims"]:
        if c["id"] == 5:
            c["value"] = "$20.67"  # a plausible wrong EPS
    (folder / "roles.json").write_text(json.dumps(roles))
    bad = [r for r in verify.verify(folder) if r["status"] != "OK"]
    assert [r["id"] for r in bad] == [5]


# --- Ownership: nothing in the code names a company ------------------------------

def test_no_company_named_in_code():
    names = re.compile(r"(?i:costco|walmart|target corp|coca-cola|pepsico)|\b(COST|WMT|TGT|BJ|KO)\b")
    for name in CODE_FILES:
        assert not names.search((ROOT / name).read_text()), name


def test_saved_reports_end_with_the_three_required_lines():
    for report in ROOT.glob("runs/*/report.md"):
        tail = report.read_text(encoding="utf-8").rstrip().splitlines()[-3:]
        assert tail[0].startswith("*Disclaimer:"), report
        assert tail[1].startswith("*AI tools used:"), report
        assert tail[2] == "*Any remaining errors are my own.*", report

"""Check a saved report's core claims against the filings the desk read.

    python verify.py runs/TICKER_2026-10-27_120000
    python verify.py runs/TICKER_2026-10-27_120000 --audit audits/TICKER-audit.md

For each of the eleven core claims, every number the report states must either
appear in the saved filing texts or be the result of arithmetic the report
shows, and that arithmetic must hold. This is a code check, not the audit: the
marks in audits/ are still made by hand.
"""

import json
import re
import sys
from pathlib import Path

import calc

TEXT_FILES = ("10-K.txt", "10-Q.txt", "release-ex99-1.txt")
NUMBER = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")
EQUATION = re.compile(r"([\d,.\s()+\-*/]+?)\s*=\s*(-?\d[\d,]*(?:\.\d+)?)\s*(%|x)?")
RELATIVE_TOLERANCE = 0.006  # rounding to what the report shows
YEAR_RANGE = range(1990, 2100)


def norm(token: str) -> str:
    return token.replace(",", "").rstrip(".")


def numbers(text: str) -> set[str]:
    return {norm(n) for n in NUMBER.findall(text)}


def filing_numbers(folder: Path) -> set[str]:
    found = set()
    for name in TEXT_FILES:
        path = folder / name
        if path.exists():
            found |= numbers(path.read_text(encoding="utf-8"))
    return found


def check_arithmetic(text: str) -> tuple[list[float], list[str]]:
    """Every 'expression = result' in the text, recomputed. Returns the values
    that hold (as a fraction and as a percent) and the equations that do not."""
    text = re.sub(r"=\s*-?\d[\d,]*(?:\.\d+)?\s*\)", ")", text)  # (a + b) / 2 = avg) -> (a + b) / 2)
    held, broken = [], []
    for expr, result, unit in EQUATION.findall(text):
        expr = expr.strip()
        if not re.search(r"\d\s*[+\-*/]\s*[\d(]", expr):
            continue
        try:
            value = calc.evaluate(expr)
        except (ValueError, SyntaxError, ZeroDivisionError):
            continue
        shown = float(norm(result))
        if any(close(v, shown) for v in (value, value * 100)):
            held += [value, value * 100]
        else:
            broken.append(f"{expr} = {result}{unit} (recomputed {value:,.4f})")
    return held, broken


def close(a: float, b: float) -> bool:
    return abs(a - b) <= max(abs(b) * RELATIVE_TOLERANCE, 0.006)


RELEASE_CLAIMS = {9, 10, 11}
CLAIM_CONCEPT = {1: "total_revenue", 3: "operating_income", 4: "net_income", 5: "diluted_eps"}
CLAIM_WORD = {5: "diluted", 11: "diluted"}
SMALLEST_TRACED = 100  # integers below this are percents and counts, found everywhere


def _pattern(number: str) -> re.Pattern:
    shown = f"{float(number):,.2f}" if "." in number else f"{int(number):,}"
    return re.compile(r"(?<![\d.,])" + re.escape(shown) + r"(?![\d,]|\.\d)")


def evidence(folder: Path, claim_id: int, stated: set[str]) -> str | None:
    """The filing line that holds the most of the claim's numbers: the release
    first for the quarter's claims, the 10-K first for the rest; then the shortest."""
    traced = [n for n in stated if "." in n or int(n) >= SMALLEST_TRACED]
    if not traced:
        return None
    patterns = [_pattern(n) for n in traced]
    order = (("release-ex99-1.txt", "10-K.txt") if claim_id in RELEASE_CLAIMS
             else ("10-K.txt", "release-ex99-1.txt"))
    best = None
    for rank, name in enumerate(order):
        path = folder / name
        if not path.exists():
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            hits = sum(bool(p.search(line)) for p in patterns)
            if hits:
                word = CLAIM_WORD.get(claim_id, "")
                key = (-hits, -(word in line.lower()), rank, len(line))
                if best is None or key < best[0]:
                    best = (key, name, i, line.strip())
    return None if best is None else f'{best[1]}:{best[2]} "{best[3][:140]}"'


def verify(folder: Path) -> list[dict]:
    roles = json.loads((folder / "roles.json").read_text(encoding="utf-8"))
    run = json.loads((folder / "facts.json").read_text(encoding="utf-8"))
    in_filings = filing_numbers(folder)
    code_ratios = " ".join(r["arithmetic"] for r in run["ratios"])
    rows = []
    for claim in sorted(roles["financial_analyst"]["core_claims"], key=lambda c: c["id"]):
        held, broken = check_arithmetic(claim.get("arithmetic", "") + " " + code_ratios)
        stated = {n for n in numbers(claim["value"]) if not (n.isdigit() and int(n) in YEAR_RANGE)}
        unsupported = sorted(n for n in stated
                             if n not in in_filings and not any(close(h, float(n)) for h in held))
        status = "OK" if not unsupported and not broken else "CHECK"
        prior = (run["fiscal_year"]["facts"].get(CLAIM_CONCEPT.get(claim["id"], ""), {}) or {}).get("prior")
        anchors = set(stated & in_filings)
        if prior:  # the statement row also holds the prior year
            v = prior["value"]
            anchors.add(norm(f"{v:.2f}") if abs(v) < 1000 else str(round(v / 1e6)))
        found = evidence(folder, claim["id"], anchors)
        lines = [found] if found else []
        rows.append({"id": claim["id"], "claim": claim["claim"], "value": claim["value"],
                     "status": status, "not_found": unsupported, "arithmetic_broken": broken,
                     "evidence": lines, "arithmetic": claim.get("arithmetic", "")})
    return rows


PARTS = ("Overview", "Market Positioning and Growth Outlook", "Valuation Insights",
         "Future Developments and Strategic Recommendations", "Investment Recommendation")


def extra_rows(folder: Path) -> list[str]:
    """P/E, each peer's margin, the template and the recommendation."""
    run = json.loads((folder / "facts.json").read_text(encoding="utf-8"))
    roles = json.loads((folder / "roles.json").read_text(encoding="utf-8"))
    report = (folder / "report.md").read_text(encoding="utf-8")
    rows = []
    for r in run["ratios"]:
        if r["name"] == "pe_ratio":
            pe = f"{r['value']:.1f}x"
            ok = "Correct" if pe in report else "Check: not stated as computed"
            rows.append(f"| P/E | price {run['price']['value']} ({run['price']['date']}) / diluted EPS | {pe} | "
                        f"computed: {cell(r['arithmetic'])} | {ok} |  |")
    for peer in run["peers"]:
        m = peer["operating_margin"]
        if not m:
            continue
        shown = f"{m['value']:.2%}"
        ok = "Correct" if shown in report else "Check: margin not in report as computed"
        rows.append(f"| Peer {peer['ticker']} | operating margin, FY ending {peer['fiscal_year_end']} | {shown} | "
                    f"10-K {peer['accession']}, tag {peer['facts']['total_revenue']['tag']}: "
                    f"{cell(m['arithmetic'])} | {ok} |  |")
    present = [p for p in PARTS if f"## " in report and p in report]
    rows.append(f"| Template | five parts present | {len(present)} of 5 | — | "
                f"{'Correct' if len(present) == 5 else 'Check: missing ' + ', '.join(set(PARTS) - set(present))} |  |")
    adv = roles["investment_advisor"]
    rows.append(f"| Recommendation | rating names a number the report states | {adv['rating']} on "
                f"{cell(adv['deciding_number'])[:60]} | — | "
                f"{'Correct' if adv['rating'] in ('Buy', 'Hold', 'Sell') else 'Check'} |  |")
    return rows


def cell(text: str) -> str:
    return text.replace("|", "/").replace("\n", " ")


def write_audit(folder: Path, rows: list[dict], out: Path) -> None:
    first_line = (folder / "report.md").read_text(encoding="utf-8").splitlines()[0]
    table = ["| # | Claim | Report said | Where in the filing | Agent check | Your mark |",
             "|---|---|---|---|---|---|"]
    for r in rows:
        where = "<br>".join(cell(e) for e in r["evidence"]) or "computed"
        if r["arithmetic"]:
            where += f"<br>arithmetic: {cell(r['arithmetic'])[:160]}"
        check = "Correct" if r["status"] == "OK" else "Check: " + cell(
            "; ".join(r["not_found"] + r["arithmetic_broken"]))
        table.append(f"| {r['id']} | {cell(r['claim'].split('(')[0].strip())[:60]} | "
                     f"{cell(r['value'])[:80]} | {where} | {check} |  |")
    table += extra_rows(folder)
    bad = sum(r["status"] != "OK" for r in rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"""# Report audit: {folder.name}

Report: `{folder}/report.md`
{first_line}
Checklist: https://cinderzhang.github.io/FIN67110-Fall2026/reference/audit-checklist.html

The **Agent check** column is written by `verify.py`: every number traced to a line of
the saved filings, every ratio recomputed. **Your mark** is the human sign-off: open the
line, confirm, write Correct / Wrong / Unsupported / Missing.

**Agent check:** {len(rows) - bad} of {len(rows)} core claims trace to the filings. Errors flagged: {bad}. Missing: {11 - len(rows)}.
**Human sign-off (errors / missing):** _ / _

{chr(10).join(table)}
""", encoding="utf-8")


def main() -> int:
    args = sys.argv[1:]
    if len(args) not in (1, 3) or (len(args) == 3 and args[1] != "--audit"):
        print(__doc__)
        return 2
    folder = Path(args[0])
    rows = verify(folder)
    if len(args) == 3:
        write_audit(folder, rows, Path(args[2]))
    for r in rows:
        line = f"{r['id']:>2} {r['status']:5} {r['value'][:70]}"
        if r["not_found"]:
            line += f"  | not in filings or arithmetic: {', '.join(r['not_found'])}"
        for b in r["arithmetic_broken"]:
            line += f"  | arithmetic fails: {b}"
        print(line)
    bad = sum(r["status"] != "OK" for r in rows)
    print(f"\n{len(rows) - bad}/{len(rows)} core claims trace to the filings or to arithmetic that holds.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

"""The desk: a ticker in, the filings, the facts and the ratios out, then the
four roles of Francis & Zhang (2026) write a five-part report.

    python desk.py TICKER --peers P1,P2 --price 123.45
    python desk.py TICKER --step 4        # one step only
    python desk.py TICKER --no-roles      # Lab 02: the seven steps, no model

Nothing in this code names a company. The ticker is an argument.
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import calc
import facts as xbrl
import sec

RUNS_DIR = Path(__file__).with_name("runs")
RELEASE_LINES_PER_KIND = 4


def banner(n: int, title: str) -> None:
    print(f"\n== Step {n}: {title} " + "=" * max(0, 60 - len(title)))


def fmt(v) -> str:
    if v is None:
        return "n/a"
    return f"{v:,.2f}" if abs(v) < 1000 else f"{v / 1e6:,.0f}M"


def step1(ticker: str) -> dict:
    banner(1, "ticker to CIK")
    cik, name = sec.ticker_to_cik(ticker)
    print(f"{ticker.upper()} -> CIK {cik} ({name})")
    return {"ticker": ticker.upper(), "cik": cik, "name": name}


def step2(co: dict) -> dict:
    banner(2, "latest 10-K, 10-Q and earnings 8-K (Item 2.02)")
    picked = sec.latest_filings(sec.submissions(co["cik"]))
    out = {}
    for form in ("10-K", "10-Q", "8-K"):
        row = picked[form]
        index = sec.read_index(co["cik"], row["accessionNumber"])
        out[form] = {
            "form": form,
            "accession": row["accessionNumber"],
            "filing_date": row["filingDate"],
            "period": row["reportDate"],
            "items": row.get("items", ""),
            "accepted": index["accepted"],
            "index_url": sec.index_url(co["cik"], row["accessionNumber"]),
            "document_url": sec.document_url(co["cik"], row, index),
        }
        f = out[form]
        extra = f" items {f['items']}" if form == "8-K" else f" period {f['period']}"
        print(f"{form:5} {f['accession']}  Accepted {f['accepted']}{extra}")
    return out


def step3(co: dict, filings: dict, folder: Path) -> dict:
    banner(3, "download the documents as plain text")
    names = {"10-K": "10-K.txt", "10-Q": "10-Q.txt", "8-K": "release-ex99-1.txt"}
    texts = {}
    for form, name in names.items():
        text = sec.html_to_text(sec.get(filings[form]["document_url"]).text)
        (folder / name).write_text(text, encoding="utf-8")
        texts[form] = text
        print(f"{form:5} -> {folder / name}  ({len(text):,} characters)")
    return texts


def step4(co: dict, filings: dict) -> dict:
    banner(4, "XBRL facts for the latest fiscal year")
    fy_end = filings["10-K"]["period"]
    raw = sec.company_facts(co["cik"])
    facts = xbrl.read_facts(raw, fy_end, filings["10-K"]["accession"])
    print(f"Fiscal year end (10-K period): {fy_end}")
    for name, f in facts.items():
        cur, pri = f.get("current"), f.get("prior")
        print(f"{name:26} {fmt(cur and cur['value']):>12}  prior {fmt(pri and pri['value']):>12}"
              f"  tag {f['tag']}  end {cur and cur['period_end']}  filing {cur and cur['accession']}")
    problems = xbrl.period_problems(facts, fy_end)
    for p in problems:
        print(f"CHECK FAILED: {p}")
    if not problems:
        print(f"CHECK OK: every period end equals {fy_end}")
    return {"fiscal_year_end": fy_end, "facts": facts, "period_problems": problems}


def step5(facts: dict, price: float | None) -> list[dict]:
    banner(5, "the calculator")
    ratios = calc.core_ratios(facts, price)
    for r in ratios:
        print(f"{r['name']:26} {r['arithmetic']}")
    if price is None:
        print("pe_ratio                   n/a (no --price given)")
    return ratios


def step6(release_text: str) -> dict:
    banner(6, "the quarter from the earnings release")
    lines = release_text.splitlines()
    revenue_words = re.compile(r"\b(total revenues?|net revenues?|revenues?|net sales)\b", re.I)
    has_number = re.compile(r"\$|\d{1,3}(,\d{3})+|\d+\.\d+")
    revenue = [l for l in lines if revenue_words.search(l) and has_number.search(l)]
    eps = [l for l in lines if re.search(r"diluted", l, re.I) and has_number.search(l)
           and re.search(r"share|EPS", l, re.I)]
    out = {"revenue_lines": revenue[:RELEASE_LINES_PER_KIND], "eps_lines": eps[:RELEASE_LINES_PER_KIND]}
    for l in out["revenue_lines"]:
        print(f"revenue: {l[:220]}")
    for l in out["eps_lines"]:
        print(f"eps:     {l[:220]}")
    return out


def step7(peers: list[str]) -> list[dict]:
    banner(7, "peers, operating margin on the same definition")
    out = []
    for ticker in peers:
        cik, name = sec.ticker_to_cik(ticker)
        tenk = sec.latest_filings(sec.submissions(cik))["10-K"]
        facts = xbrl.read_facts(sec.company_facts(cik), tenk["reportDate"],
                                tenk["accessionNumber"], xbrl.PEER_CONCEPTS)
        margin = calc.peer_margin(facts)
        rev = facts["total_revenue"]
        print(f"{ticker.upper():6} FY end {tenk['reportDate']}  10-K {tenk['accessionNumber']}  "
              f"revenue tag {rev['tag']}  margin {margin['arithmetic'] if margin else 'n/a'}")
        out.append({"ticker": ticker.upper(), "cik": cik, "name": name,
                    "fiscal_year_end": tenk["reportDate"], "accession": tenk["accessionNumber"],
                    "facts": facts, "operating_margin": margin})
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ticker")
    parser.add_argument("--peers", default="", help="comma-separated tickers")
    parser.add_argument("--price", type=float, help="last close before the release")
    parser.add_argument("--price-date", default="", help="the date of that close")
    parser.add_argument("--step", type=int, choices=range(1, 8), help="run one step only")
    parser.add_argument("--no-roles", action="store_true", help="stop after the seven steps")
    args = parser.parse_args()
    peers = [p.strip() for p in args.peers.split(",") if p.strip()]

    started = datetime.now()
    co = step1(args.ticker)
    if args.step == 1:
        return
    if args.step == 7:
        step7(peers)
        return
    filings = step2(co)
    if args.step == 2:
        return
    folder = RUNS_DIR / f"{co['ticker']}_{started:%Y-%m-%d_%H%M%S}"
    folder.mkdir(parents=True, exist_ok=True)
    texts = step3(co, filings, folder) if args.step in (None, 3, 6) else {}
    if args.step == 3:
        return
    fy = step4(co, filings) if args.step in (None, 4, 5) else None
    if args.step == 4:
        return
    ratios = step5(fy["facts"], args.price) if fy else []
    if args.step == 5:
        return
    quarter = step6(texts["8-K"])
    if args.step == 6:
        return
    peer_rows = step7(peers)

    run = {"company": co, "run_started": started.isoformat(timespec="seconds"),
           "price": {"value": args.price, "date": args.price_date or None},
           "filings": filings, "fiscal_year": fy, "ratios": ratios,
           "quarter_release_lines": quarter, "peers": peer_rows}
    (folder / "facts.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
    print(f"\nSaved: {folder}")

    if args.no_roles:
        return
    import roles  # the model side needs API_KEY; the steps above do not
    report_path = roles.run_desk(run, texts, folder)
    print(f"\nReport: {report_path}")


if __name__ == "__main__":
    main()

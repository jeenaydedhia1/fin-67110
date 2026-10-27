"""The four roles of Francis & Zhang (2026), Figure 1, on top of the seven steps.

Each role is a separate model call with its own instructions. It receives only
what the Strategy Manager sends it: JSON with the task, the context and the
expected output. The Manager is code, not a model: a checklist that checks the
five parts, sends a failing part back to its role once, then compiles.

Nothing here names a company.
"""

import json
import os
import re
from pathlib import Path

import anthropic
from dotenv import load_dotenv

import calc

load_dotenv(Path(__file__).with_name(".env"))

MODEL = os.environ.get("MODEL", "claude-sonnet-5-5")
MAX_TOKENS = 8000
MAX_TOOL_TURNS = 12
SECTION_CHAR_LIMIT = 60_000
PARTS = (
    "Overview",
    "Market Positioning and Growth Outlook",
    "Valuation Insights",
    "Future Developments and Strategic Recommendations",
    "Investment Recommendation",
)
# The course requires these three lines at the end of anything public.
REQUIRED_LINES = (
    "*Disclaimer: written for FIN 67110 coursework. This is not investment advice.*",
    f"*AI tools used: Claude Code (Anthropic) to build and check the desk; {MODEL} for the four roles.*",
    "*Any remaining errors are my own.*",
)
CORE_CLAIMS = {
    1: "Total revenue, latest fiscal year",
    2: "Revenue growth versus the prior year",
    3: "Operating income and operating margin",
    4: "Net income attributable to the company",
    5: "Diluted earnings per share, GAAP",
    6: "Return on average equity",
    7: "Debt to equity (long-term debt including current portion)",
    8: "Free cash flow (cash from operations - additions to property and equipment)",
    9: "The latest quarter's total revenue (earnings release)",
    10: "The quarter's revenue growth versus the same quarter last year",
    11: "The quarter's GAAP diluted EPS (earnings release)",
}
RATINGS = ("Buy", "Hold", "Sell")

_client = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        key = os.environ.get("API_KEY", "")
        if not key or key == "paste-here":
            raise SystemExit("API_KEY is missing from .env.")
        _client = anthropic.Anthropic(api_key=key)
    return _client


# --- Role instructions --------------------------------------------------------

RESEARCH_ANALYST = """You are the Research Analyst on an equity research desk.
You read filings: the 10-K's Business section (Item 1), its MD&A (Item 7), and the latest earnings release (8-K Exhibit 99.1).
Write about the business model, competitive position, catalysts and recent developments.
Rules:
- Every factual claim quotes its line from the filing in double quotes and names the source in brackets, e.g. [10-K Item 7] or [Release].
- Use only the context you are sent. If the filings do not say something, do not say it.
- Do not compute ratios. Numbers you state must appear word for word in the quoted line.
Submit with the submit tool."""

FINANCIAL_ANALYST = """You are the Financial Analyst on an equity research desk.
You receive the XBRL facts (each with its tag, period end and accession number), ratios already computed in code with their arithmetic, the earnings release's quarter lines and text, and peers' facts.
Rules:
- Never compute in your head. Every ratio you state is either one given to you (copy its arithmetic) or the result of the calculator tool (show the expression you sent).
- Every number carries its source: the filing (form and accession number) and the XBRL tag and period end, or the release line quoted word for word.
- Where a filing offers two definitions (total revenue vs net sales; gross margin on net sales vs on total revenue), state which one you use. Total revenue means the revenue tag given to you.
- Diluted EPS means GAAP diluted EPS. Never substitute an adjusted or non-GAAP figure.
- Fill all eleven core claims. If the context truly lacks one, give value "not in filings" and say why.
- Peers: name each peer's fiscal year end and compare operating margins only on the same definition (operating income / total revenue).
Submit with the submit tool."""

INVESTMENT_ADVISOR = """You are the Investment Advisor on an equity research desk.
You receive only the Research Analyst's and the Financial Analyst's outputs. Use nothing else.
Write a thesis and a rating of Buy, Hold or Sell, and name the one number that decides it.
Rules:
- Every number you use must appear in the two outputs you were given, written the same way. Do not compute new numbers.
- The deciding number must be one of the Financial Analyst's core claims or ratios.
- Also write the strategic recommendations: what an investor should watch, tied to the catalysts the Research Analyst found.
Submit with the submit tool."""


# --- Tools --------------------------------------------------------------------

def submit_tool(properties: dict, required: list[str]) -> dict:
    return {"name": "submit", "description": "Submit your finished output.",
            "input_schema": {"type": "object", "properties": properties, "required": required}}


MD = {"type": "string", "description": "Markdown"}

RA_SUBMIT = submit_tool({
    "overview": MD,
    "market_positioning_and_growth_outlook": MD,
    "future_developments": MD,
}, ["overview", "market_positioning_and_growth_outlook", "future_developments"])

FA_SUBMIT = submit_tool({
    "core_claims": {"type": "array", "items": {"type": "object", "properties": {
        "id": {"type": "integer"}, "claim": {"type": "string"},
        "value": {"type": "string"}, "source": {"type": "string"},
        "arithmetic": {"type": "string", "description": "for computed claims; else empty"},
    }, "required": ["id", "claim", "value", "source", "arithmetic"]}},
    "peer_table": {"type": "string", "description": "Markdown table: peer, fiscal year end, total revenue, operating income, operating margin, source"},
    "valuation_narrative": MD,
}, ["core_claims", "peer_table", "valuation_narrative"])

ADVISOR_SUBMIT = submit_tool({
    "rating": {"type": "string", "enum": list(RATINGS)},
    "deciding_number": {"type": "string", "description": "the number, exactly as the Financial Analyst wrote it, and what it is"},
    "thesis": MD,
    "strategic_recommendations": MD,
}, ["rating", "deciding_number", "thesis", "strategic_recommendations"])

CALCULATOR = {
    "name": "calculator",
    "description": "Evaluate arithmetic on numbers from the filings: + - * / and parentheses only.",
    "input_schema": {"type": "object", "properties": {"expression": {"type": "string"}},
                     "required": ["expression"]},
}


def call_role(name: str, system: str, message: dict, submit: dict, tools=()) -> dict:
    """One role, one conversation. Loops only for calculator calls."""
    print(f"-- {name}")
    messages = [{"role": "user", "content": json.dumps(message, indent=1)}]
    all_tools = [*tools, submit]
    for _ in range(MAX_TOOL_TURNS):
        response = client().messages.create(
            model=MODEL, max_tokens=MAX_TOKENS, system=system, tools=all_tools,
            tool_choice={"type": "auto"}, messages=messages)
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            if block.name == "submit":
                return block.input
            try:
                answer = str(calc.evaluate(block.input["expression"]))
            except (ValueError, SyntaxError, ZeroDivisionError) as err:
                answer = f"error: {err}"
            print(f"   calculator: {block.input['expression']} = {answer}")
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": answer})
        if not results:
            results = [{"type": "text", "text": "Submit your output with the submit tool."}]
        messages.append({"role": "user", "content": results})
    raise RuntimeError(f"{name} did not submit within {MAX_TOOL_TURNS} turns.")


# --- What the Manager sends ---------------------------------------------------

def section(text: str, start: str, end: str) -> str:
    """The longest stretch between a heading like 'Item 7' and the next item.
    The table of contents holds the same headings, so the shortest hits are skipped."""
    best = ""
    for m in re.finditer(start, text, re.I | re.M):
        e = re.search(end, text[m.end():], re.I | re.M)
        chunk = text[m.start(): m.end() + e.start()] if e else text[m.start():]
        if len(chunk) > len(best):
            best = chunk
    return best[:SECTION_CHAR_LIMIT]


def task(t: str, context: dict, expected: str) -> dict:
    return {"task": t, "context": context, "expected_output": expected}


def ra_message(run: dict, texts: dict) -> dict:
    co = run["company"]
    return task(
        "Describe the business model, competitive position, catalysts and recent developments.",
        {"company": co["name"], "ticker": co["ticker"],
         "filings": {k: v["accession"] for k, v in run["filings"].items()},
         "10-K Item 1 Business": section(texts["10-K"], r"^item\s*1\W*business", r"^item\s*1a\b"),
         "10-K Item 7 MD&A": section(texts["10-K"], r"^item\s*7\W*management", r"^item\s*7a\b"),
         "earnings release": texts["8-K"][:SECTION_CHAR_LIMIT]},
        "Three Markdown parts: Overview; Market Positioning and Growth Outlook; Future Developments. "
        "Every claim quotes its line and names its source.")


def fa_message(run: dict, texts: dict) -> dict:
    co = run["company"]
    return task(
        "Write the statement analysis: growth, margins, returns, leverage, cash flow, the latest "
        "quarter, valuation on the given price, and the peer comparison. Fill the eleven core claims.",
        {"company": co["name"], "ticker": co["ticker"],
         "filings": run["filings"], "fiscal_year": run["fiscal_year"],
         "ratios_computed_in_code": run["ratios"], "price": run["price"],
         "quarter_release_lines": run["quarter_release_lines"],
         "earnings release text": texts["8-K"][:SECTION_CHAR_LIMIT],
         "peers": run["peers"], "core_claims_to_fill": CORE_CLAIMS},
        "core_claims (ids 1-11, each with value, source and arithmetic), a peer table, and a "
        "valuation narrative in Markdown. Every number with its source.")


def advisor_message(ra: dict, fa: dict) -> dict:
    return task(
        "Write the investment thesis and a rating of Buy, Hold or Sell, with the one number that "
        "decides it, and the strategic recommendations.",
        {"research_analyst": ra, "financial_analyst": fa},
        "rating, deciding_number, thesis and strategic_recommendations in Markdown.")


# --- The Manager's checklist --------------------------------------------------

NUMBER = re.compile(r"\d[\d,]*\.?\d*")


def _numbers(text: str) -> set[str]:
    return {n.replace(",", "").rstrip(".") for n in NUMBER.findall(text) if len(n.strip(".,")) > 1}


def check_ra(ra: dict) -> list[str]:
    return [f"{k} is empty" for k in RA_SUBMIT["input_schema"]["required"] if not ra.get(k, "").strip()]


def check_fa(fa: dict) -> list[str]:
    problems = []
    ids = {c.get("id") for c in fa.get("core_claims", [])}
    for i in CORE_CLAIMS:
        if i not in ids:
            problems.append(f"core claim {i} ({CORE_CLAIMS[i]}) is missing")
    for c in fa.get("core_claims", []):
        if not c.get("source", "").strip():
            problems.append(f"core claim {c.get('id')} has no source")
        if re.search(r"adjusted|non-gaap", c.get("value", ""), re.I) and c.get("id") in (5, 11):
            problems.append(f"core claim {c['id']} must be GAAP diluted EPS")
    if not fa.get("peer_table", "").strip():
        problems.append("peer table is empty")
    return problems


def check_advisor(adv: dict, ra: dict, fa: dict) -> list[str]:
    problems = []
    if adv.get("rating") not in RATINGS:
        problems.append("rating must be Buy, Hold or Sell")
    upstream = _numbers(json.dumps(ra) + json.dumps(fa))
    decider = _numbers(adv.get("deciding_number", ""))
    if not decider or not decider <= upstream:
        problems.append("the deciding number does not appear in the Financial Analyst's output")
    stray = _numbers(adv.get("thesis", "")) - upstream
    if stray:
        problems.append("the thesis uses numbers the analysts did not state: " + ", ".join(sorted(stray)))
    return problems


def with_retry(name, system, build, submit, check, tools=()) -> dict:
    """The Manager sends a failing part back to its role once, then accepts it."""
    message = build()
    out = call_role(name, system, message, submit, tools)
    problems = check(out)
    if problems:
        print(f"   Manager: sending back once: {'; '.join(problems)}")
        message = {**message, "manager_feedback": problems, "your_previous_output": out}
        out = call_role(name, system, message, submit, tools)
        for p in check(out):
            print(f"   Manager: still open after one return: {p}")
            out.setdefault("_manager_notes", []).append(p)
    return out


# --- The report ---------------------------------------------------------------

def claims_table(fa: dict) -> str:
    rows = ["| # | Claim | Value | Source | Arithmetic |", "|---|---|---|---|---|"]
    for c in sorted(fa.get("core_claims", []), key=lambda c: c.get("id", 0)):
        cells = (str(c.get("id")), c.get("claim", ""), c.get("value", ""),
                 c.get("source", ""), c.get("arithmetic", ""))
        rows.append("| " + " | ".join(x.replace("|", "/").replace("\n", " ") for x in cells) + " |")
    return "\n".join(rows)


def demote(markdown: str) -> str:
    """A role's own headings sit under the five part headings."""
    return re.sub(r"^#{1,3} ", "#### ", markdown, flags=re.M)


def compile_report(run: dict, ra: dict, fa: dict, adv: dict) -> str:
    ra, adv = ({k: demote(v) if isinstance(v, str) else v for k, v in d.items()} for d in (ra, adv))
    fa = {**fa, "valuation_narrative": demote(fa["valuation_narrative"])}
    co, f = run["company"], run["filings"]
    first = (f"Filings read: {co['name']} ({co['ticker']}), 10-K {f['10-K']['accession']}, "
             f"10-Q {f['10-Q']['accession']}, 8-K earnings release (Ex. 99.1) {f['8-K']['accession']}; "
             f"XBRL company facts CIK {co['cik']}")
    second = f"Run time: {run['run_started']} · model {MODEL} · price {run['price']['value']} {run['price']['date'] or ''}".rstrip()
    notes = [n for part in (ra, fa, adv) for n in part.get("_manager_notes", [])]
    body = [
        first, second, "",
        f"# {co['name']} ({co['ticker']}) — Equity Research Report", "",
        f"## 1. {PARTS[0]}", ra["overview"], "",
        f"## 2. {PARTS[1]}", ra["market_positioning_and_growth_outlook"], "",
        f"## 3. {PARTS[2]}", "### Core claims", claims_table(fa), "",
        "### Peers", fa["peer_table"], "", fa["valuation_narrative"], "",
        f"## 4. {PARTS[3]}", ra["future_developments"], "", adv["strategic_recommendations"], "",
        f"## 5. {PARTS[4]}", f"**Rating: {adv['rating']}**", "",
        f"**Deciding number:** {adv['deciding_number']}", "", adv["thesis"], "",
    ]
    if notes:
        body += ["---", "Manager notes (checks still failing after one return):",
                 *[f"- {n}" for n in notes]]
    body += ["", "---", *REQUIRED_LINES]
    return "\n".join(body)


def run_desk(run: dict, texts: dict, folder: Path) -> Path:
    print("\n== The four roles " + "=" * 47)
    print("-- Strategy Manager: sending tasks")
    ra = with_retry("Research Analyst", RESEARCH_ANALYST, lambda: ra_message(run, texts),
                    RA_SUBMIT, check_ra)
    fa = with_retry("Financial Analyst", FINANCIAL_ANALYST, lambda: fa_message(run, texts),
                    FA_SUBMIT, check_fa, tools=(CALCULATOR,))
    adv = with_retry("Investment Advisor", INVESTMENT_ADVISOR, lambda: advisor_message(ra, fa),
                     ADVISOR_SUBMIT, lambda a: check_advisor(a, ra, fa))
    print("-- Strategy Manager: compiling")
    report = compile_report(run, ra, fa, adv)
    missing = [p for p in PARTS if p not in report]
    if missing:
        print(f"   Manager: parts missing: {missing}")
    path = folder / "report.md"
    path.write_text(report, encoding="utf-8")
    (folder / "roles.json").write_text(json.dumps({"research_analyst": ra, "financial_analyst": fa,
                                                   "investment_advisor": adv}, indent=2), encoding="utf-8")
    return path

# Week 2 notes — Jeenay Dedhia

Partner: Krishmi.

## Before Session 2

**Figure 1: workflow or agent?** A workflow. Code sets the path: the Strategy
Manager sends tasks to the Research Analyst, the Financial Analyst and the
Investment Advisor, checks the five parts and sends a part back once. The model
never chooses the next step.

**Which of the paper's tools does my desk get for free from EDGAR?** The
filings reader: the filing lists, the 10-K, 10-Q and 8-K documents, and the
XBRL company facts with tag, period and filing. The calculator is my code. I do
not use web search.

**Kim, Muhn & Nikolaev (2024): what would make the 60.35% edge shrink on
companies and years the model never saw?** Crowding: when many investors run
LLMs on the same statements, the signal is priced in and the edge goes away.

**Karpathy: where is the autonomy slider in my agent?** It is set low. Code
owns the seven steps, the Manager's checks and all arithmetic. The models only
write text inside a fixed path, and a human audit signs off. The one step up
is the Financial Analyst, which chooses which extra ratios to ask the
calculator for.

## Lab 02 — the desk's steps

**Gap check (the one I could not explain):** XBRL. Every number in a filing is
tagged with a concept, a period and a unit, and EDGAR serves them as one file
per company. A filer can move a number to a new tag between years. Costco moved
total revenue from `Revenues` (last year FY2025) to
`RevenueFromContractWithCustomerExcludingAssessedTax` (FY2026, $303,154M).
My reader picks, among the candidate tags, the one whose latest year is newest.

**Reflect 1, the step I trust least on a new company:** Step 4, the tag
choice. Companies tag differently. For example, Coca-Cola's long-term debt is
under `LongTermDebtAndCapitalLeaseObligations`, not `LongTermDebtNoncurrent`.
A new filer can use a tag that is not in my candidate list.

**Reflect 2, what the four roles need from the steps:** the accession numbers
of the filings, the facts with tag and period, the ratios with their
arithmetic, the release lines for the quarter, and the peers on one
definition. The roles must not compute.

## Lab 03 — the app

**Gap check, the role I expected to get a number wrong:** The Investment
Advisor. It sees only the two analysts' outputs, so it can restate or round a
number differently from the source. The Manager now checks that every number
in the thesis appears in the analysts' outputs.

**Reflect 1, the error a reader would trust most:** Costco's operating cash
flow. The 10-K XBRL gives $15,817M and the release's cash flow statement gives
$15,825M. Both look right, so a reader would trust either without checking.
The Financial Analyst used the 10-K figure and named the $8M difference.

**Reflect 2, the role I will change first:** The Research Analyst. I will tell
it to keep the unit on every quoted number ("$5,907 million", not "$5,907"),
because the 10-K states amounts in millions in the table heading, not on each
line.

## The human sign-off — learn on your own

**What is it?** Anthropic's `financial-services` repository says its agents
"draft analyst work product" for review by a qualified professional, and
"every output is staged for human sign-off."

**How does it work there?** The agents do not make investment recommendations,
execute transactions, bind risk, post to a ledger or approve onboarding on
their own.

**What does that agent have that my desk lacked?** An explicit sign-off gate.
My desk printed a Buy, Hold or Sell. Theirs stages the output for a human
before anything is final. My `verify.py` and the "Your mark" column in
`audits/` are my first version of that gate.

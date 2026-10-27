# fin-67110

Work folder for FIN 67110 Mastering AI for Finance, Purdue University, Daniels
School of Business, Fall 2026.

## Lab 01 — the question

Can the agent write a program in this folder that reads a key from a file, and
can the key stay off GitHub?

Yes to both. `check_env.py` reads `.env` and prints only the first four
characters of the key. `.gitignore` excludes `.env`, so the key is not in this
public repository.

## Files

| File | What it is |
| --- | --- |
| `check_env.py` | Loads `.env`, prints four characters of `API_KEY` and the full `SEC_USER_AGENT` |
| `.env.example` | Committed template with placeholder values |
| `.env` | **Not committed.** Real key lives here, excluded by `.gitignore` |
| `.gitignore` | Excludes `.env` and the other usual ways a secret leaks |
| `AGENTS.md` | Standing instructions the agent reads at the start of each session |
| `requirements.txt` | `python-dotenv` |
| `hello.md` | Written by the agent, to prove it runs in this folder |
| `desk.py` | The desk: seven steps from a ticker to the filings, facts and ratios, then the four roles |
| `sec.py` | EDGAR access: ticker to CIK, filing lists, index pages, documents as text |
| `facts.py` | Step 4: XBRL facts for the latest fiscal year, with the tag-trap rule |
| `calc.py` | Step 5: the calculator, every ratio with its arithmetic |
| `roles.py` | Lab 03: Research Analyst, Financial Analyst, Investment Advisor, Strategy Manager |
| `verify.py` | Traces each core claim to a filing line or to arithmetic that holds; writes the agent check in `audits/` |
| `tests/` | Known-answer tests: tag trap, Item 2.02, audit definitions, Costco's numbers, no company names in code |
| `week-02-notes.md` | My Week 2 one-line answers and reflections |
| `runs/` | One folder per run: the filings as text, `facts.json`, `report.md`, `roles.json` |
| `audits/` | Hand audits of the reports against the filings |

## Setup

Requires Python 3.11 or higher.

```bash
pip install -r requirements.txt     # Windows, if pip is not found: py -m pip install -r requirements.txt
cp .env.example .env                # Windows: copy .env.example .env
```

Open `.env`, paste your model provider's key over `paste-here`, and save it
under exactly that name — not `.env.txt`. Then:

```bash
python check_env.py                 # Windows, if python is not found: py check_env.py
```

Expected output:

```
Read: /path/to/fin-67110/.env
API_KEY:        sk-a...
SEC_USER_AGENT: Jeenay Dedhia dedhiaj@purdue.edu

OK: .env is being read. This does not prove the key is valid.
```

The four characters prove the file is read, not that the key works. Session 3
makes the first paid call.

## Labs 02 and 03 — the desk

Can four model roles, on top of seven coded steps, write a five-part report
whose numbers survive an audit against the filings, on any ticker?

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python desk.py COST --peers WMT,TGT,BJ --price 992.13 --price-date 2026-10-27
.venv/bin/python desk.py COST --no-roles      # the seven steps only, no model key
.venv/bin/python desk.py COST --step 4        # one step only
.venv/bin/python verify.py runs/COST_2026-10-27_174839 --audit audits/COST-audit.md
.venv/bin/python -m pytest -q
```

The seven steps (no model): (1) ticker to CIK; (2) latest 10-K, 10-Q and the
newest 8-K that reports Item 2.02, with accession numbers and the index page's
Accepted time; (3) the documents as text, the release from Exhibit 99.1;
(4) XBRL facts for the 10-K's fiscal year, choosing among candidate tags the one
whose latest year is newest; (5) ratios in code on the audit's definitions;
(6) the quarter's revenue and diluted EPS lines from the release; (7) peers'
operating margin on the same definition.

The four roles (`MODEL` in `.env`, default `claude-sonnet-5-5`, key as
`API_KEY`): each is a separate call that receives only the Manager's JSON
(task, context, expected output). The Financial Analyst may call a calculator
tool but never computes in the model. The Strategy Manager is code: it checks
the five parts, the eleven core claims and their sources, and that the
Advisor's numbers appear in the analysts' outputs; it sends a failing part back
once, then compiles `report.md`.

Nothing in the code names a company.

| Run | Report |
| --- | --- |
| Costco (known answer) | `runs/COST_2026-10-27_174839/report.md` |
| Coca-Cola (partner's pick, reported 2026-10-27) | `runs/KO_2026-10-27_175126/report.md` |
| Walmart (steps only) | `runs/WMT_*/facts.json` |

Prices are the 2026-10-27 close (COST 992.13, KO 91.18).

`verify.py` result: 11/11 core claims trace to the filings on both reports,
plus P/E, every peer margin, the template and the recommendation. The
"Your mark" column in `audits/` is the human sign-off.

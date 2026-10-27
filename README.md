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

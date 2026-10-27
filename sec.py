"""SEC EDGAR access: tickers, filing lists, index pages, documents as text.

Every request sends SEC_USER_AGENT from .env. EDGAR allows 10 requests per
second; a short pause between calls keeps the desk well under that.
"""

import os
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

REQUEST_PAUSE_SECONDS = 0.15
ARCHIVES = "https://www.sec.gov/Archives/edgar/data"

_session = requests.Session()


def _user_agent() -> str:
    agent = os.environ.get("SEC_USER_AGENT", "").strip().strip('"')
    if not agent or "@" not in agent:
        raise SystemExit("SEC_USER_AGENT is missing from .env (name and email).")
    return agent


def get(url: str) -> requests.Response:
    time.sleep(REQUEST_PAUSE_SECONDS)
    response = _session.get(url, headers={"User-Agent": _user_agent()}, timeout=60)
    response.raise_for_status()
    return response


def ticker_to_cik(ticker: str) -> tuple[str, str]:
    """Step 1: the ten-digit CIK and the registered name for a ticker."""
    table = get("https://www.sec.gov/files/company_tickers.json").json()
    wanted = ticker.upper().replace(".", "-")
    for row in table.values():
        if row["ticker"].upper() == wanted:
            return f"{int(row['cik_str']):010d}", row["title"]
    raise SystemExit(f"Ticker {ticker} is not in SEC company_tickers.json.")


def submissions(cik: str) -> dict:
    return get(f"https://data.sec.gov/submissions/CIK{cik}.json").json()


def _recent_rows(subs: dict) -> list[dict]:
    recent = subs["filings"]["recent"]
    keys = list(recent.keys())
    return [{k: recent[k][i] for k in keys} for i in range(len(recent["form"]))]


def latest_filings(subs: dict) -> dict:
    """Step 2: the latest 10-K, the latest 10-Q, and the latest 8-K with Item 2.02.

    The submissions list is newest first. A newer 8-K for an officer change or
    a shareholder vote is skipped: only Item 2.02 is an earnings release.
    """
    picked = {}
    for row in _recent_rows(subs):
        form = row["form"]
        if form == "10-K" and "10-K" not in picked:
            picked["10-K"] = row
        elif form == "10-Q" and "10-Q" not in picked:
            picked["10-Q"] = row
        elif form == "8-K" and "8-K" not in picked:
            items = [i.strip() for i in row.get("items", "").split(",")]
            if "2.02" in items:
                picked["8-K"] = row
        if len(picked) == 3:
            break
    missing = {"10-K", "10-Q", "8-K"} - picked.keys()
    if missing:
        raise SystemExit(f"No recent filing found for: {', '.join(sorted(missing))}.")
    return picked


def index_url(cik: str, accession: str) -> str:
    folder = accession.replace("-", "")
    return f"{ARCHIVES}/{int(cik)}/{folder}/{accession}-index.htm"


def read_index(cik: str, accession: str) -> dict:
    """The 'Accepted' time and the document table from a filing's index page."""
    soup = BeautifulSoup(get(index_url(cik, accession)).text, "html.parser")
    accepted = None
    for head in soup.select("div.infoHead"):
        if head.get_text(strip=True) == "Accepted":
            accepted = head.find_next_sibling("div").get_text(strip=True)
    documents = []
    table = soup.find("table", class_="tableFile")
    for tr in table.find_all("tr")[1:] if table else []:
        cells = tr.find_all("td")
        link = cells[2].find("a") if len(cells) > 3 else None
        if link:
            documents.append({
                "type": cells[3].get_text(strip=True),
                "url": "https://www.sec.gov" + link["href"].replace("/ix?doc=", ""),
            })
    return {"accepted": accepted, "documents": documents}


def document_url(cik: str, row: dict, index: dict) -> str:
    """The release is the 8-K's Exhibit 99.1; the others are the main document."""
    if row["form"] == "8-K":
        for doc in index["documents"]:
            if doc["type"].upper().startswith("EX-99.1") or doc["type"].upper() == "EX-99":
                return doc["url"]
        raise SystemExit(f"8-K {row['accessionNumber']} has no Exhibit 99.1.")
    folder = row["accessionNumber"].replace("-", "")
    return f"{ARCHIVES}/{int(cik)}/{folder}/{row['primaryDocument']}"


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for hidden in soup.select("ix\\:header, script, style"):
        hidden.decompose()
    # One table row becomes one line, so a label stays beside its numbers.
    for row in soup.find_all("tr"):
        cells = (c.get_text(" ", strip=True) for c in row.find_all(["td", "th"]))
        row.replace_with(" ".join(c for c in cells if c) + "\n")
    text = soup.get_text("\n")
    lines = (re.sub(r"[ \t\xa0]+", " ", line).strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def company_facts(cik: str) -> dict:
    return get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json").json()

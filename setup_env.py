"""setup_env.py - create the .env file without fighting a text editor.

Lab 01, FIN 67110 Mastering AI for Finance

Run once:
    python setup_env.py

Asks for your API key, hides it as you type, and writes .env with exactly
that name. Nothing is printed to the screen and nothing is stored in your
shell history. Delete this file afterwards if you like; it is not needed
again.
"""

import os
import stat
import sys
from getpass import getpass
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
ENV_PATH = FOLDER / ".env"
USER_AGENT = "Jeenay Dedhia dedhiaj@purdue.edu"


def main() -> None:
    if ENV_PATH.is_file():
        answer = input(f".env already exists in {FOLDER}. Overwrite? [y/N] ")
        if answer.strip().lower() not in ("y", "yes"):
            print("Left the existing .env alone.")
            return

    print("Paste your API key and press Enter. Nothing will appear as you type.")
    print("(That is deliberate - it keeps the key off your screen.)\n")

    key = getpass("API_KEY: ").strip()

    if not key:
        sys.exit("FAIL: nothing entered. Run this again and paste the key.")
    if key == "paste-here":
        sys.exit("FAIL: that is the placeholder, not a key.")
    if len(key) < 20:
        sys.exit(
            f"FAIL: that is only {len(key)} characters, which is too short for "
            "an API key. A paste may have been cut off. Run this again."
        )

    ENV_PATH.write_text(
        f"API_KEY={key}\n"
        f'SEC_USER_AGENT="{USER_AGENT}"\n',
        encoding="utf-8",
    )

    # On Mac and Linux, make the file readable only by you.
    if os.name != "nt":
        ENV_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)

    print(f"\nWrote {ENV_PATH}")
    print(f"Key length: {len(key)} characters (the key itself is not shown)")
    print("\nNow run:  python check_env.py")


if __name__ == "__main__":
    main()

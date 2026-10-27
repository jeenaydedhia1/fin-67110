"""check_env.py - prove this folder's .env is read, without exposing the secret.

Lab 01, FIN 67110 Mastering AI for Finance
Purdue University, Daniels School of Business

Run:
    pip install python-dotenv
    python check_env.py

Prints the first four characters of API_KEY followed by "...", then the full
SEC_USER_AGENT. No network call is made here, so a well-formed key and a
working key look the same. Session 3 makes the first paid call.
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    sys.exit(
        "FAIL: python-dotenv is not installed.\n"
        "      Install it with: pip install python-dotenv\n"
        "      (on Windows, if pip is not found: py -m pip install python-dotenv)"
    )

FOLDER = Path(__file__).resolve().parent
ENV_PATH = FOLDER / ".env"
PREFIX_LENGTH = 4
REQUIRED = ("API_KEY", "SEC_USER_AGENT")


def fail(message: str) -> None:
    """Print the problem and the fix, then stop with a non-zero exit code."""
    print(f"FAIL: {message}", file=sys.stderr)
    sys.exit(1)


def find_env_file() -> Path:
    """Return the .env path, or stop with the most likely cause."""
    if ENV_PATH.is_file():
        return ENV_PATH

    # The common Windows mistake: Notepad appends .txt when the file type is
    # left at "Text Documents". The file looks right in Explorer and is never
    # read. Name the actual file found so the fix is one rename.
    for stray in sorted(FOLDER.glob(".env.*")):
        if stray.name != ".env.example":
            fail(
                f"no .env in this folder, but {stray.name} is here. "
                f"Rename it to exactly .env (no extension) and run this again."
            )

    fail(
        f"no .env file in {FOLDER}.\n"
        "      Copy .env.example to .env, then paste your key into it.\n"
        '      Windows: copy .env.example .env    Mac/Linux: cp .env.example .env'
    )
    raise AssertionError("unreachable")  # fail() exits; this keeps linters quiet


def masked(value: str, prefix_length: int = PREFIX_LENGTH) -> str:
    """Return the first prefix_length characters and three dots.

    A value shorter than prefix_length is never shown in full, so a truncated
    paste cannot leak the whole key to the terminal or a screen share.
    """
    if len(value) <= prefix_length:
        return "..."
    return f"{value[:prefix_length]}..."


def main() -> None:
    env_path = find_env_file()
    load_dotenv(env_path, override=True)

    missing = [name for name in REQUIRED if not os.getenv(name)]
    if missing:
        fail(
            f"{', '.join(missing)} not set in {env_path.name}. "
            "Check each line is NAME=value with no spaces around the = sign."
        )

    api_key = os.environ["API_KEY"]
    user_agent = os.environ["SEC_USER_AGENT"]

    if api_key == "paste-here":
        fail(
            "API_KEY is still the placeholder 'paste-here'. "
            "Open .env and paste your model provider's key in its place."
        )

    print(f"Read: {env_path}")
    print(f"API_KEY:        {masked(api_key)}")
    print(f"SEC_USER_AGENT: {user_agent}")
    print()
    print("OK: .env is being read. This does not prove the key is valid.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""One-time OAuth bootstrap for a Google account.

Usage:
    python3 services/Google/authorize.py <account-alias>

Example:
    python3 services/Google/authorize.py personal
    python3 services/Google/authorize.py work

Opens a browser, you pick the Google account and grant access, and the token is
saved to tokens/<account-alias>.json. Repeat once per account.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auth  # noqa: E402  (script-mode import of the sibling module)


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    account = sys.argv[1]
    try:
        auth.authorize(account)
    except Exception as e:
        print(f"✗ {e}")
        sys.exit(1)
    print(f"✓ Authorised '{account}'. Token saved to tokens/{account}.json")


if __name__ == "__main__":
    main()

"""Shared Google OAuth for all Google services, across multiple accounts.

Each account authorises once (via authorize.py), producing a token file in
tokens/<account>.json. Access tokens refresh automatically using the stored
refresh token, so you only do the browser consent once per account.

Requires the Google client libraries (see requirements.txt). They are imported
at module load, but this module is only imported lazily by the service classes,
which the agent only touches when a Google tool is actually called — so the core
app runs fine without these libraries installed.
"""
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

HERE = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(HERE, "credentials.json")
TOKENS_DIR = os.path.join(HERE, "tokens")

# One consolidated scope set, requested once per account, covering every service.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

_services = {}  # (api, version, account) -> built service


def _token_path(account: str) -> str:
    return os.path.join(TOKENS_DIR, f"{account}.json")


def authorize(account: str) -> str:
    """Run the interactive OAuth consent flow for one account and save its token."""
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            f"Missing {CREDENTIALS_FILE}. Download your OAuth client secrets (Desktop "
            "app) from Google Cloud Console and save them there. See services/Google/README.md."
        )
    os.makedirs(TOKENS_DIR, exist_ok=True)
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(_token_path(account), "w") as f:
        f.write(creds.to_json())
    return account


def load_credentials(account: str) -> "Credentials":
    path = _token_path(account)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No saved token for Google account '{account}'. Authorise it once with:\n"
            f"    python3 services/Google/authorize.py {account}"
        )
    creds = Credentials.from_authorized_user_file(path, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(path, "w") as f:
                f.write(creds.to_json())
        else:
            raise RuntimeError(
                f"Token for '{account}' is invalid. Re-run: "
                f"python3 services/Google/authorize.py {account}"
            )
    return creds


def service(api: str, version: str, account: str):
    """Return a cached, authenticated Google API client for an account."""
    key = (api, version, account)
    if key not in _services:
        creds = load_credentials(account)
        _services[key] = build(api, version, credentials=creds, cache_discovery=False)
    return _services[key]

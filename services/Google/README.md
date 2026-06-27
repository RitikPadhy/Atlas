# Google Services

Gmail, Calendar, Drive, and Sheets — for one or more Google accounts —
exposed to the agent as tools. All free (quota-limited, no billing).

## Files
| File | What it does |
| ---- | ------------ |
| `auth.py` | Shared OAuth: stores/refreshes a token per account, builds API clients |
| `authorize.py` | One-time CLI to grant access for an account |
| `gmail.py` | search / read / send mail |
| `gcal.py` | list events / create event |
| `drive.py` | search / recent files |
| `sheets.py` | read / write ranges |

## One-time setup

**1. Install the libraries** (the core app doesn't need these; only Google tools do):
```sh
pip install -r requirements.txt
```

**2. Make a Google Cloud project + OAuth client (free, ~5 min):**
1. Go to <https://console.cloud.google.com/> → create a project.
2. **APIs & Services → Library** → enable: Gmail API, Google Calendar API, Google Drive API, Google Sheets API.
3. **APIs & Services → OAuth consent screen** → External → add your Google accounts under **Test users** (so the "unverified app" screen lets you through).
4. **APIs & Services → Credentials → Create credentials → OAuth client ID → Desktop app**.
5. Download the JSON and save it as **`services/Google/credentials.json`**.

**3. Authorise each account** (opens a browser; pick the account, click Allow):
```sh
python3 services/Google/authorize.py personal
python3 services/Google/authorize.py work
python3 services/Google/authorize.py other
```
The alias you pass is how you refer to the account later (e.g. "check my *work* gmail").
Set the default alias in the root `config.json` under `google.default_account`.

## Notes
- `credentials.json` and `tokens/` are git-ignored — they're secrets, never commit them.
- Tokens auto-refresh; you only do the browser consent once per account.
- Scopes requested (in `auth.py`): Gmail modify+send, Calendar, Drive, Sheets.
  Trim them if you want a narrower grant.

# Private Email (IMAP/SMTP)

Read, search, and send mail for any standard IMAP/SMTP account (Namecheap Private
Email, Zoho, Fastmail, custom domains…). Standard library only — no OAuth, no
extra packages, no Cloud project.

## Files
| File | What it does |
| ---- | ------------ |
| `client.py` | `EmailClient` — IMAP search/read, SMTP send |

## Tools exposed to the agent
- `mail_search` — search the inbox (unread / sender / subject / last-N-days)
- `mail_read` — read a message by uid
- `mail_send` — send mail (confirms first)

## Setup (2 steps)

**1. Put your address in `config.json`** under `email.accounts.private.address`.
For Namecheap Private Email the hosts/ports are already filled in:
```
imap_host: mail.privateemail.com   imap_port: 993
smtp_host: mail.privateemail.com   smtp_port: 465
```

**2. Export the mailbox password** (kept out of the repo — read from the environment):
```sh
echo "export PRIVATE_EMAIL_PW='your-mailbox-password'" >> ~/.zshrc
source ~/.zshrc
```

Then in the agent: *"search my private email for unread messages from the last week."*

## Notes
- A mailbox password is **full account access** (unlike a scoped OAuth token), so it
  lives only in the env var, never in `config.json`. For more safety you can store it in
  the macOS Keychain and export it in your shell from there.
- IMAP search is simpler than Gmail's: it supports unread / from / subject / since-date.
- Add more accounts by adding entries under `email.accounts` (each with its own
  `password_env`), and set `email.default_account`.

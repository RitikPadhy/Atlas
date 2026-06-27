"""Generic IMAP/SMTP email client — works with any provider (Namecheap Private
Email, Zoho, Fastmail, custom domains…). Standard library only.

The password is read from an environment variable (never stored in config), so
it isn't committed and the secret scanner can't leak it.
"""
import datetime
import email
import imaplib
import os
import smtplib
from email.header import decode_header, make_header
from email.mime.text import MIMEText


def _decode(value: str) -> str:
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value or ""


def _body_text(msg) -> str:
    """Best-effort plain-text body out of a parsed message."""
    if msg.is_multipart():
        for part in msg.walk():
            disp = str(part.get("Content-Disposition") or "")
            if part.get_content_type() == "text/plain" and "attachment" not in disp:
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", "replace")
        return ""
    payload = msg.get_payload(decode=True)
    return payload.decode(msg.get_content_charset() or "utf-8", "replace") if payload else ""


class EmailClient:
    def __init__(self, account_cfg: dict):
        self.cfg = account_cfg
        self.address = account_cfg["address"]
        pw_env = account_cfg.get("password_env", "PRIVATE_EMAIL_PW")
        self.password = os.environ.get(pw_env)
        if not self.password:
            raise RuntimeError(
                f"Email password not set. Export it first, e.g. in ~/.zshrc:\n"
                f"    export {pw_env}='your-mailbox-password'\n"
                f"then reopen the terminal."
            )

    def _imap(self):
        m = imaplib.IMAP4_SSL(self.cfg["imap_host"], int(self.cfg.get("imap_port", 993)))
        m.login(self.address, self.password)
        return m

    def search(self, unread: bool = False, sender: str = None, subject: str = None,
               since_days: int = None, limit: int = 10, folder: str = "INBOX") -> str:
        m = self._imap()
        try:
            m.select(folder, readonly=True)  # readonly so we don't mark mail as read
            crit = []
            if unread:
                crit += ["UNSEEN"]
            if sender:
                crit += ["FROM", sender]
            if subject:
                crit += ["SUBJECT", subject]
            if since_days:
                since = (datetime.date.today() - datetime.timedelta(days=int(since_days)))
                crit += ["SINCE", since.strftime("%d-%b-%Y")]
            if not crit:
                crit = ["ALL"]
            typ, data = m.uid("search", None, *crit)
            uids = data[0].split()
            uids = uids[-int(limit):][::-1]  # newest first
            out = []
            for uid in uids:
                typ, d = m.uid("fetch", uid,
                               "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
                hdr = _parse_headers(d)
                out.append(f"[{uid.decode()}] {hdr.get('Subject', '(no subject)')}\n"
                           f"   from {hdr.get('From', '?')} · {hdr.get('Date', '')}")
            return "\n".join(out) if out else "No messages found."
        finally:
            m.logout()

    def read(self, uid: str, folder: str = "INBOX") -> str:
        m = self._imap()
        try:
            m.select(folder, readonly=True)
            typ, d = m.uid("fetch", str(uid), "(BODY.PEEK[])")
            if not d or d[0] is None:
                return "Message not found."
            msg = email.message_from_bytes(d[0][1])
            return (f"Subject: {_decode(msg.get('Subject', ''))}\n"
                    f"From: {_decode(msg.get('From', ''))}\n"
                    f"Date: {msg.get('Date', '')}\n\n{_body_text(msg)}")
        finally:
            m.logout()

    def send(self, to: str, subject: str, body: str) -> str:
        msg = MIMEText(body)
        msg["From"] = self.address
        msg["To"] = to
        msg["Subject"] = subject
        host = self.cfg["smtp_host"]
        port = int(self.cfg.get("smtp_port", 465))
        smtp = smtplib.SMTP_SSL(host, port) if port == 465 else smtplib.SMTP(host, port)
        try:
            if port != 465:
                smtp.starttls()
            smtp.login(self.address, self.password)
            smtp.sendmail(self.address, [to], msg.as_string())
        finally:
            smtp.quit()
        return f"Sent to {to}."


def _parse_headers(fetch_data) -> dict:
    for part in fetch_data:
        if isinstance(part, tuple):
            msg = email.message_from_bytes(part[1])
            return {k: _decode(v) for k, v in msg.items()}
    return {}

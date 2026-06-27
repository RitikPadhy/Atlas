"""Gmail, per account."""
import base64
from email.mime.text import MIMEText

from . import auth


class GmailService:
    def __init__(self, account: str):
        self.account = account
        self.svc = auth.service("gmail", "v1", account)

    def search(self, query: str, max_results: int = 10) -> str:
        """Search messages with Gmail's query syntax (e.g. 'from:boss is:unread')."""
        resp = self.svc.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        msgs = resp.get("messages", [])
        if not msgs:
            return "No messages found."
        out = []
        for m in msgs:
            full = self.svc.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()
            h = {x["name"]: x["value"] for x in full.get("payload", {}).get("headers", [])}
            out.append(
                f"[{m['id']}] {h.get('Subject', '(no subject)')}\n"
                f"   from {h.get('From', '?')} · {h.get('Date', '')}\n"
                f"   {full.get('snippet', '')}"
            )
        return "\n".join(out)

    def read(self, message_id: str) -> str:
        """Return the full plain-text body of a message by id."""
        msg = self.svc.users().messages().get(userId="me", id=message_id, format="full").execute()
        payload = msg.get("payload", {})
        h = {x["name"]: x["value"] for x in payload.get("headers", [])}
        body = _extract_body(payload)
        return (f"Subject: {h.get('Subject', '')}\nFrom: {h.get('From', '')}\n"
                f"Date: {h.get('Date', '')}\n\n{body}")

    def address(self) -> str:
        """The email address this account's token belongs to."""
        return self.svc.users().getProfile(userId="me").execute().get("emailAddress", "")

    def send(self, to: str, subject: str, body: str) -> str:
        msg = MIMEText(body)
        msg["to"] = to
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        sent = self.svc.users().messages().send(userId="me", body={"raw": raw}).execute()
        return f"Sent to {to} (id {sent.get('id')})."


def _extract_body(payload: dict) -> str:
    """Pull the text/plain part out of a Gmail message payload."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", "replace")
    for part in payload.get("parts", []) or []:
        text = _extract_body(part)
        if text:
            return text
    return ""

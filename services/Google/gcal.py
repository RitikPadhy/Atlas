"""Google Calendar, per account."""
import datetime

from . import auth


class CalendarService:
    def __init__(self, account: str):
        self.account = account
        self.svc = auth.service("calendar", "v3", account)

    def events(self, days: int = 1) -> str:
        """Upcoming events from now to `days` ahead (default: today)."""
        now = datetime.datetime.utcnow()
        time_min = now.isoformat() + "Z"
        time_max = (now + datetime.timedelta(days=days)).isoformat() + "Z"
        resp = self.svc.events().list(
            calendarId="primary", timeMin=time_min, timeMax=time_max,
            singleEvents=True, orderBy="startTime",
        ).execute()
        items = resp.get("items", [])
        if not items:
            return "No events."
        out = []
        for e in items:
            start = e["start"].get("dateTime", e["start"].get("date"))
            out.append(f"- {start}  {e.get('summary', '(no title)')}")
        return "\n".join(out)

    def create_event(self, summary: str, start_iso: str, end_iso: str) -> str:
        """Create an event. start_iso/end_iso are RFC3339, e.g. 2026-06-28T15:00:00+05:30."""
        body = {
            "summary": summary,
            "start": {"dateTime": start_iso},
            "end": {"dateTime": end_iso},
        }
        ev = self.svc.events().insert(calendarId="primary", body=body).execute()
        link = ev.get("htmlLink", "")
        return f"Created '{summary}' ({start_iso}). {link}"

"""Google Sheets, per account."""
from . import auth


class SheetsService:
    def __init__(self, account: str):
        self.account = account
        self.svc = auth.service("sheets", "v4", account)

    def read(self, spreadsheet_id: str, range_a1: str) -> str:
        """Read an A1 range, e.g. 'Sheet1!A1:C10'."""
        resp = self.svc.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_a1,
        ).execute()
        rows = resp.get("values", [])
        if not rows:
            return "(empty range)"
        return "\n".join("\t".join(str(c) for c in row) for row in rows)

    def write(self, spreadsheet_id: str, range_a1: str, values: list) -> str:
        """Write a 2-D list of values into an A1 range (overwrites)."""
        resp = self.svc.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range=range_a1,
            valueInputOption="USER_ENTERED", body={"values": values},
        ).execute()
        return f"Updated {resp.get('updatedCells', 0)} cells in {range_a1}."

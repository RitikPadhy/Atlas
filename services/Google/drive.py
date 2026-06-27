"""Google Drive, per account."""
from . import auth

_FIELDS = "files(id,name,mimeType,modifiedTime,webViewLink)"


class DriveService:
    def __init__(self, account: str):
        self.account = account
        self.svc = auth.service("drive", "v3", account)

    def search(self, query: str, max_results: int = 15) -> str:
        """Find files whose name contains `query`."""
        safe = query.replace("'", "\\'")
        resp = self.svc.files().list(
            q=f"name contains '{safe}' and trashed = false",
            pageSize=max_results, fields=_FIELDS,
        ).execute()
        return _format(resp.get("files", []))

    def recent(self, max_results: int = 15) -> str:
        """List the most recently modified files."""
        resp = self.svc.files().list(
            orderBy="modifiedTime desc", pageSize=max_results, fields=_FIELDS,
        ).execute()
        return _format(resp.get("files", []))


def _format(files: list) -> str:
    if not files:
        return "No files found."
    return "\n".join(
        f"- {f['name']}  ({f.get('mimeType', '')})\n  {f.get('webViewLink', '')}"
        for f in files
    )

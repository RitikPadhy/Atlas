"""The tools the orchestrator (brain) can call.

Each tool is a method on ToolBox. SCHEMAS describes them to the model in the
Ollama / OpenAI function-calling format. `dispatch()` runs a tool by name.

Two safety rules live here:
  - destructive tools (run_shell, write_file) require user confirmation;
  - their inputs are secret-scanned before anything happens.

The coding specialist (`qwen2.5-coder:7b`) is exposed as the `ask_coder`
tool: that is how the brain delegates real coding, which triggers the
one model swap we allow.
"""
import html
import html.parser
import os
import re
import subprocess
import urllib.parse
import urllib.request
from typing import Callable, Dict, List

import ollama_client
import secret_scanner

_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}


def _http_get(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        charset = r.headers.get_content_charset() or "utf-8"
        return r.read().decode(charset, "replace")


class _TextExtractor(html.parser.HTMLParser):
    """Strip a page down to readable text."""
    _SKIP = {"script", "style", "noscript", "head", "svg", "nav", "footer"}

    def __init__(self):
        super().__init__()
        self.out: List[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            s = data.strip()
            if s:
                self.out.append(s)


def _html_to_text(raw: str) -> str:
    p = _TextExtractor()
    try:
        p.feed(raw)
    except Exception:
        pass
    return re.sub(r"[ \t]{2,}", " ", " ".join(p.out))


_TAGS = re.compile(r"<[^>]+>")
_DDG_A = re.compile(r'<a[^>]+class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL)
_DDG_SNIP = re.compile(r'class="result__snippet"[^>]*>(.*?)</a>', re.DOTALL)


def _strip(s: str) -> str:
    return html.unescape(_TAGS.sub("", s)).strip()


def _real_url(href: str) -> str:
    m = re.search(r"[?&]uddg=([^&]+)", href)
    if m:
        return urllib.parse.unquote(m.group(1))
    return ("https:" + href) if href.startswith("//") else href


def _ddg_search(query: str, n: int = 5) -> str:
    base = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    try:
        page = _http_get(base)
    except Exception as e:
        return f"error searching: {e}"
    out = []
    for m in _DDG_A.finditer(page):
        href, title = m.group(1), m.group(2)
        # Skip sponsored results (DuckDuckGo serves these via a y.js ad redirect).
        if "y.js" in href or "ad_domain" in href:
            continue
        sm = _DDG_SNIP.search(page, m.end())  # the snippet that follows this title
        snip = _strip(sm.group(1)) if sm else ""
        out.append(f"{len(out) + 1}. {_strip(title)}\n   {_real_url(href)}\n   {snip}")
        if len(out) >= n:
            break
    return "\n".join(out) if out else "No results found."


SCHEMAS: List[Dict] = [
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Open a URL in the browser so the user can see it.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "The full URL, including https://"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Launch a macOS application by name, e.g. 'Spotify', 'Finder', 'Visual Studio Code'.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "The application name"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_path",
            "description": "Open a file or folder in its default app / Finder.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Absolute or ~ path to a file or folder"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List the contents of a directory.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Directory path (default: current directory)"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read and return the text contents of a file.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Path to the file"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write text to a file (overwrites). Asks the user to confirm first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"},
                    "content": {"type": "string", "description": "The full text to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a shell command on the user's Mac and return its output. "
                           "Asks the user to confirm first. Use for anything not covered by another tool.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "The shell command to run"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mac_health",
            "description": "Report the Mac's health: loaded models, memory pressure, disk space, battery, uptime, top processes.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web and return the top results (title, URL, snippet). "
                           "Use this first for research or any question about current/real-world facts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "num_results": {"type": "integer", "description": "How many results (default 5)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch a web page and return its readable text. Use after web_search to read a result.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "The full URL to fetch"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calendar_today",
            "description": "List the user's calendar events for today (from macOS Calendar).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reminders",
            "description": "List the user's open (incomplete) reminders from macOS Reminders.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_accounts",
            "description": "List ALL connected accounts — both Google (Gmail/Calendar/Drive/Sheets) "
                           "and the private IMAP/SMTP email — with their addresses and status. Use this "
                           "whenever the user asks which email/accounts are connected.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "google_accounts",
            "description": "List the configured Google account aliases, which are authorized, "
                           "and the real email address each one maps to. Use this when the user "
                           "asks which Google/Gmail accounts are connected or for their addresses.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_search",
            "description": "Search Gmail using Gmail query syntax (e.g. 'from:boss is:unread newer_than:7d').",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Gmail search query"},
                    "account": {"type": "string", "description": "Account alias (omit for default)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_send",
            "description": "Send an email. Asks the user to confirm first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                    "account": {"type": "string", "description": "Account alias (omit for default)"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gcal_events",
            "description": "List upcoming Google Calendar events from now to N days ahead (default 1 = today).",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "How many days ahead (default 1)"},
                    "account": {"type": "string", "description": "Account alias (omit for default)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gcal_create_event",
            "description": "Create a Google Calendar event. Asks the user to confirm first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Event title"},
                    "start": {"type": "string", "description": "Start, RFC3339 e.g. 2026-06-28T15:00:00+05:30"},
                    "end": {"type": "string", "description": "End, RFC3339"},
                    "account": {"type": "string", "description": "Account alias (omit for default)"},
                },
                "required": ["summary", "start", "end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "drive_search",
            "description": "Search Google Drive for files whose name contains the query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "account": {"type": "string", "description": "Account alias (omit for default)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sheets_read",
            "description": "Read an A1 range from a Google Sheet, e.g. 'Sheet1!A1:C10'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {"type": "string", "description": "The sheet ID from its URL"},
                    "range": {"type": "string", "description": "A1 range, e.g. Sheet1!A1:C10"},
                    "account": {"type": "string", "description": "Account alias (omit for default)"},
                },
                "required": ["spreadsheet_id", "range"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sheets_write",
            "description": "Write a 2-D array of values into an A1 range of a Google Sheet. Confirms first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {"type": "string"},
                    "range": {"type": "string", "description": "A1 range to write into"},
                    "values": {
                        "type": "array",
                        "description": "Rows of cells, e.g. [[\"a\",\"b\"],[\"c\",\"d\"]]",
                        "items": {"type": "array", "items": {"type": "string"}},
                    },
                    "account": {"type": "string", "description": "Account alias (omit for default)"},
                },
                "required": ["spreadsheet_id", "range", "values"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mail_search",
            "description": "Search the user's private (non-Gmail) email over IMAP. All filters "
                           "optional; with none it returns the most recent messages from the inbox.",
            "parameters": {
                "type": "object",
                "properties": {
                    "unread": {"type": "boolean", "description": "Only unread messages"},
                    "sender": {"type": "string", "description": "Filter by From address/name"},
                    "subject": {"type": "string", "description": "Filter by subject text"},
                    "since_days": {"type": "integer", "description": "Only messages from the last N days"},
                    "limit": {"type": "integer", "description": "Max results (default 10)"},
                    "account": {"type": "string", "description": "Account alias (omit for default)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mail_read",
            "description": "Read the full body of one private-email message by its uid (from mail_search).",
            "parameters": {
                "type": "object",
                "properties": {
                    "uid": {"type": "string", "description": "The message uid shown in mail_search"},
                    "account": {"type": "string", "description": "Account alias (omit for default)"},
                },
                "required": ["uid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mail_send",
            "description": "Send an email from the user's private (non-Gmail) account. Confirms first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                    "account": {"type": "string", "description": "Account alias (omit for default)"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_coder",
            "description": "Delegate a programming task (write, explain, debug, or review code) to the "
                           "specialised coding model. Give a clear, self-contained brief with all needed context.",
            "parameters": {
                "type": "object",
                "properties": {"task": {"type": "string", "description": "A complete description of the coding task"}},
                "required": ["task"],
            },
        },
    },
]


def _cmd(args, timeout=10):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout).stdout
    except Exception:
        return ""


def _mem_free_pct():
    m = re.search(r"free percentage:\s*(\d+)%", _cmd(["memory_pressure"]))
    return int(m.group(1)) if m else None


def _disk_root():
    """(avail_gb, used_pct) for /."""
    lines = _cmd(["df", "-k", "/"]).splitlines()
    if len(lines) < 2:
        return (None, None)
    p = lines[1].split()
    try:
        return (int(p[3]) / 1024 / 1024, int(p[4].rstrip("%")))  # avail KB -> GB, capacity %
    except (IndexError, ValueError):
        return (None, None)


def _battery():
    """(percent, on_ac_power)."""
    out = _cmd(["pmset", "-g", "batt"])
    m = re.search(r"(\d+)%", out)
    return (int(m.group(1)) if m else None, "AC Power" in out)


def _loadavg():
    m = re.findall(r"[\d.]+", _cmd(["sysctl", "-n", "vm.loadavg"]))
    return float(m[0]) if m else None


def _top_cpu():
    """(percent, name) of the busiest process."""
    lines = _cmd(["bash", "-c", "ps -Aceo pcpu,comm -r | head -2"]).splitlines()
    if len(lines) >= 2:
        p = lines[1].strip().split(None, 1)
        try:
            return (float(p[0]), p[1] if len(p) > 1 else "?")
        except ValueError:
            pass
    return (None, None)


class ToolBox:
    def __init__(self, config: dict, confirm: Callable[[str], bool], notify: Callable[[str], None]):
        self.cfg = config
        self.host = config["ollama_host"]
        self.confirm = confirm           # confirm(question) -> bool
        self.notify = notify             # notify(text) -> None  (for user-facing status)
        self.max_chars = config.get("max_tool_output_chars", 6000)
        self._gdefault = config.get("google", {}).get("default_account", "personal")
        self._edefault = config.get("email", {}).get("default_account", "private")

    # ---- helpers -----------------------------------------------------------
    def _truncate(self, s: str) -> str:
        if len(s) > self.max_chars:
            return s[: self.max_chars] + f"\n…[truncated {len(s) - self.max_chars} chars]"
        return s

    def _run(self, args: List[str], timeout: int = 30) -> str:
        try:
            p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        except FileNotFoundError:
            return f"error: command not found: {args[0]}"
        except subprocess.TimeoutExpired:
            return "error: command timed out"
        out = (p.stdout or "") + (p.stderr or "")
        return self._truncate(out.strip()) or "(no output)"

    # ---- tools -------------------------------------------------------------
    def open_url(self, url: str) -> str:
        browser = self.cfg.get("browser_app")
        if browser:
            p = subprocess.run(["open", "-a", browser, url], capture_output=True, text=True)
            if p.returncode == 0:
                return f"Opened {url} in {browser}."
        subprocess.run(["open", url])
        return f"Opened {url}."

    def open_app(self, name: str) -> str:
        p = subprocess.run(["open", "-a", name], capture_output=True, text=True)
        if p.returncode != 0:
            return f"error: could not open app '{name}': {p.stderr.strip()}"
        return f"Opened {name}."

    def open_path(self, path: str) -> str:
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            return f"error: path does not exist: {path}"
        subprocess.run(["open", path])
        return f"Opened {path}."

    def list_dir(self, path: str = ".") -> str:
        path = os.path.expanduser(path or ".")
        if not os.path.isdir(path):
            return f"error: not a directory: {path}"
        return self._run(["ls", "-la", path])

    def read_file(self, path: str) -> str:
        path = os.path.expanduser(path)
        if not os.path.isfile(path):
            return f"error: not a file: {path}"
        try:
            with open(path, "r", errors="replace") as f:
                return self._truncate(f.read())
        except Exception as e:
            return f"error reading file: {e}"

    def write_file(self, path: str, content: str) -> str:
        path = os.path.expanduser(path)
        findings = secret_scanner.scan(content, self.cfg["secret_patterns"])
        if findings:
            self.notify("⚠ The text to write looks like it contains secret(s): "
                        + ", ".join(sorted({f.name for f in findings})))
        if not self.confirm(f"Write {len(content)} chars to {path}?"):
            return "User declined to write the file."
        try:
            with open(path, "w") as f:
                f.write(content)
            return f"Wrote {len(content)} chars to {path}."
        except Exception as e:
            return f"error writing file: {e}"

    def run_shell(self, command: str) -> str:
        findings = secret_scanner.scan(command, self.cfg["secret_patterns"])
        if findings:
            self.notify("⚠ This command looks like it contains secret(s): "
                        + ", ".join(sorted({f.name for f in findings})))
        if not self.confirm(f"Run shell command?\n    $ {command}"):
            return "User declined to run the command."
        try:
            p = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return "error: command timed out"
        out = (p.stdout or "") + (p.stderr or "")
        return self._truncate(out.strip()) + f"\n(exit code {p.returncode})"

    def mac_health(self) -> str:
        """System health with a DETERMINISTIC 'needs attention' verdict computed
        here in code (not left to the model), so the alerts are always correct."""
        cores = None
        try:
            cores = int(_cmd(["sysctl", "-n", "hw.logicalcpu"]).strip())
        except ValueError:
            pass
        mem = _mem_free_pct()
        avail_gb, used_pct = _disk_root()
        batt, on_ac = _battery()
        load1 = _loadavg()
        top_pct, top_name = _top_cpu()
        models = self._run(["ollama", "ps"]).strip()

        status = ["## Status"]
        status.append(f"- Memory: {mem}% free" if mem is not None else "- Memory: (unknown)")
        status.append(f"- Disk: {avail_gb:.0f} GB free ({used_pct}% used)"
                      if avail_gb is not None else "- Disk: (unknown)")
        status.append(f"- Battery: {batt}% ({'on AC' if on_ac else 'on battery'})"
                      if batt is not None else "- Battery: (unknown)")
        cpu = f"- CPU load (1-min): {load1:.2f} on {cores or '?'} cores" if load1 is not None else "- CPU load: (unknown)"
        if top_pct is not None:
            cpu += f"; top: {top_name} @ {top_pct:.0f}%"
        status.append(cpu)
        status.append("- GPU models loaded: " + (models.replace("\n", " | ") if models else "none"))

        # --- deterministic alerts ---
        alerts = []
        if avail_gb is not None and (avail_gb < 20 or (used_pct is not None and used_pct >= 90)):
            alerts.append(f"⚠ Disk low: {avail_gb:.0f} GB free ({used_pct}% used) → free up space")
        if mem is not None and mem < 10:
            alerts.append(f"⚠ Memory pressure: only {mem}% free → close heavy apps before loading a model")
        if batt is not None and batt < 20 and not on_ac:
            alerts.append(f"⚠ Battery low: {batt}% on battery → plug in")
        if load1 is not None and cores and load1 > cores:
            alerts.append(f"⚠ High CPU load: {load1:.2f} on {cores} cores → something's working hard")
        if top_pct is not None and top_pct > 80:
            alerts.append(f"⚠ {top_name} is using {top_pct:.0f}% CPU")

        attn = "## NEEDS ATTENTION\n" + ("\n".join(alerts) if alerts else "Nothing — all healthy.")
        return "\n".join(status) + "\n\n" + attn

    def web_search(self, query: str, num_results: int = 5) -> str:
        return _ddg_search(query, int(num_results) if num_results else 5)

    def web_fetch(self, url: str) -> str:
        try:
            raw = _http_get(url, timeout=20)
        except Exception as e:
            return f"error fetching {url}: {e}"
        return self._truncate(_html_to_text(raw))

    def _osa(self, script: str, timeout: int = 25) -> str:
        try:
            p = subprocess.run(["osascript", "-e", script],
                               capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return ("error: timed out — on first use, grant access in "
                    "System Settings → Privacy & Security → Automation.")
        out = (p.stdout or "") + (p.stderr or "")
        return self._truncate(out.strip()) or "(nothing)"

    def calendar_today(self) -> str:
        script = (
            'set output to ""\n'
            'tell application "Calendar"\n'
            '  set theDay to current date\n'
            '  set hours of theDay to 0\n'
            '  set minutes of theDay to 0\n'
            '  set seconds of theDay to 0\n'
            '  set tomorrow to theDay + 1 * days\n'
            '  repeat with c in calendars\n'
            '    repeat with e in (every event of c whose start date ≥ theDay and start date < tomorrow)\n'
            '      set output to output & (summary of e) & " — " & (start date of e as string) & linefeed\n'
            '    end repeat\n'
            '  end repeat\n'
            'end tell\n'
            'return output'
        )
        return self._osa(script, timeout=40)

    def reminders(self) -> str:
        script = ('tell application "Reminders" to return name of '
                  '(reminders whose completed is false)')
        return self._osa(script).replace(", ", "\n")

    def ask_coder(self, task: str) -> str:
        coder = self.cfg["models"]["coder"]
        self.notify(f"→ delegating to {coder} (loading the coding model)…")
        msg = ollama_client.chat(
            self.host,
            coder,
            messages=[
                {"role": "system", "content": "You are an expert programmer. Answer the coding task "
                                               "directly and completely with correct, runnable code."},
                {"role": "user", "content": task},
            ],
            keep_alive=self.cfg.get("keep_alive", "5m"),
            timeout=300,
        )
        return self._truncate(msg.get("content", "").strip() or "(coder returned nothing)")

    # ---- Google services (lazy: don't import unless actually used) ----------
    def _gservice(self, module: str, cls: str, account):
        """Import a Services.Google.<module>.<cls> and instantiate it for an account."""
        import importlib
        mod = importlib.import_module(f"services.Google.{module}")
        return getattr(mod, cls)(account or self._gdefault)

    @staticmethod
    def _gerr(e: Exception) -> str:
        if isinstance(e, ImportError):
            return ("Google libraries not installed. Run:  pip install -r requirements.txt")
        return f"Google error: {e}"

    def list_accounts(self) -> str:
        """All connected accounts: Google + the private IMAP/SMTP email."""
        import os
        parts = []
        if self.cfg.get("google", {}).get("accounts"):
            parts.append(self.google_accounts())
        email_accounts = self.cfg.get("email", {}).get("accounts", {})
        if email_accounts:
            lines = ["Private email (IMAP/SMTP):"]
            for alias, a in email_accounts.items():
                ready = bool(os.environ.get(a.get("password_env", "PRIVATE_EMAIL_PW")))
                lines.append(f"- {alias}: {a.get('address', '?')} "
                             f"({'ready' if ready else 'password env not set'})")
            parts.append("\n".join(lines))
        return "\n\n".join(parts) if parts else "No accounts configured."

    def google_accounts(self) -> str:
        """List configured Google aliases, whether each is authorized, and its email."""
        import os
        g = self.cfg.get("google", {})
        aliases = g.get("accounts", [])
        if not aliases:
            return "No Google accounts configured in config.json."
        tokens_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "services", "Google", "tokens")
        lines = []
        for alias in aliases:
            if not os.path.exists(os.path.join(tokens_dir, f"{alias}.json")):
                lines.append(f"- {alias}: NOT authorized "
                             f"(run: python3 services/Google/authorize.py {alias})")
                continue
            try:
                lines.append(f"- {alias}: {self._gservice('gmail', 'GmailService', alias).address()}")
            except Exception as e:
                lines.append(f"- {alias}: authorized, but error ({self._gerr(e)})")
        return f"Google accounts (default: {g.get('default_account')}):\n" + "\n".join(lines)

    def gmail_search(self, query: str, account: str = None) -> str:
        try:
            return self._truncate(self._gservice("gmail", "GmailService", account).search(query))
        except Exception as e:
            return self._gerr(e)

    def gmail_send(self, to: str, subject: str, body: str, account: str = None) -> str:
        findings = secret_scanner.scan(body, self.cfg["secret_patterns"])
        if findings:
            self.notify("⚠ This email body looks like it contains secret(s): "
                        + ", ".join(sorted({f.name for f in findings})))
        acct = account or self._gdefault
        if not self.confirm(f"Send email from '{acct}' to {to} (subject: {subject})?"):
            return "User declined to send the email."
        try:
            return self._gservice("gmail", "GmailService", account).send(to, subject, body)
        except Exception as e:
            return self._gerr(e)

    def gcal_events(self, days: int = 1, account: str = None) -> str:
        try:
            return self._truncate(self._gservice("gcal", "CalendarService", account).events(int(days)))
        except Exception as e:
            return self._gerr(e)

    def gcal_create_event(self, summary: str, start: str, end: str, account: str = None) -> str:
        acct = account or self._gdefault
        if not self.confirm(f"Create event '{summary}' ({start}) on '{acct}'?"):
            return "User declined to create the event."
        try:
            return self._gservice("gcal", "CalendarService", account).create_event(summary, start, end)
        except Exception as e:
            return self._gerr(e)

    def drive_search(self, query: str, account: str = None) -> str:
        try:
            return self._truncate(self._gservice("drive", "DriveService", account).search(query))
        except Exception as e:
            return self._gerr(e)

    def sheets_read(self, spreadsheet_id: str, range: str, account: str = None) -> str:
        try:
            return self._truncate(self._gservice("sheets", "SheetsService", account).read(spreadsheet_id, range))
        except Exception as e:
            return self._gerr(e)

    def sheets_write(self, spreadsheet_id: str, range: str, values: list, account: str = None) -> str:
        acct = account or self._gdefault
        if not self.confirm(f"Write {len(values)} row(s) to {range} in sheet {spreadsheet_id} on '{acct}'?"):
            return "User declined to write to the sheet."
        try:
            return self._gservice("sheets", "SheetsService", account).write(spreadsheet_id, range, values)
        except Exception as e:
            return self._gerr(e)

    # ---- private (IMAP/SMTP) email -----------------------------------------
    def _email_client(self, account):
        from services.Private_Emails.client import EmailClient
        e = self.cfg.get("email", {})
        alias = account or self._edefault
        accounts = e.get("accounts", {})
        if alias not in accounts:
            raise RuntimeError(f"Unknown email account '{alias}'. Configured: "
                               f"{', '.join(accounts) or 'none'}.")
        return EmailClient(accounts[alias])

    def mail_search(self, unread: bool = False, sender: str = None, subject: str = None,
                    since_days: int = None, limit: int = 10, folder: str = "INBOX",
                    account: str = None) -> str:
        try:
            return self._truncate(self._email_client(account).search(
                unread=unread, sender=sender, subject=subject,
                since_days=since_days, limit=int(limit), folder=folder))
        except Exception as e:
            return f"Email error: {e}"

    def mail_read(self, uid: str, folder: str = "INBOX", account: str = None) -> str:
        try:
            return self._truncate(self._email_client(account).read(uid, folder=folder))
        except Exception as e:
            return f"Email error: {e}"

    def mail_send(self, to: str, subject: str, body: str, account: str = None) -> str:
        findings = secret_scanner.scan(body, self.cfg["secret_patterns"])
        if findings:
            self.notify("⚠ This email body looks like it contains secret(s): "
                        + ", ".join(sorted({f.name for f in findings})))
        if not self.confirm(f"Send email to {to} (subject: {subject})?"):
            return "User declined to send the email."
        try:
            return self._email_client(account).send(to, subject, body)
        except Exception as e:
            return f"Email error: {e}"

    # ---- dispatch ----------------------------------------------------------
    def dispatch(self, name: str, args: Dict) -> str:
        fn = getattr(self, name, None)
        if not callable(fn) or name.startswith("_"):
            return f"error: unknown tool '{name}'"
        try:
            return fn(**args)
        except TypeError as e:
            return f"error: bad arguments for {name}: {e}"
        except Exception as e:
            return f"error running {name}: {e}"

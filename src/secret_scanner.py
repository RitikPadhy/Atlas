"""Scan prompts for hardcoded secrets before they are sent to a model."""
import re
from typing import Dict, List, NamedTuple


class Finding(NamedTuple):
    name: str       # human-readable label, e.g. "AWS access key id"
    match: str      # the (redacted) offending substring
    line: int       # 1-based line number within the prompt


def _redact(s: str) -> str:
    """Show only the first few chars so the secret isn't echoed in full."""
    s = s.strip()
    if len(s) <= 8:
        return s[:2] + "…"
    return s[:4] + "…" + s[-2:]


def scan(text: str, patterns: List[Dict[str, str]]) -> List[Finding]:
    """Return every secret-pattern match found in `text`."""
    compiled = [(p["name"], re.compile(p["regex"])) for p in patterns]
    findings: List[Finding] = []
    for lineno, line in enumerate(text.splitlines() or [text], start=1):
        for name, rx in compiled:
            for m in rx.finditer(line):
                findings.append(Finding(name, _redact(m.group(0)), lineno))
    return findings

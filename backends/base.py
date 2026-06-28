"""Provider-agnostic model backend interface.

The agent loop talks ONLY to a Backend — it never knows which model/provider is
behind it. Each provider (Ollama today; Claude / GPT / etc. later) implements
`chat`, returning a NORMALIZED assistant reply:

    {"content": str, "tool_calls": [{"name": str, "arguments": dict}, ...]}

Conversation history stays in the OpenAI/Ollama-style message format (role +
content, assistant tool_calls, tool-role results). A backend translates that to
and from its provider's own shape internally, so the rest of the system —
tools, skills, shortcuts, guardrails — never changes when you switch models.

To add a provider: create backends/<name>_backend.py with a Backend subclass,
then register it in backends/__init__.py and set "provider" in config.json.
"""


class BackendError(RuntimeError):
    """Raised by a backend for any model/transport failure (shown to the user)."""


class Backend:
    name = "base"      # short id, e.g. "ollama"
    label = "base"     # human-readable banner string

    def preflight(self) -> None:
        """Raise BackendError if the backend isn't ready (model missing, no API key…)."""

    def chat(self, messages, tools=None, think=None) -> dict:
        """Send the conversation; return {"content": str, "tool_calls": [...]}"""
        raise NotImplementedError

    @property
    def is_local(self) -> bool:
        """True for local models (GPU/keep_alive concerns apply)."""
        return False

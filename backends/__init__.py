"""Model backends. Pick one with config.json -> "provider"."""
from .base import Backend, BackendError
from .ollama_backend import OllamaBackend
from .claude_backend import ClaudeBackend

_REGISTRY = {
    "ollama": OllamaBackend,
    "claude": ClaudeBackend,
}


def get_backend(config: dict) -> Backend:
    provider = config.get("provider", "ollama")
    cls = _REGISTRY.get(provider)
    if cls is None:
        raise BackendError(
            f"Unknown provider '{provider}'. Supported: {', '.join(_REGISTRY)}. "
            f"Add a backend in backends/ and register it to support more.")
    return cls(config)

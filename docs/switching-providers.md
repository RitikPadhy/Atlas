# Switching the model provider

The agent talks only to a **Backend** (`backends/`), so the underlying model is
swappable without touching tools, skills, shortcuts, services, or guardrails.
You select one with `"provider"` in `config.json`.

**Current setup:** `"provider": "ollama"` — your local models (`qwen3:8b` brain +
`qwen2.5-coder:7b` coder) on your Mac. This is what runs today; nothing below is
active until you deliberately switch.

---

## Switching to the Anthropic (Claude) API — when you choose to

> ⚠️ The Claude API is **pay-per-use** and **separate from a Claude.ai subscription**.
> A Pro/Max plan does *not* include API access — you need an API key from
> console.anthropic.com (billed per token).

1. **Install the SDK** (optional dependency, only for this provider):
   ```sh
   pip install anthropic
   ```
2. **Get an API key** at console.anthropic.com, then export it:
   ```sh
   echo "export ANTHROPIC_API_KEY=sk-ant-..." >> ~/.zshrc
   source ~/.zshrc
   ```
3. **Add a `claude` block to `config.json`** (sits alongside the other keys):
   ```json
   "claude": {
     "model": "claude-opus-4-8",
     "max_tokens": 16000,
     "api_key_env": "ANTHROPIC_API_KEY"
   },
   ```
4. **Flip the provider** in `config.json`:
   ```json
   "provider": "claude"
   ```
5. Run `ai`. The banner will show the Claude model instead of the local ones.

**To switch back:** set `"provider": "ollama"`. (You can leave the `claude` block
and the env var in place — they're ignored while the provider is `ollama`.)

### Caveats when running on the Anthropic API
- **`ask_coder`** delegates to the *local* coder model — it needs Ollama running and
  isn't useful with a cloud brain (the cloud model codes directly). Harmless if unused.
- **`/think`** only affects the local `qwen3` brain; it's a no-op on the cloud backend.

---

## Adding a different provider (GPT, etc.)

1. Create `backends/<name>_backend.py` with a `Backend` subclass implementing
   `preflight()` and `chat(messages, tools, think) → {"content", "tool_calls"}`
   (translating to/from that provider's API shape).
2. Register it in `backends/__init__.py`.
3. Add any provider config block to `config.json` and set `"provider": "<name>"`.

Local-only concerns (GPU `keep_alive`, the `ask_coder` swap) automatically apply
only when a backend reports `is_local = True`.

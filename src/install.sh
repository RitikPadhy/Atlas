#!/usr/bin/env bash
# Installs the `ai` command by adding an alias to your shell rc file.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALIAS_LINE="alias ai='python3 \"$DIR/ai_agent.py\"'"

case "${SHELL:-}" in
  *zsh)  RC="$HOME/.zshrc" ;;
  *bash) RC="$HOME/.bashrc" ;;
  *)     RC="$HOME/.profile" ;;
esac

if grep -qF "$DIR/ai_agent.py" "$RC" 2>/dev/null; then
  echo "✓ Alias already present in $RC"
else
  printf '\n# AI Agent Center\n%s\n' "$ALIAS_LINE" >> "$RC"
  echo "✓ Added alias to $RC"
fi

echo "Run:  source $RC   (or open a new terminal), then type:  ai"

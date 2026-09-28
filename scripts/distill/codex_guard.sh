#!/usr/bin/env bash
# Stop Codex-backed distill workers once the Codex plan's weekly usage passes a cap (default 60%); Gemini workers keep going.
CAP=${1:-60}; export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"; cd "$(dirname "$0")"
while pgrep -f "distill.py run video --backend codex" >/dev/null; do
  u=$(python3 codex_usage.py 2>/dev/null | awk '{print int($1)}'); echo "$(date +%T) codex weekly usage ${u}%"
  if [ -n "$u" ] && [ "$u" -ge "$CAP" ]; then
    for p in $(pgrep -f "distill.py run video --backend codex"); do pkill -TERM -P "$p"; kill "$p"; done
    echo "cap ${CAP}% reached: stopped Codex video workers (keeps enforcing)"
  fi
  sleep 300
done

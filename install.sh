#!/usr/bin/env bash
# Hormozi Brain installer for macOS, Linux and Windows (WSL). Needs only python3 (3.9+).
#
#   ./install.sh                 link the skills into every AI agent found on this machine
#   ./install.sh --semantic      also enable meaning-based search (downloads ~200 MB of Python packages, once)
#   ./install.sh --copy          copy instead of symlink (for agents that don't follow symlinks)
#   ./install.sh --uninstall     remove everything this script added
#
# Claude Code users can instead run:  /plugin marketplace add aziznizomofficial/hormozi-brain
#                                     /plugin install hormozi-brain@hormozi-brain
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SKILLS=(hormozi hormozi-diagnose hormozi-offer hormozi-review)
MODE=link; SEMANTIC=0; UNINSTALL=0
for a in "$@"; do case "$a" in
  --copy) MODE=copy ;; --semantic) SEMANTIC=1 ;; --uninstall) UNINSTALL=1 ;;
  -h|--help) sed -n '2,10p' "$0"; exit 0 ;; *) echo "unknown option $a"; exit 1 ;; esac; done

command -v python3 >/dev/null || { echo "python3 is required (3.9 or newer)"; exit 1; }
python3 -c 'import sys, sqlite3; assert sys.version_info >= (3, 9); sqlite3.connect(":memory:").execute("create virtual table t using fts5(x)")' 2>/dev/null \
  || { echo "python3 must be 3.9+ with SQLite FTS5 (standard on macOS and current Linux)"; exit 1; }

# agent home → its skills folder (only agents that are installed get a link)
TARGETS=()
add() { [ -d "$1" ] && TARGETS+=("$2"); return 0; }
add "$HOME/.claude"            "$HOME/.claude/skills"             # Claude Code
add "$HOME/.agents"            "$HOME/.agents/skills"             # shared skills folder (Codex and others)
add "$HOME/.codex"             "$HOME/.codex/skills"              # Codex CLI
add "$HOME/.gemini"            "$HOME/.gemini/skills"             # Gemini CLI
add "$HOME/.gemini/antigravity-cli" "$HOME/.gemini/config/skills" # Antigravity CLI (agy)
add "$HOME/.cursor"            "$HOME/.cursor/skills"             # Cursor
add "$HOME/.config/opencode"   "$HOME/.config/opencode/skills"    # OpenCode
[ ${#TARGETS[@]} -eq 0 ] && TARGETS+=("$HOME/.agents/skills")

place() { # src dst
  if [ -L "$2" ] || [ -e "$2" ]; then
    if [ -L "$2" ] || [ -f "$2/.hormozi-brain" ]; then rm -rf "$2"; else echo "  skip $2 (exists and is not ours)"; return; fi
  fi
  if [ "$MODE" = copy ]; then cp -R "$1" "$2"; touch "$2/.hormozi-brain" 2>/dev/null || true; else ln -s "$1" "$2"; fi
  echo "  $2"
}
unplace() { if [ -L "$1" ] || [ -f "$1/.hormozi-brain" ]; then rm -rf "$1"; echo "  removed $1"; fi; }

if [ $UNINSTALL = 1 ]; then
  for t in "${TARGETS[@]}"; do for s in "${SKILLS[@]}"; do unplace "$t/$s"; done; done
  unplace "$HOME/.claude/agents/hormozi.md"; unplace "$HOME/.local/bin/hormozi"
  rm -rf "$ROOT/skills/hormozi/.venv" "$ROOT/skills/hormozi/.cache"; echo "done"; exit 0
fi

echo "Linking skills:"
for t in "${TARGETS[@]}"; do mkdir -p "$t"; for s in "${SKILLS[@]}"; do place "$ROOT/skills/$s" "$t/$s"; done; done
if [ -d "$HOME/.claude" ]; then mkdir -p "$HOME/.claude/agents"; place "$ROOT/agents/hormozi.md" "$HOME/.claude/agents/hormozi.md"; fi
mkdir -p "$HOME/.local/bin"; ln -sfn "$ROOT/skills/hormozi/scripts/hormozi" "$HOME/.local/bin/hormozi"; echo "  $HOME/.local/bin/hormozi (command)"

if [ $SEMANTIC = 1 ]; then echo "Enabling meaning-based search…"; python3 "$ROOT/skills/hormozi/scripts/hormozi.py" setup --semantic; fi
echo "Building the search index…"; python3 "$ROOT/skills/hormozi/scripts/hormozi.py" stats | tail -1
echo
echo "Done. Restart your AI tool, then ask e.g. \"/hormozi how do I raise prices without losing customers?\""
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) echo "Tip: add ~/.local/bin to your PATH to use the \`hormozi\` command directly." ;; esac

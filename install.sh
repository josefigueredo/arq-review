#!/usr/bin/env bash
# Install arq-review for Claude Code, Codex and Cursor.
#   ./install.sh
# Skills: ~/.agents/skills/<skill> points at this repo's skills/<skill>; ~/.claude/skills and ~/.codex/skills point
# at ../../.agents/skills/<skill>; Cursor reads ~/.agents/skills natively (same layout as WayOfWork and jira-kanban).
# CLI: ~/.local/bin/arq points at arq.py. Re-running is safe. A real file or directory with the same name is never
# replaced: the script stops with exit 1.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
case "${1:-}" in
  -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
  "") ;;
  *) echo "unknown argument: $1" >&2; exit 2 ;;
esac

link() {  # link <target> <path>: create or refresh a symlink, never replace a real file or directory
  if [ -e "$2" ] && [ ! -L "$2" ]; then
    echo "refusing to replace $2: it is not a symlink; move it away and re-run" >&2
    return 1
  fi
  mkdir -p "$(dirname "$2")"
  ln -sfn "$1" "$2"
}

status=0
for skill in arq-manager arq-architect; do
  link "$REPO/skills/$skill" "$HOME/.agents/skills/$skill" || exit 1
  for host in .claude .codex; do
    link "../../.agents/skills/$skill" "$HOME/$host/skills/$skill" || status=1
  done
done
chmod +x "$REPO/arq.py"
link "$REPO/arq.py" "$HOME/.local/bin/arq" || status=1
command -v python3 >/dev/null || { echo "note: python3 is not on PATH; arq needs it" >&2; status=1; }
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) echo "note: add ~/.local/bin to PATH to use arq" >&2 ;; esac
echo "skills: arq-manager, arq-architect (Claude Code, Codex, Cursor) -> $REPO/skills"
echo "cli: arq -> $REPO/arq.py"
exit "$status"

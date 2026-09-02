#!/bin/bash

set -e

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Home for config and Claude Code state. On Windows shells (Git Bash, MSYS2,
# Cygwin) that is USERPROFILE, which is what Python's Path.home() and Claude
# Code resolve ~ to there; HOME can point at another drive (a corporate roaming
# home) and would split the config between the bash and Python halves.
# Elsewhere HOME is the home. Uses bash 3.2 features only.
case "$(uname -s 2>/dev/null)" in
  MINGW*|MSYS*|CYGWIN*) OSB_HOME="$(cygpath -u "${USERPROFILE:-$HOME}" 2>/dev/null || printf '%s' "${USERPROFILE:-$HOME}")" ;;
  *) OSB_HOME="$HOME" ;;
esac
COMMANDS_DIR="$OSB_HOME/.claude/commands"

# Pull latest
if [ -d "$SKILL_DIR/.git" ]; then
  echo "Pulling latest changes..."
  git -C "$SKILL_DIR" pull
else
  echo "Not a git repo - skipping pull. Update the files in $SKILL_DIR manually."
fi

# Symlinked commands pick up git pull automatically.
# Copied commands (Windows without Developer Mode) need an explicit refresh.
echo "Updating slash commands..."
updated=0
for file in "$SKILL_DIR/commands/"*.md; do
  name=$(basename "$file")
  dest="$COMMANDS_DIR/$name"
  if [ -L "$dest" ]; then
    : # symlink - already current after git pull
  else
    cp "$file" "$dest"
    echo "  updated $name"
    updated=$((updated + 1))
  fi
done
[ "$updated" -gt 0 ] && echo "  $updated command(s) refreshed (copied, not symlinked)"

echo ""
echo "Done. Restart Claude Code to pick up the changes."

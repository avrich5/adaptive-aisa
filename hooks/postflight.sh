#!/usr/bin/env bash
# Stop hook for adaptive_aisa — backup project memory + B2 sync
[[ "$PWD" != *adaptive_aisa* ]] && exit 0
BACKUP_DIR=~/.claude/backups/adaptive_aisa
mkdir -p "$BACKUP_DIR"
TS=$(date +%Y%m%d_%H%M%S)
PROJ=~/adaptive_aisa
for FILE in CLAUDE.md README.md; do
  SRC="$PROJ/$FILE"
  [[ -f "$SRC" ]] && cp "$SRC" "$BACKUP_DIR/${FILE%.md}_${TS}.md"
done
for PREFIX in CLAUDE README; do
  ls -t "$BACKUP_DIR/${PREFIX}_"*.md 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null
done
B2=/opt/homebrew/bin/b2
BUCKET="andriy-home-services"
if [[ -x "$B2" ]]; then
  "$B2" sync --compare-versions size "$BACKUP_DIR/" "b2://$BUCKET/adaptive_aisa/" 2>/dev/null || true
fi
exit 0

#!/usr/bin/env bash
# SessionStart hook for adaptive_aisa
[[ "$PWD" != *adaptive_aisa* ]] && exit 0
CONTEXT=""
PROJ=~/adaptive_aisa
cd "$PROJ" 2>/dev/null || exit 0
BR=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
DIRTY=$(git status --porcelain 2>/dev/null | wc -l | tr -d " ")
LAST=$(git log -1 --format="%h %s" 2>/dev/null)
CONTEXT+="## adaptive_aisa pre-flight\n**Git**: branch=${BR:-none}, dirty=${DIRTY}, last=[${LAST}]\n"
# dataset state
PTS=$(ls data/*.parquet 2>/dev/null | wc -l | tr -d " ")
LASTREP=$(ls -t reports/*.md 2>/dev/null | head -1)
CONTEXT+="**Dataset**: parquet_files=${PTS}; last_report=[${LASTREP:-none}]\n"
CONTEXT+="**Rules**: frv GitLab READ-ONLY; write only to avrich5/adaptive-aisa\n"
printf "{\"hookSpecificOutput\":{\"hookEventName\":\"SessionStart\",\"additionalContext\":\"%s\"}}" \
  "$(echo -e "$CONTEXT" | sed "s/\"/\\\\\"/g" | tr "\n" " ")"

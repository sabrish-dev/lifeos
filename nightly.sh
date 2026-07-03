#!/bin/zsh
# LifeOS nightly — the dream that runs while Sabrish sleeps.
# 1. ingest  (grow the map + stamp last_touched)
# 2. dreamer (structural gap-hunt: world + tool)
# 3. insight (LLM reasoning layer → revelations, via claude headless)
# Scheduled by ~/Library/LaunchAgents/com.lifeos.dreamer.plist
#
# Hardened 2026-07-02 (Don't inflate or fabricate — applied to the tool itself):
#   - insight is written to a TMP file, VALIDATED, then atomically moved.
#     A failed/blank/"Not logged in" run can never masquerade as (or clobber)
#     a real morning report.
#   - the claude call has a hard 15-minute timeout (2026-07-02 run hung 2h11m).
#   - failures leave a dated marker in logs/ so the morning hook can say
#     "the Dreamer didn't dream" instead of showing garbage.
set -uo pipefail

LIFEOS="/Users/sabrishiyer/brain/10-os/lifeos"
PY="/opt/anaconda3/bin/python3"
CLAUDE="/Users/sabrishiyer/.local/bin/claude"
cd "$LIFEOS" || exit 1
mkdir -p logs dreams insights
DATE=$(date +%F)
LOG="logs/nightly.log"

echo "=== LifeOS nightly $(date) ===" >> "$LOG"
"$PY" ingest.py            >> "$LOG" 2>&1
"$PY" dreamer.py --date "$DATE" >> "$LOG" 2>&1

# Insight — reasoning layer. Only if the claude CLI is present.
if [[ -x "$CLAUDE" ]]; then
  read -r -d '' PROMPT <<EOF
You are the reasoning layer of Sabrish Iyer's LifeOS "Dreamer". Below is tonight's
structural dream brief plus his root directive. Produce the morning INSIGHT.

Rules: NOT a summary. Fused REVELATIONS — name which separate gaps are actually one
gap, which world-gap and tool-gap share a shape, and the single most-avoided thing.
Prioritise findings marked (new) over long-persisting ones; for persisting findings,
the streak itself is the story — name what N days of repetition means. Run every
revelation through the hierarchy identity > ANTARA > ṛta (identity outranks
all). Attach exactly ONE action to each. End with a "## Proposed edges" list
(mirrors / conflicts_with / avoided) for world-map.json. Output GitHub-flavored
markdown only, starting with: # 🌅 Insight — $DATE

GROUNDING (hard rule — ऋतम्, not the legible): every factual claim in every
revelation must trace to a specific finding line in tonight's brief or a line
of the root directive — QUOTE the line (or its exact fragment) when you use it.
Make NO claims about the world beyond the brief + the root directive. If a
pattern is your inference rather than a quoted fact, mark it "(inference)".
If the brief is too thin to support a revelation, say so — a smaller honest
insight beats a grand fabricated one.

Reflexive law: the Dreamer must hunt gaps in the tool, not only the life.

===== TONIGHT'S DREAM BRIEF =====
$(cat "dreams/$DATE.md")

===== ROOT DIRECTIVE: identity (outranks all) =====
$(sed -n '1,45p' ../../00-soul/looking-at-the-man-in-the-mirror.md)
EOF

  TMP="insights/.$DATE.tmp.md"
  # Hard 15-min timeout (no coreutils timeout on this Mac → python wrapper).
  "$PY" - "$CLAUDE" "$TMP" <<'PYEOF' "$PROMPT" 2>> "$LOG"
import subprocess, sys
claude, tmp, prompt = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    r = subprocess.run([claude, "-p", prompt], capture_output=True, text=True, timeout=900)
    out = r.stdout
except subprocess.TimeoutExpired:
    sys.stderr.write("insight: TIMEOUT after 900s\n"); sys.exit(2)
open(tmp, "w").write(out)
sys.exit(r.returncode)
PYEOF
  RC=$?

  # Validate: exists, starts with the insight header, is substantive, no auth error.
  if [[ $RC -eq 0 && -s "$TMP" ]] \
     && head -1 "$TMP" | grep -q '^# 🌅 Insight' \
     && ! grep -qi 'not logged in\|please run /login' "$TMP" \
     && [[ $(wc -l < "$TMP") -ge 10 ]]; then
    mv "$TMP" "insights/$DATE.md"
    rm -f "logs/insight-failed-$DATE"
    echo "insight -> insights/$DATE.md (validated)" >> "$LOG"
  else
    echo "WARN: insight FAILED validation (rc=$RC) — structural dream still written; previous insights untouched" >> "$LOG"
    [[ -s "$TMP" ]] && head -3 "$TMP" >> "$LOG"
    rm -f "$TMP"
    date > "logs/insight-failed-$DATE"
  fi
else
  echo "WARN: claude CLI absent; structural dream only" >> "$LOG"
  date > "logs/insight-failed-$DATE"
fi
echo "=== done $(date) ===" >> "$LOG"

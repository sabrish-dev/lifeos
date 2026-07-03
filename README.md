# 🌌 LifeOS — A Second Mind That Dreams While You Sleep

> A persistent outboard subconscious. It watches everything its keeper touches,
> builds a living world-map, dreams against it nightly, and delivers morning
> **revelations** — not summaries — measured against his own frameworks
> (ANTARA · the identity doc · ṛta as the measure).

**This repo is the machinery only.** The world-map, dreams, insights, and logs
are personal data and are gitignored — the code is portable, the life is not.

## The loop

| Part | File | What it does |
|---|---|---|
| **Subconscious** | `ingest.py` | Grows `world-map.json` from Claude Code memory dirs + brain-vault links; stamps `last_touched` from real file mtimes. Idempotent, never fabricates. |
| **Dreamer** | `dreamer.py` | Deterministic structural pass over the map. Hunts gaps in **the world** (avoidance, ṛta-drift, unmanaged wounds, projects without a why) *and* in **the tool itself** (blind detectors, thin coverage, un-ingested memories — the reflexive law). Dream-memory via `dreams/.streaks.json` tags every finding `(new)` or `(day N)`. Writes `dreams/<date>.md`. |
| **Insight** | `nightly.sh` → `claude -p` | LLM reasoning layer fuses the dream brief into revelations + one action each, run through the hierarchy identity > ANTARA > ṛta. **Grounded**: every claim must quote its source line from the brief; inferences are marked. Output validated (header / length / no auth error) and atomically moved — a failed run can never masquerade as a report. |
| **Loop** | launchd `com.lifeos.dreamer.plist` (03:00, fires on wake) | act → map updates → next dream goes deeper. A SessionStart hook surfaces the latest insight at the top of every session — the day starts from the report — and stamps `logs/attention.log` on read. |

## Design laws

1. **The reflexive law** — the Dreamer must hunt gaps in the tool, not only the
   life. Self-audit is not optional; it's how the tool stays true.
2. **ऋतम्, not the legible** — validate results, not artifacts. A file existing
   is not an insight existing. (Learned the hard way: night one wrote
   "Not logged in" as the morning report and called it success.)
3. **Measure nature, not visible form** — mtime sees edits, not attention;
   until `attention.log` is folded into ingest, avoidance flags are questions,
   not verdicts.
4. **Don't inflate or fabricate** — grounding rule in the insight prompt;
   smaller honest insight beats a grand fabricated one.

## Ops

```bash
python3 ingest.py --dry-run      # preview map growth
python3 dreamer.py               # write tonight's dream brief
./nightly.sh                     # full loop by hand
launchctl list | grep lifeos     # is the night job loaded
python3 validate_world_map.py    # schema check
```

Schema for the world-map: `schema.md`.

## Open builds

- ingest consumes `attention.log` → `last_touched` (eyes for attention, not edits)
- goal nodes + `serves` wiring at ingest time (kill manufactured "project-without-why" noise)
- `due`/horizon field + *approaching-undreamt* detector (the Dreamer currently only hunts backwards)

#!/usr/bin/env python3
"""The Dreamer — walks the world-map and hunts gaps. Two domains:

  1. WORLD gaps  — in Sabrish's life (goals with no vehicle, drift from ṛta,
     unmanaged wounds, over-extension, mirror candidates, avoidance).
  2. TOOL gaps   — in LifeOS itself (ingest not built, blind detectors from
     unused fields, un-ingested memories, orphan directives, thin coverage).

Deterministic structural pass → writes a "dream brief" to dreams/<date>.md.
The LLM reasoning layer (a nightly Claude routine, or Claude now) reads the
brief + the directives and turns findings into Insight (revelations + actions),
and may propose new mirrors/conflicts/avoided edges back into the map (the Loop).

Run: python3 dreamer.py [--date YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
MAP = HERE / "world-map.json"
MEMORY_INDEX = Path.home() / ".claude/projects/-Users-sabrishiyer/memory/MEMORY.md"
DREAMS = HERE / "dreams"
STREAKS = DREAMS / ".streaks.json"  # the Dreamer's memory of past dreams
DEFERRALS = DREAMS / ".deferrals.json"  # {normalized-finding-key: reason} — explicit, dated excuses
BLOCKER_DAYS = 3  # Insight 2026-07-04 Rev 1: a finding unchanged this long is a blocker, not a report

STOP = {"with", "the", "own", "and", "against", "a", "of", "to", "it", "not", "in", "on", "no"}


def load_map():
    d = json.loads(MAP.read_text())
    nodes = {n["id"]: n for n in d["nodes"]}
    return d, nodes, d["edges"]


def out_edges(edges, i):
    return [e for e in edges if e["from"] == i]


def in_edges(edges, i):
    return [e for e in edges if e["to"] == i]


def is_project(n):
    return n["type"] == "project"


# ---------------- WORLD GAPS ----------------
def world_gaps(nodes, edges, today):
    g = []
    t0 = __import__("datetime").date.fromisoformat(today)

    # avoidance — evidence law (Insight 2026-07-05 Rev 1): mtime alone cannot
    # distinguish "abandoned" from "read daily, never edited". Only nodes with
    # real attention data (last_attention) produce blocker-grade findings;
    # mtime-only staleness is reported as UNVERIFIED inference, never a blocker.
    for n in nodes.values():
        lt = n.get("last_touched")
        if lt and n.get("salience", 0) >= 0.6:
            days = (t0 - __import__("datetime").date.fromisoformat(lt)).days
            if days >= 30:
                if n.get("last_attention"):
                    g.append(("avoidance", f"'{n['name']}' untouched {days}d despite attention-tracking (salience {n['salience']}) — evidenced, last attention {n['last_attention']}."))
                else:
                    g.append(("avoidance-unverified", f"'{n['name']}' not edited in {days}d (salience {n['salience']}) — mtime-only: inference, not fact; no attention data for this node."))

    for i, n in nodes.items():
        if n["type"] == "goal" and not [e for e in in_edges(edges, i) if e["rel"] == "serves"]:
            g.append(("goal-without-vehicle", f"Goal '{n['name']}' has no project serving it — a stated want with no vehicle."))
        if is_project(n) and n.get("status") in ("active", "blocked"):
            serves = [e for e in out_edges(edges, i) if e["rel"] in ("serves", "part_of")]
            if not serves:
                g.append(("project-without-why", f"Active project '{n['name']}' serves no goal — building without a named why (drift check)."))
        if n.get("rta_alignment") in ("drifting", "tension"):
            g.append(("rta-drift", f"'{n['name']}' flagged {n['rta_alignment']} vs ṛta (salience {n.get('salience','?')})."))
        if n["type"] == "wound":
            managed = [e for e in in_edges(edges, i) if e["rel"] in ("serves", "measures")]
            if not managed:
                g.append(("unmanaged-wound", f"Wound '{n['name']}' has no value/resolve managing it."))
        if is_project(n) and n.get("salience", 0) >= 0.7:
            measured = [e for e in in_edges(edges, i) if e["rel"] == "measures"]
            if not measured:
                g.append(("unmeasured-high-salience", f"High-salience '{n['name']}' is measured by no directive/value."))
        if n.get("avoided_since"):
            g.append(("avoidance", f"'{n['name']}' avoided since {n['avoided_since']}."))

    # (venture-count cap removed by Sabrish, 2026-07-01 — no over-extension flag)

    # mirror candidates: unrelated nodes sharing a shape token
    edged = {(e["from"], e["to"]) for e in edges} | {(e["to"], e["from"]) for e in edges}
    shaped = [(i, set(t for t in re.split(r"[-_]", n["shape"]) if t not in STOP and len(t) >= 4))
              for i, n in nodes.items() if n.get("shape")]
    for a in range(len(shaped)):
        for b in range(a + 1, len(shaped)):
            ia, ta = shaped[a]; ib, tb = shaped[b]
            shared = ta & tb
            if shared and (ia, ib) not in edged:
                g.append(("mirror-candidate", f"'{nodes[ia]['name']}' & '{nodes[ib]['name']}' share shape [{', '.join(sorted(shared))}] but aren't linked."))

    # orphans (world nodes with no edges)
    touched = {e["from"] for e in edges} | {e["to"] for e in edges}
    for i, n in nodes.items():
        if i not in touched and n["type"] in ("person", "project", "goal", "idea", "wound"):
            g.append(("world-orphan", f"'{n['name']}' sits disconnected from the map."))
    return g


# ---------------- TOOL GAPS (self-audit) ----------------
def tool_gaps(meta, nodes, edges):
    t = []
    N = len(nodes)

    # ingest autonomy — honest self-audit against the actual launchd job
    if not (Path.home() / "Library/LaunchAgents/com.lifeos.dreamer.plist").exists():
        t.append(("ingest-not-scheduled", "ingest.py + dreamer run by hand — no nightly job. The 'always-on' promise is unmet."))

    # field coverage → blind detectors
    for field, why in [("last_touched", "the avoidance/'N days' revelation cannot fire"),
                        ("avoided_since", "the explicit avoidance detector has nothing to read"),
                        ("shape", "mirror-matching runs on a thin sample")]:
        cov = sum(1 for n in nodes.values() if n.get(field))
        if cov / N < 0.3:
            t.append(("blind-detector", f"Only {cov}/{N} nodes have '{field}' → {why}."))

    # orphan directives/values — not wired, so not doing their job in the tool
    touched = {e["from"] for e in edges} | {e["to"] for e in edges}
    orphan_dv = [nodes[i]["name"] for i in nodes if i not in touched and nodes[i]["type"] in ("directive", "value", "ritual")]
    if orphan_dv:
        t.append(("orphan-directive", f"Directives/values not wired into any reasoning: {', '.join(orphan_dv)}."))

    # thin type coverage
    by_type = Counter(n["type"] for n in nodes.values())
    for typ, floor in [("wound", 4), ("goal", 4), ("ritual", 2)]:
        if by_type.get(typ, 0) < floor:
            t.append(("thin-coverage", f"Only {by_type.get(typ,0)} '{typ}' node(s) — the map is almost certainly under-covering this; the Dreamer can't hunt what isn't there."))

    # inferred nodes need confirmation
    inf = [n["name"] for n in nodes.values() if n.get("confidence") == "inferred"]
    if inf:
        t.append(("needs-confirmation", f"Inferred (unconfirmed) nodes to verify with Sabrish: {', '.join(inf)}."))

    # memory index vs map — un-ingested memories
    if MEMORY_INDEX.exists():
        mem = set(re.findall(r"\]\(([a-z0-9-]+)\.md\)", MEMORY_INDEX.read_text()))
        linked = set()
        for n in nodes.values():
            for l in n.get("links", []):
                linked.add(Path(l).stem)
        missing = sorted(mem - linked)
        if missing:
            t.append(("un-ingested-memory", f"{len(missing)} memories exist with no node in the map: {', '.join(missing)}."))

    # the Dreamer's own limits (kept honest: dream-memory + nightly LLM layer landed 2026-07-02..04)
    t.append(("dreamer-limits", "Structural pass limits: exact-token shape matching only — no fuzzy semantic mirror detection at this layer (the nightly LLM Insight covers some of it); attention-stamping depends on events being logged to attention.log."))
    return t


def annotate_streaks(findings, date):
    """Dream memory: tag each finding (new) or (day N). Keyed on the finding with
    digits normalised (so 'not edited in 36d' == 'in 37d'). Streaks reset when a
    finding disappears — a gap that heals and reopens is news, not noise."""
    norm = lambda kind, msg: f"{kind}|{re.sub(r'\d+', '#', msg)}"
    state = json.loads(STREAKS.read_text()) if STREAKS.exists() else {}
    out, new_state = [], {}
    for kind, msg in findings:
        k = norm(kind, msg)
        first = state.get(k, date)
        new_state[k] = first
        days = (dt.date.fromisoformat(date) - dt.date.fromisoformat(first)).days + 1
        tag = "(new)" if first == date else f"(day {days})"
        out.append((kind, f"{msg} {tag}"))
    STREAKS.write_text(json.dumps(new_state, indent=1, ensure_ascii=False) + "\n")
    # new findings first — they are tonight's actual news
    return sorted(out, key=lambda f: 0 if f[1].endswith("(new)") else 1)


def blockers(findings):
    """Escalation (Insight 2026-07-04): findings at (day >= BLOCKER_DAYS), minus explicit
    deferrals, stop being reports and become blockers — silent re-dating is forbidden.
    Unverified (mtime-only) findings are inference, never blockers (Insight 2026-07-05)."""
    norm = lambda kind, msg: f"{kind}|{re.sub(r'\d+', '#', re.sub(r' \((?:new|day \d+)\)$', '', msg))}"
    deferred = json.loads(DEFERRALS.read_text()) if DEFERRALS.exists() else {}
    out = []
    for kind, msg in findings:
        if kind == "avoidance-unverified":
            continue
        m = re.search(r"\(day (\d+)\)$", msg)
        if m and int(m.group(1)) >= BLOCKER_DAYS and norm(kind, msg) not in deferred:
            out.append((kind, msg))
    return out


def write_dream(date, world, tool, meta, nodes, edges):
    DREAMS.mkdir(exist_ok=True)
    p = DREAMS / f"{date}.md"
    blk = blockers(world + tool)
    L = [f"# 🌙 Dream — {date}", "",
         f"World-map v{meta['version']} · {len(nodes)} nodes / {len(edges)} edges.",
         "Structural pass. The reasoning layer turns these into Insight (revelations + actions) and may propose edges back."]
    if blk:
        L += ["", f"## ⚠️ BLOCKERS — unchanged ≥{BLOCKER_DAYS} days (not reports anymore)",
              f"These have been re-dated nightly without movement. Each MUST leave this list via its one named action being DONE, or an explicit entry in `dreams/.deferrals.json` ({{key: reason}}). The reasoning layer must lead with these."]
        L += [f"- **[{k}]** {m}" for k, m in blk]
    verified = [(k, m) for k, m in world if k != "avoidance-unverified"]
    unverified = [(k, m) for k, m in world if k == "avoidance-unverified"]
    L += ["", "## I. Gaps in the world"]
    for kind, msg in verified:
        L.append(f"- **[{kind}]** {msg}")
    if unverified:
        L += ["", "## I-b. Unverified (mtime-only — inference, NOT evidence)",
              "Evidence law (Insight 2026-07-05): mtime cannot distinguish 'abandoned' from 'read daily, never edited'. These are staleness inferences awaiting attention data — never blockers, never accusations. The fix is the attention-stamp, not the life."]
        for kind, msg in unverified:
            L.append(f"- **[{kind}]** {msg}")
    L += ["", "## II. Gaps in the tool (self-audit)"]
    for kind, msg in tool:
        L.append(f"- **[{kind}]** {msg}")
    L += ["", "## III. Directives to dream against",
          "Run the findings above through, in order of authority: **identity** (outranks all) → **ANTARA** → **ṛta** (the measure) → resolves. Ask of each finding: *what does this cost the identity, and where is the drift from ṛta?*",
          "", "## IV. For the reasoning layer",
          "Fuse findings into **revelations** (not a list): which separate gaps are one gap; which world-gap and tool-gap are the same shape; the single most-avoided thing. Attach one action each. Then propose any `mirrors`/`conflicts_with`/`avoided` edges to add to `world-map.json`."]
    p.write_text("\n".join(L) + "\n")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="today")
    a = ap.parse_args()
    date = a.date if a.date != "today" else __import__("datetime").date.today().isoformat()

    d, nodes, edges = load_map()
    world = world_gaps(nodes, edges, date)
    tool = tool_gaps(d["meta"], nodes, edges)
    # dream memory: annotate streaks across both domains, then split back
    both = annotate_streaks(world + tool, date)
    wkinds = {"avoidance", "avoidance-unverified", "goal-without-vehicle", "project-without-why",
              "rta-drift", "unmanaged-wound", "unmeasured-high-salience", "mirror-candidate", "world-orphan"}
    world = [f for f in both if f[0] in wkinds]
    tool = [f for f in both if f[0] not in wkinds]
    p = write_dream(date, world, tool, d["meta"], nodes, edges)

    print(f"🌙 dream written → {p}")
    print(f"   world gaps: {len(world)}   tool gaps: {len(tool)}")
    print("   world:", Counter(k for k, _ in world))
    print("   tool :", Counter(k for k, _ in tool))


if __name__ == "__main__":
    main()

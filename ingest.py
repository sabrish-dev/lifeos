#!/usr/bin/env python3
"""The Subconscious ingest — the always-on part. Grows the world-map from real
sources without fabricating.

Sources: ALL Claude Code project-memory dirs (~/.claude/projects/*/memory) +
the brain vault via node links. (Claude app memory is server-side — no local
file to ingest.)

Phase B — GROW/ATTACH: for each memory, resolve to an existing node (exact slug
  or ALIAS) and attach it as provenance; else create a node
  (feedback->value, project->project, reference->idea; user skipped).
Phase A — STAMP: set last_touched = newest mtime among each node's linked
  files/dirs (real "when you last touched it" — unblocks the avoidance detector).

Idempotent. Never overwrites hand-authored name/summary/salience.
Run: python3 ingest.py [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
MAP = HERE / "world-map.json"
BRAIN_ROOT = HERE.parent.parent
CLAUDE_PROJECTS = Path.home() / ".claude/projects"
MEM_DIRS = sorted(p for p in CLAUDE_PROJECTS.glob("*/memory") if p.is_dir())

TYPE_MAP = {"feedback": "value", "project": "project", "reference": "idea"}  # user -> skip
# secondary/duplicate memory slugs -> the existing node they enrich (attach, don't duplicate)
ALIAS = {
    "project_quixar_engagement": "quixar",
    "quixar-founder-branding-refs": "quixar",
    "gully-labs-deck": "gully-labs",
    "project_fractalseo": "fractal-seo",
    "calibration_predicted_direction": "fractal-seo",
    "sc_leads_2026_05_21": "fractal-seo",
    "project_saravana_consultancy": "saravana",
    "project_proposals_qr": "saravana",
    "project_content_strategy": "saravana",
    "feedback_saravana_tool_philosophy": "asteria-kernel",
    "agent_orchestration": "asteria-kernel",
}
WIKILINK = re.compile(r"\[\[([a-z0-9-]+)")
FM_FIELD = re.compile(r"^(?:\s*)(name|description|type)\s*:\s*(.+?)\s*$", re.M)


def mtime_date(p: Path) -> str | None:
    try:
        return dt.date.fromtimestamp(p.stat().st_mtime).isoformat()
    except OSError:
        return None


def mem_path(slug: str) -> Path | None:
    for d in MEM_DIRS:
        p = d / f"{slug}.md"
        if p.exists():
            return p
    return None


def resolve(link: str) -> Path | None:
    link = link.strip()
    if link.startswith("~") or link.startswith("/"):
        p = Path(link).expanduser()
        return p if p.exists() else None
    if link.endswith(".md"):
        p = BRAIN_ROOT / link
        return p if p.exists() else None
    return mem_path(link)


def parse_memory(p: Path) -> dict:
    txt = p.read_text()
    fm = dict(FM_FIELD.findall(txt.split("---", 2)[1])) if txt.startswith("---") else {}
    body = txt.split("---", 2)[2] if txt.startswith("---") else txt
    return {"slug": p.stem, "name": fm.get("name") or p.stem, "desc": fm.get("description", ""),
            "type": fm.get("type", ""), "links": WIKILINK.findall(body), "mtime": mtime_date(p)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    d = json.loads(MAP.read_text())
    nodes = {n["id"]: n for n in d["nodes"]}
    edges = d["edges"]
    edgeset = {(e["from"], e["to"], e["rel"]) for e in edges}
    stem2id = {}
    for n in d["nodes"]:
        stem2id[n["id"]] = n["id"]
        for l in n.get("links", []):
            stem2id[Path(l.rstrip("/")).name.replace(".md", "")] = n["id"]

    created, attached, edged = [], 0, 0
    memories = [m for md in MEM_DIRS for f in sorted(md.glob("*.md"))
                if f.name != "MEMORY.md" for m in [parse_memory(f)]]

    # ---- Phase B: attach-or-create ----
    for m in memories:
        target = stem2id.get(m["slug"]) or ALIAS.get(m["slug"])
        if target and target in nodes:                       # attach as provenance
            n = nodes[target]
            if m["slug"] not in n.get("links", []):
                attached += 1
                if not a.dry_run:
                    n.setdefault("links", []).append(m["slug"])
            stem2id[m["slug"]] = target
        elif m["slug"] not in stem2id and m["type"] in TYPE_MAP:   # create
            ntype = TYPE_MAP[m["type"]]
            node = {"id": m["slug"], "type": ntype, "name": m["name"], "summary": m["desc"][:200],
                    "salience": 0.3, "links": [m["slug"]], "confidence": "stated",
                    "tags": ["ingested", m["type"]]}
            if ntype == "project":
                node["status"] = "active"
            created.append(node)
            if not a.dry_run:
                d["nodes"].append(node); nodes[node["id"]] = node
            stem2id[m["slug"]] = m["slug"]

    # wire relates_to from every memory's [[links]]
    for m in memories:
        src = stem2id.get(m["slug"])
        if not src:
            continue
        for tgt_slug in m["links"]:
            tgt = stem2id.get(tgt_slug)
            if tgt and tgt != src and (src, tgt, "relates_to") not in edgeset \
               and (src, tgt, "serves") not in edgeset and (tgt, src, "serves") not in edgeset:
                edgeset.add((src, tgt, "relates_to")); edged += 1
                if not a.dry_run:
                    edges.append({"from": src, "to": tgt, "rel": "relates_to"})

    # ---- Phase A: stamp last_touched (after attach, so new links count) ----
    stamped = 0
    for n in d["nodes"]:
        dates = [x for l in n.get("links", []) if (r := resolve(l)) and (x := mtime_date(r))]
        if dates and n.get("last_touched") != max(dates):
            stamped += 1
            if not a.dry_run:
                n["last_touched"] = max(dates)

    cov = sum(1 for n in d["nodes"] if n.get("last_touched")) / len(d["nodes"])
    print(f"{'[dry-run] ' if a.dry_run else ''}ingest complete")
    print(f"  memory dirs scanned: {len(MEM_DIRS)}  ({sum(1 for _ in memories)} memories)")
    print(f"  Phase B — attached to existing: {attached}   created: {len(created)} {[n['id'] for n in created]}")
    print(f"           relates_to edges wired: {edged}")
    print(f"  Phase A — last_touched stamped: {stamped}  (coverage {cov:.0%})")
    if not a.dry_run:
        MAP.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
        print(f"  saved -> {MAP}")


if __name__ == "__main__":
    main()

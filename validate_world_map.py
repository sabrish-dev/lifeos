#!/usr/bin/env python3
"""Validate + summarise the LifeOS world-map. Run: python3 validate_world_map.py"""
import json
import sys
from collections import Counter
from pathlib import Path

MAP = Path(__file__).parent / "world-map.json"


def main() -> int:
    data = json.loads(MAP.read_text())
    nodes = {n["id"]: n for n in data["nodes"]}
    edges = data["edges"]
    meta = data["meta"]

    errors = []
    # duplicate ids
    seen = Counter(n["id"] for n in data["nodes"])
    errors += [f"duplicate node id: {i}" for i, c in seen.items() if c > 1]
    # edge endpoints resolve
    for e in edges:
        for end in ("from", "to"):
            if e[end] not in nodes:
                errors.append(f"dangling edge {end}: {e['from']}->{e['to']} ({e['rel']}) missing '{e[end]}'")
        if e["rel"] not in meta["edge_rels"]:
            errors.append(f"unknown rel: {e['rel']} on {e['from']}->{e['to']}")
    # node type sanity
    for n in data["nodes"]:
        if n["type"] not in meta["node_types"]:
            errors.append(f"unknown node type: {n['type']} on {n['id']}")

    by_type = Counter(n["type"] for n in data["nodes"])
    by_conf = Counter(n.get("confidence", "?") for n in data["nodes"])
    # connectivity: nodes with no edges
    touched = {e["from"] for e in edges} | {e["to"] for e in edges}
    orphans = [i for i in nodes if i not in touched]
    # gap-hunt readiness signals
    shapes = Counter(n["shape"] for n in data["nodes"] if n.get("shape"))
    dup_shapes = {s: c for s, c in shapes.items() if c > 1}
    drifting = [n["id"] for n in data["nodes"] if n.get("rta_alignment") in ("drifting", "tension")]

    print(f"world-map v{meta['version']}  ({MAP})")
    print(f"  nodes: {len(nodes)}   edges: {len(edges)}")
    print(f"  by type: {dict(by_type)}")
    print(f"  confidence: {dict(by_conf)}")
    print(f"  orphan nodes (no edges): {orphans or 'none'}")
    print(f"  repeated shapes (mirror candidates): {dup_shapes or 'none'}")
    print(f"  ṛta drift/tension flags: {drifting or 'none'}")
    if errors:
        print("\n  ✗ ERRORS:")
        for e in errors:
            print("    -", e)
        return 1
    print("\n  ✓ graph is internally consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

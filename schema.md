---
title: LifeOS Subconscious — World-Map Schema
type: lifeos-schema
status: v0.1 seed
updated: 2026-06-30
---

# 🕸️ The World-Map — Schema

The substrate of [[lifeos-second-mind|LifeOS]]. A graph the **Dreamer** loads and walks. Nodes are the things in Sabrish's world; edges are how they link. Stored in `world-map.json`. The brain vault + memory index is the seed; ingest grows it 24/7.

## Node types
**Core five** (Sabrish's spec): `person` · `project` · `goal` · `idea` · `wound`.
**Structural** (so the Dreamer can run + measure): `directive` (ANTARA, identity, resolves, ṛta — what it runs against) · `value` (operating principles) · `ritual` (The Mirror).

`subtype` refines: project → `venture | engagement | tool`; person → `self | family | friend | founder | collaborator | contact`.

## Node fields
| field | meaning |
|---|---|
| `id` | kebab-case unique key |
| `type` / `subtype` | from above |
| `name`, `summary` | label + one-line |
| `status` | active / paused / idea / blocked / live / done |
| `salience` | 0–1 importance (Dreamer prioritises high) |
| `shape` | archetype/pattern string — lets the Dreamer match *"two unrelated things secretly the same"* (esp. wounds, ideas) |
| `rta_alignment` | `aligned / drifting / tension / unknown` — fuels the **drift-from-ṛta** check |
| `avoided_since` | date — fuels *"you've avoided this N days"* |
| `last_touched` | date |
| `links` | brain files / memory slugs / project dirs |
| `confidence` | `stated` (grounded) or `inferred` (flagged; never fabricate, esp. wounds) |

## Edge vocabulary
`from → to (rel)`. Relationships: `owns` · `collaborates_with` · `contact_on` · `friend_of` · `family_of` · `serves` (X advances Y) · `part_of` · `derives_from` · `deploys_on` (anchor) · `feeds` (data/tool) · `measures` (directive→node) · `outranks` (hierarchy) · `dreams_in` · `mirrors` (same `shape`) · `conflicts_with` · `blocks` · `avoided` · `relates_to` (generic link, from ingested [[wikilinks]]).

## Ingest (the always-on part)
`ingest.py` grows the map from real sources — **all 4 Claude Code project-memory dirs** (`~/.claude/projects/*/memory`) + the brain vault. (Claude app memory is server-side — nothing local to ingest.) Secondary/duplicate memories attach to the node they enrich (via an ALIAS map) instead of duplicating. Two phases: **(A) stamp** `last_touched` on every node from the newest mtime of its linked files/dirs (real last-touch signal, no fabrication); **(B) grow** — create nodes for un-ingested memories (feedback→`value`, project→`project`, reference→`idea`; `user` folds into self) and wire `relates_to` edges from their `[[links]]`. Idempotent: updates never overwrite hand-authored `name`/`summary`/`salience`.

## How the Dreamer uses it
- **What's missing** → expected edges absent (a goal with no serving project; a project with no goal).
- **What contradicts** → `conflicts_with`, or a node `tension` vs a `directive` that `measures` it.
- **Said you'd do and didn't** → `goal`/resolve `status` + `avoided_since`.
- **Two things secretly the same** → matching `shape` across unrelated nodes → propose a `mirrors` edge.
- **Drift from ṛta** → `rta_alignment: drifting/tension`, weighted by `salience`.

Every dream may *add* `mirrors`/`conflicts_with`/`avoided` edges back — the map deepens each cycle (the Loop).

#!/usr/bin/env python3
"""
generate_obsidian_links.py
Adam Framework — Obsidian Graph Generator

Reads your nmem neural graph (SQLite) and writes Obsidian-compatible
wikilink files into your vault so the Obsidian graph view reflects
what Adam actually knows.

Usage:
    python tools\generate_obsidian_links.py
    python tools\generate_obsidian_links.py --vault C:\MyVault --db C:\path\to\default.db
    python tools\generate_obsidian_links.py --dry-run
    python tools\generate_obsidian_links.py --min-weight 0.5

Output:
    {vault}\adam-graph\      <-- new folder, won't touch your existing files
        _index.md            <-- summary: total nodes, edges, top concepts
        TurfTracker.md       <-- one file per concept, with [[wikilinks]]
        AJSupplyCo.md
        ...
"""

import sqlite3
import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ── defaults ──────────────────────────────────────────────────────────────────
DEFAULT_DB    = r"C:\Users\ajsup\.neuralmemory\brains\default.db"
DEFAULT_VAULT = r"C:\AdamsVault"
GRAPH_FOLDER  = "adam-graph"
MIN_WEIGHT_DEFAULT  = 0.4
MAX_LINKS_PER_NODE  = 30
MIN_CONNECTIONS     = 2

MEANINGFUL_TYPES = {"related_to", "involves", "contains", "leads_to", "caused_by", "co_occurs"}
INCLUDE_TYPES    = {"concept", "entity", "state"}

# ── helpers ───────────────────────────────────────────────────────────────────

def sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    name = name.strip('. ')
    return name[:100] if name else "unnamed"

def slugify_content(content: str) -> str:
    content = re.sub(r'^doc_train:', '', content)
    content = re.sub(r'^workspace[/\\]', '', content)
    return content.strip()

def relationship_label(synapse_type: str) -> str:
    labels = {
        "related_to": "Related To",
        "involves":   "Involves",
        "contains":   "Contains",
        "leads_to":   "Leads To",
        "caused_by":  "Caused By",
        "co_occurs":  "Co-occurs With",
        "after":      "Comes After",
        "before":     "Comes Before",
        "felt":       "Associated Feeling",
    }
    return labels.get(synapse_type, synapse_type.replace("_", " ").title())

# ── graph loading ─────────────────────────────────────────────────────────────

def load_graph(db_path: str, min_weight: float):
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    cur.execute("""
        SELECT id, content, type, metadata, created_at FROM neurons
        WHERE type IN ({})
        ORDER BY created_at ASC
    """.format(','.join('?' * len(INCLUDE_TYPES))), list(INCLUDE_TYPES))

    neurons = {}
    for nid, content, ntype, metadata, created in cur.fetchall():
        cleaned = slugify_content(content)
        if not cleaned or len(cleaned) < 2:
            continue
        neurons[nid] = {
            "id": nid, "content": cleaned, "type": ntype,
            "metadata": json.loads(metadata) if metadata else {},
            "created": created,
        }

    placeholders = ','.join('?' * len(MEANINGFUL_TYPES))
    cur.execute(f"""
        SELECT source_id, target_id, type, weight, reinforced_count, last_activated
        FROM synapses
        WHERE type IN ({placeholders}) AND weight >= ?
        ORDER BY weight DESC
    """, [*list(MEANINGFUL_TYPES), min_weight])

    edges = []
    for src, tgt, stype, weight, reinforced, last_act in cur.fetchall():
        if src in neurons and tgt in neurons:
            edges.append({
                "source": src, "target": tgt, "type": stype,
                "weight": weight, "reinforced": reinforced or 0,
            })

    conn.close()
    return neurons, edges

def build_adjacency(neurons, edges):
    adj = defaultdict(list)
    for e in edges:
        adj[e["source"]].append((e["target"], e))
        adj[e["target"]].append((e["source"], {**e, "type": e["type"] + "_rev"}))
    return adj

# ── file writers ──────────────────────────────────────────────────────────────

def write_node_file(neuron, neighbors, neurons, output_dir, dry_run):
    name     = sanitize_filename(neuron["content"])
    filepath = output_dir / f"{name}.md"

    neighbors_sorted = sorted(neighbors, key=lambda x: x[1]["weight"], reverse=True)
    neighbors_sorted = neighbors_sorted[:MAX_LINKS_PER_NODE]

    by_type = defaultdict(list)
    for (nid, edge) in neighbors_sorted:
        neighbor = neurons[nid]
        nname    = sanitize_filename(neighbor["content"])
        etype    = edge["type"].replace("_rev", "")
        by_type[etype].append((nname, edge["weight"], edge["reinforced"]))

    meta        = neuron.get("metadata", {})
    entity_type = meta.get("entity_type", neuron["type"])
    confidence  = meta.get("confidence", "")
    created     = neuron["created"][:10] if neuron["created"] else "unknown"

    lines = [f"# {neuron['content']}", ""]
    lines += [f"**Type:** {entity_type}"]
    if confidence:
        lines.append(f"**Confidence:** {confidence}")
    lines += [f"**First seen:** {created}", f"**Connections:** {len(neighbors_sorted)}", "", "---", ""]

    if by_type:
        lines.append("## Connections")
        lines.append("")
        for rel_type, items in sorted(by_type.items()):
            lines.append(f"### {relationship_label(rel_type)}")
            for (nname, weight, reinforced) in items:
                dot = "🔴" if weight > 0.8 else "🟡" if weight > 0.6 else "⚪"
                lines.append(f"- {dot} [[{nname}]] *(strength: {weight:.2f}, seen {reinforced}x)*")
            lines.append("")
    else:
        lines += ["*No strong connections yet.*", ""]

    lines += ["---", f"*Generated by Adam — last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*"]

    if not dry_run:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    return filepath, len(neighbors_sorted)

def write_index(neurons, edges, adj, output_dir, dry_run, min_connections):
    conn_counts = {nid: len(adj[nid]) for nid in neurons}
    top_nodes   = sorted(conn_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    included    = [nid for nid, c in conn_counts.items() if c >= min_connections]

    lines = [
        "# Adam's Knowledge Graph", "",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*", "", "---", "",
        "## Stats", "",
        "| Metric | Value |", "|---|---|",
        f"| Total concept nodes | {len(neurons):,} |",
        f"| Total connections | {len(edges):,} |",
        f"| Nodes in graph (≥{min_connections} connections) | {len(included):,} |",
        "", "---", "",
        "## Most Connected Concepts", "",
        "*Adam's core knowledge hubs — the concepts with the most connections.*", "",
    ]
    for nid, count in top_nodes:
        if nid in neurons:
            name = sanitize_filename(neurons[nid]["content"])
            lines.append(f"- [[{name}]] — {count} connections")
    lines += [
        "", "---", "",
        "## How to Use This Graph", "",
        "1. Open Obsidian → click **Graph view** in the left sidebar",
        "2. In filters, set path to `adam-graph` to see only Adam's knowledge",
        "3. **Nodes** = concepts Adam knows. **Lines** = connections between them.",
        "4. Larger nodes = more connections = core knowledge hubs",
        "5. This graph grows every night as Adam learns more.", "",
        "*Re-run `tools/generate_obsidian_links.py` any time to update.*",
    ]

    filepath = output_dir / "_index.md"
    if not dry_run:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    return filepath

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate Obsidian wikilinks from Adam's neural graph")
    parser.add_argument("--vault",           default=DEFAULT_VAULT)
    parser.add_argument("--db",              default=DEFAULT_DB)
    parser.add_argument("--min-weight",      type=float, default=MIN_WEIGHT_DEFAULT)
    parser.add_argument("--min-connections", type=int,   default=MIN_CONNECTIONS)
    parser.add_argument("--dry-run",         action="store_true")
    args = parser.parse_args()

    print("Adam Framework — Obsidian Graph Generator")
    print("=" * 45)
    print(f"Database  : {args.db}")
    print(f"Vault     : {args.vault}")
    print(f"Min weight: {args.min_weight}  |  Min connections: {args.min_connections}")
    print(f"Dry run   : {args.dry_run}")
    print()

    if not os.path.exists(args.db):
        print(f"ERROR: Database not found at {args.db}")
        return 1
    if not os.path.exists(args.vault):
        print(f"ERROR: Vault not found at {args.vault}")
        return 1

    output_dir = Path(args.vault) / GRAPH_FOLDER
    if not args.dry_run:
        output_dir.mkdir(exist_ok=True)

    print("Loading neural graph...")
    neurons, edges = load_graph(args.db, args.min_weight)
    adj = build_adjacency(neurons, edges)
    print(f"  {len(neurons):,} neurons | {len(edges):,} edges")

    to_write = {nid: neurons[nid] for nid in neurons if len(adj[nid]) >= args.min_connections}
    print(f"  {len(to_write):,} nodes will be written to Obsidian")
    print()
    print("Generating files...")

    written = skipped = total_links = 0
    for nid, neuron in to_write.items():
        neighbors = [(tid, e) for (tid, e) in adj[nid] if tid in to_write]
        if not neighbors:
            skipped += 1
            continue
        _, link_count = write_node_file(neuron, neighbors, neurons, output_dir, args.dry_run)
        total_links += link_count
        written += 1
        if written % 500 == 0:
            print(f"  {written:,} files written...")

    write_index(neurons, edges, adj, output_dir, args.dry_run, args.min_connections)

    print()
    print("=" * 45)
    print(f"Done.")
    print(f"  Files written  : {written:,}")
    print(f"  Nodes skipped  : {skipped:,} (isolated)")
    print(f"  Total wikilinks: {total_links:,}")
    if not args.dry_run:
        print()
        print(f"Open Obsidian → Graph View → filter path to 'adam-graph'")
        print(f"Your AI's brain is now visible.")
    return 0

if __name__ == "__main__":
    exit(main())

"""Make rel[] symmetric in-place (relations are conceptually undirected)."""
import json, io, os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
FILES = ["nodes-context.json", "nodes-control.json", "nodes-orchestration.json", "nodes-extra.json"]

all_nodes = []
for f in FILES:
    all_nodes += json.load(io.open(os.path.join(DATA, f), encoding="utf-8"))
by_id = {n["id"]: n for n in all_nodes}

added = 0
for n in all_nodes:
    for r in list(n.get("rel", [])):
        if r not in by_id:
            continue
        other = by_id[r]
        if n["id"] not in other.setdefault("rel", []):
            other["rel"].append(n["id"])
            added += 1

# canonical order: by coordinate then original order, so rebuilds are stable
for n in all_nodes:
    n["rel"] = sorted(dict.fromkeys(n["rel"]), key=lambda x: (by_id[x]["dot"], by_id[x]["name"]))

for f in FILES:
    p = os.path.join(DATA, f)
    keep = [n for n in json.load(io.open(p, encoding="utf-8"))]
    ids_here = {n["id"] for n in keep}
    for n in keep:
        n["rel"] = by_id[n["id"]]["rel"]
    with io.open(p, "w", encoding="utf-8") as fh:
        json.dump(keep, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

print("symmetrized, added", added, "back-links")

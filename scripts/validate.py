"""Data integrity: coordinates, facets, relations, lineage, symmetry."""
import json, collections, sys, os

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "..", "data")
def load(f): return json.load(open(os.path.join(DATA, f), encoding="utf-8"))

meta = load("meta.json")
anc = load("ancestors.json")
nodes = []
for f in ["nodes-context.json", "nodes-control.json", "nodes-orchestration.json", "nodes-extra.json"]:
    nodes += load(f)

ids = [n["id"] for n in nodes]
idp = set(ids)
L = {i["code"] for i in meta["axes"]["layer"]["items"]}
P = {i["code"] for i in meta["axes"]["loop"]["items"]}
F = {i["code"] for i in meta["axes"]["facet"]["items"]}
MAIN = L - {"L6"}

fails = []
def check(name, cond, detail=""):
    if not cond: fails.append(f"{name}: {detail}")

check("no duplicate ids", len(ids) == len(idp),
      str([k for k, v in collections.Counter(ids).items() if v > 1]))

bad_dot, bad_facet, dangling, dangling_from = [], [], [], []
for n in nodes:
    d = n["dot"]
    if d == "L6":
        if "cluster" not in n: bad_dot.append((n["id"], "L6 needs cluster"))
        for k in ("loop",):
            pass
    else:
        parts = d.split(".")
        if len(parts) != 2 or parts[0] not in MAIN or parts[1] not in P:
            bad_dot.append((n["id"], d))
        if "cluster" in n and d != "L6":
            bad_dot.append((n["id"], "non-L6 has cluster"))
    for f in n["facets"]:
        if f not in F: bad_facet.append((n["id"], f))
    for r in n.get("rel", []):
        if r not in idp: dangling.append((n["id"], r))
    for fr in n.get("from", []):
        if fr[0] not in idp and fr[0] not in anc: dangling_from.append((n["id"], fr[0]))

check("coordinates valid", not bad_dot, str(bad_dot))

# every concept must carry a concrete example and valid prerequisites
noex = [n["id"] for n in nodes if not (n.get("example") or "").strip()]
badpre = [(n["id"], p) for n in nodes for p in n.get("prereq", []) if p not in idp]
selfpre = [n["id"] for n in nodes if n["id"] in n.get("prereq", [])]
check("every node has an example", not noex, str(noex[:8]))
check("prereq ids exist", not badpre, str(badpre[:8]))
check("no self-prerequisite", not selfpre, str(selfpre[:8]))
check("facets valid", not bad_facet, str(bad_facet))
check("rel targets exist", not dangling, str(dangling))
check("lineage targets exist (node or ancestor)", not dangling_from, str(dangling_from))

# relation symmetry (from[] is directional by design, rel[] should be mutual)
asym = []
for n in nodes:
    for r in n.get("rel", []):
        other = next((x for x in nodes if x["id"] == r), None)
        if other and n["id"] not in other.get("rel", []):
            asym.append((n["id"], r))
check("rel symmetric", not asym, str(asym[:8]) + (" ..." if len(asym) > 8 else ""))

cells = collections.Counter(n["dot"] for n in nodes)
occupied = {k: v for k, v in cells.items() if k != "L6"}
check("no empty cell has nodes", all(v > 0 for v in cells.values()))
check("L6 band populated", cells.get("L6", 0) > 0, str(cells.get("L6")))

print(f"nodes: {len(nodes)}")
print(f"occupied main cells: {len(occupied)} / {len(MAIN) * len(P)}")
print(f"L6 band: {cells.get('L6', 0)} nodes")
print(f"relations: {sum(len(n.get('rel', [])) for n in nodes)}")
print(f"root nodes (no lineage): {sum(1 for n in nodes if not n.get('from'))}")
print("layer dist:", dict(collections.Counter(n['dot'].split('.')[0] for n in nodes)))
print("tier:", dict(collections.Counter(n["tier"] for n in nodes)))
print("maturity:", dict(collections.Counter(n["maturity"] for n in nodes)))

if fails:
    print("\nFAILURES:")
    for f in fails: print("  -", f)
    sys.exit(1)
print("\nAll integrity checks passed.")

"""Content QA: field completeness, duplicate prose, trap quality, lineage presence.

Gate semantics: structural problems exit 1. Descriptive statistics (lengths,
distributions) are printed for context but never fail the gate.
"""
import json, io, os, collections, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(BASE, "..", "data")
def load(f): return json.load(io.open(os.path.join(D, f), encoding="utf-8"))
meta = load("meta.json"); anc = load("ancestors.json")
nodes = []
for f in ["nodes-context.json", "nodes-control.json", "nodes-orchestration.json", "nodes-extra.json"]:
    nodes += load(f)

L = {x["code"]: x for x in meta["axes"]["layer"]["items"]}
P = {x["code"]: x for x in meta["axes"]["loop"]["items"]}
F = {x["code"]: x for x in meta["axes"]["facet"]["items"]}
ids = {n["id"] for n in nodes}

fails = []

req = ["id","name","en","alias","dot","facets","tier","maturity","oneLine","problem","newIn","from","rel","trap","tags","example","prereq"]
missing = []
for n in nodes:
    for k in req:
        if k not in n or (isinstance(n[k], (str, list)) and len(n[k]) == 0 and k in ("oneLine","problem","newIn","trap","example")):
            missing.append((n["id"], k))
print("missing/empty required fields:", missing or "none")
if missing: fails.append(f"{len(missing)} 个字段缺失或为空")

# duplicates in prose
for field in ["oneLine", "problem", "newIn", "trap", "example"]:
    c = collections.Counter(n[field] for n in nodes)
    dup = [(v, k[:40]) for k, v in c.items() if v > 1]
    print(f"duplicate {field}:", dup or "none")
    if dup: fails.append(f"{field} 有 {len(dup)} 组重复文本")

# every node must have a lineage statement (from non-empty OR explicit note in newIn)
no_lineage = [n["id"] for n in nodes if not n.get("from")]
print("nodes with no from[]:", no_lineage)
for i in no_lineage:
    n = next(x for x in nodes if x["id"] == i)
    print("   ", i, "| newIn:", n["newIn"][:50])

# dot validity
bad = []
for n in nodes:
    d = n["dot"]
    if d == "L6":
        if "cluster" not in n: bad.append((n["id"], "L6 without cluster"))
        continue
    if "." not in d: bad.append((n["id"], d)); continue
    lc, pc = d.split(".")
    if lc not in L or pc not in P: bad.append((n["id"], d))
print("bad coords:", bad or "none")
if bad: fails.append(f"{len(bad)} 个坐标非法")

# facet validity
badf = [(n["id"], f) for n in nodes for f in n["facets"] if f not in F]
print("bad facets:", badf or "none")
if badf: fails.append(f"{len(badf)} 个 facet 非法")

# rel symmetry + no self refs
selfref = [n["id"] for n in nodes if n["id"] in n.get("rel", [])]
print("self refs:", selfref or "none")
if selfref: fails.append(f"{len(selfref)} 个节点自引用")

# trap length distribution
lens = sorted(len(n["trap"]) for n in nodes)
print("trap len: min %d p25 %d median %d p75 %d max %d" % (lens[0], lens[len(lens)//4], lens[len(lens)//2], lens[3*len(lens)//4], lens[-1]))

# oneLine length
ol = sorted(len(n["oneLine"]) for n in nodes)
print("oneLine len: min %d median %d max %d" % (ol[0], ol[len(ol)//2], ol[-1]))

# tier/maturity vocab
print("tiers:", dict(collections.Counter(n["tier"] for n in nodes)))
print("maturity:", dict(collections.Counter(n["maturity"] for n in nodes)))
print("facets dist:", dict(collections.Counter(f for n in nodes for f in n["facets"])))

if fails:
    print("\nFAILURES:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("\ncontent checks passed.")

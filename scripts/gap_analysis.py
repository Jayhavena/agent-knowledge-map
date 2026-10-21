"""Gap analysis: which cells are empty, which axes are thin, where the graph is sparse.

Used to decide what to build next — both content (missing concepts) and features
(missing capabilities) — instead of guessing.
"""
import io, json, os, collections

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
DATA = os.path.join(ROOT, "data")

meta = json.load(io.open(os.path.join(DATA, "meta.json"), encoding="utf-8"))
nodes = []
for f in ["nodes-context.json", "nodes-control.json", "nodes-orchestration.json", "nodes-extra.json"]:
    nodes += json.load(io.open(os.path.join(DATA, f), encoding="utf-8"))

LAYERS = [x for x in meta["axes"]["layer"]["items"] if x["code"] != "L6"]
LOOPS = meta["axes"]["loop"]["items"]
FACETS = meta["axes"]["facet"]["items"]

occ = collections.Counter(n["dot"] for n in nodes)
print("=== 空格子（内容缺口，不是 bug）===")
empty = []
for l in LAYERS:
    row = []
    for p in LOOPS:
        k = l["code"] + "." + p["code"]
        if not occ.get(k):
            row.append(p["code"])
            empty.append(k)
    if row:
        print(f"  {l['code']} {l['name']:<6} 空 {len(row)}/7: {' '.join(row)}")

print(f"\n总计 {len(empty)} / {len(LAYERS)*len(LOOPS)} 个主格为空")

print("\n=== 每列（环）的密度 ===")
for p in LOOPS:
    n = sum(occ.get(l["code"] + "." + p["code"], 0) for l in LAYERS)
    bar = "#" * n
    print(f"  {p['code']} {p['name']:<4} {n:>3} {bar}")

print("\n=== 每层（含 L6）===")
for l in meta["axes"]["layer"]["items"]:
    n = sum(v for k, v in occ.items() if k.split(".")[0] == l["code"])
    print(f"  {l['code']} {l['name']:<6} {n:>3}")

print("\n=== 面分布（一条概念可属多面）===")
fc = collections.Counter(f for n in nodes for f in n["facets"])
for f in FACETS:
    n = fc.get(f["code"], 0)
    print(f"  {f['code']} {f['name']:<4} {n:>3} {'#'*(n//3)}")

# 关系稀疏度
deg = collections.Counter()
for n in nodes:
    deg[n["id"]] += len(n["rel"])
low = sorted(deg.items(), key=lambda kv: kv[1])[:8]
print("\n=== 关联最少的概念（可能是还没连上）===")
for k, v in low:
    name = next(n["name"] for n in nodes if n["id"] == k)
    print(f"  {name:<16} {v} 条  ({next(n['dot'] for n in nodes if n['id']==k)})")

print("\n=== 深读卡覆盖 ===")
deeps = []
for f in ["deeps-evaluation.json", "deeps-memory.json"]:
    p = os.path.join(DATA, f)
    if os.path.exists(p):
        deeps += [v for k, v in json.load(io.open(p, encoding="utf-8")).items() if not k.startswith("_")]
print(f"  {len(deeps)} 张 / 134 个概念")

"""Numeric layout QA mirroring template.html's layoutGraph()."""
import json, io, os, math, sys
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(BASE, "..", "data")
def load(f): return json.load(io.open(os.path.join(D, f), encoding="utf-8"))

meta = load("meta.json")
nodes = []
for f in ["nodes-context.json", "nodes-control.json", "nodes-orchestration.json", "nodes-extra.json"]:
    nodes += load(f)

LAYERS = meta["axes"]["layer"]["items"]
LOOPS = meta["axes"]["loop"]["items"]
MAIN = [l for l in LAYERS if l["code"] != "L6"]
CLUSTERS = ["评测与质量", "观测与成本", "安全与治理", "运行与发布", "其他"]

by_id = {n["id"]: n for n in nodes}
DEG = {n["id"]: 0 for n in nodes}
for n in nodes:
    for r in n.get("rel", []):
        if r in by_id: DEG[n["id"]] += 1; DEG[r] += 1
    for f in n.get("from", []):
        if f[0] in by_id: DEG[n["id"]] += 1; DEG[f[0]] += 1

W, H = float(os.environ.get("W", 1400)), float(os.environ.get("H", 780))
PADL, PADR, PADT, PADB = 62.0, 16.0, 24.0, 12.0
availW = W - PADL - PADR
totalH = H - PADT - PADB
bandH = max(150, totalH * .28)
rowsH = totalH - bandH
ch = rowsH / len(MAIN)
cw = availW / len(LOOPS)

groups = defaultdict(list)
for n in nodes:
    if n["dot"] == "L6": continue
    groups[n["dot"]].append(n)

for k, arr in groups.items():
    lc, pc = k.split(".")
    li = [x["code"] for x in MAIN].index(lc)
    pi = [x["code"] for x in LOOPS].index(pc)
    cx = PADL + cw*(pi+.5); cy = PADT + ch*(li+.5)
    rMax = min(cw*.36, ch*.40)
    if len(arr) == 1:
        arr[0]["_x"], arr[0]["_y"] = cx, cy; continue
    two = len(arr) > 12
    inner = math.ceil(len(arr)*.36) if two else 0
    outer = len(arr) - inner
    for i, n in enumerate(arr):
        inInner = i < inner
        cnt = inner if inInner else outer
        idx = i if inInner else i - inner
        rad = rMax*.48 if inInner else rMax
        a = (idx/cnt)*math.pi*2 - math.pi/2
        n["_x"] = cx + math.cos(a)*rad
        n["_y"] = cy + math.sin(a)*rad*.92

six = [n for n in nodes if n["dot"] == "L6"]
bandTop = PADT + rowsH + 6
bandInner = bandH - 26
present = [c for c in CLUSTERS if any((n.get("cluster") or "其他") == c for n in six)]
segW = availW / max(len(present), 1)
for ci, c in enumerate(present):
    arr = [n for n in six if (n.get("cluster") or "其他") == c]
    per = max(1, math.ceil(len(arr)/3))
    rows = math.ceil(len(arr)/per)
    cellW, cellH = segW/per, bandInner/rows
    for i, n in enumerate(arr):
        row, col = divmod(i, per)
        n["_x"] = PADL + segW*ci + cellW*(col+.5) + 4
        n["_y"] = bandTop + 20 + cellH*(row+.5)

print(f"cell {cw:.1f}x{ch:.1f}  bandH={bandH:.1f} bandTop={bandTop:.1f} bottom={bandTop+bandInner:.1f} (H={H:.0f})")

worst = []
for k, arr in groups.items():
    if len(arr) < 2: continue
    md = min(math.dist((a["_x"], a["_y"]), (b["_x"], b["_y"])) for i, a in enumerate(arr) for b in arr[i+1:])
    worst.append((md, k, len(arr)))
worst.sort()
print("\ncell      n  minDist  verdict")
bad = 0
for md, k, n in worst[:8]:
    v = "OVERLAP" if md < 9.5 else ("tight" if md < 12 else "ok")
    if md < 9.5: bad += 1
    print(f"{k:9s} {n:3d} {md:7.1f}  {v}")

xs = [n["_x"] for n in nodes]; ys = [n["_y"] for n in nodes]
oob = [n["id"] for n in nodes if n["_x"] < 52 or n["_x"] > W-6 or n["_y"] < 6 or n["_y"] > H-6]
print(f"\nx {min(xs):.1f}..{max(xs):.1f}  y {min(ys):.1f}..{max(ys):.1f}")
print("out of bounds:", oob or "none")

smin = min(min(a["_x"], b["_x"]) for i, a in enumerate(six) for b in six[i+1:] if abs(a["_y"]-b["_y"]) < 1)
print(f"L6 band: {len(six)} nodes, top={min(n['_y'] for n in six):.1f}, bottom={max(n['_y'] for n in six):.1f}, band {bandTop:.1f}..{bandTop+bandInner:.1f}")
print("L6 inside band:", all(bandTop <= n["_y"] <= bandTop+bandInner for n in six))
verdict = "PASS" if not oob and bad == 0 and all(bandTop <= n["_y"] <= bandTop+bandInner for n in six) else "FAIL"
print("VERDICT:", verdict)

fails = []
if oob:
    fails.append(f"{len(oob)} 个节点超出画布: {oob[:6]}")
if bad:
    fails.append(f"{bad} 个格子节点重叠")
if not all(bandTop <= n["_y"] <= bandTop+bandInner for n in six):
    fails.append("L6 带内有节点越界")

if fails:
    print("\nFAILURES:")
    for f in fails:
        print("  -", f)
    sys.exit(1)

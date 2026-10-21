"""Gate: from relation types must be whitelisted, and no `from` cycles are allowed."""
import json, io, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "..", "data")
FILES = ["nodes-context.json", "nodes-control.json", "nodes-orchestration.json", "nodes-extra.json"]

meta = json.load(io.open(os.path.join(DATA, "meta.json"), encoding="utf-8"))
nodes = []
for f in FILES:
    nodes += json.load(io.open(os.path.join(DATA, f), encoding="utf-8"))
by = {n["id"]: n for n in nodes}

fails = []

# 1. 词表：from 的 kind 必须在 meta.relationTypes 里定义
allowed = set(meta.get("relationTypes", {}).keys())
if not allowed:
    fails.append("meta.json 缺少 relationTypes 定义")
used = {}
for n in nodes:
    for fr, k in n.get("from", []):
        used[k] = used.get(k, 0) + 1
        if k not in allowed:
            fails.append(f"未定义的关系类型「{k}」（{n['id']} ← {fr}）")
        if fr == n["id"]:
            fails.append(f"自引用关系: {n['id']}")

# 2. 环检测
color, cycles = {}, []
def dfs(u, path):
    color[u] = 1
    for v in by[u].get("from", []):
        v = v[0]
        if v not in by:
            continue
        if color.get(v) == 1:
            cycles.append(path + [v])
        elif color.get(v, 0) == 0:
            dfs(v, path + [v])
    color[u] = 2
for u in by:
    if color.get(u, 0) == 0:
        dfs(u, [u])
for c in cycles:
    fails.append("from 环: " + " → ".join(c))

# 3. 「组合」必须多来源：单来源的组合没有意义
for n in nodes:
    combos = [f for f, k in n.get("from", []) if k == "组合"]
    if len(combos) == 1:
        fails.append(f"{n['id']} 只有 1 条「组合」来源，请改用其他类型")

# 4. 「替代」的 A 不得标注为「争议」
for n in nodes:
    for fr, k in n.get("from", []):
        if k == "替代" and n.get("maturity") == "争议":
            fails.append(f"{n['id']} 标注为「争议」却使用「替代」关系（替代意味着已定论）")

print("关系类型分布:", dict(sorted(used.items(), key=lambda kv: -kv[1])))
print("from 环:", len(cycles))
print("单来源组合:", sum(1 for n in nodes if sum(1 for _, k in n.get("from", []) if k == "组合") == 1))

if fails:
    print("\nFAILURES:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("\nrelation type checks passed.")

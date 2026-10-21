"""Undefined-jargon check: a definition that names another concept,
but that concept is neither a prereq nor a direct neighbour, is unexplained jargon.
"""
import io, json, os

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "..", "data")
FILES = ["nodes-context.json", "nodes-control.json", "nodes-orchestration.json", "nodes-extra.json"]

nodes = []
for f in FILES:
    nodes += json.load(io.open(os.path.join(DATA, f), encoding="utf-8"))
by_id = {n["id"]: n for n in nodes}

lex = {}
for n in nodes:
    lex.setdefault(n["name"], n["id"])
    for a in n.get("alias", []):
        if 2 <= len(a) <= 12:
            lex.setdefault(a, n["id"])

def jargon(text, self_id, allowed):
    out = []
    for term, nid in lex.items():
        if nid == self_id or nid in allowed:
            continue
        if term in text:
            out.append((term, nid))
    return out

rows = []
for n in nodes:
    allowed = set(n.get("prereq", [])) | set(n.get("rel", []))
    hits = jargon(n["oneLine"] + "、" + n["problem"], n["id"], allowed)
    if hits:
        rows.append((len(hits), n, hits))

rows.sort(key=lambda r: -r[0])
print(f"定义里出现「既不是前置、也不是邻居」的概念：{len(rows)} 条\n")
for cnt, n, hits in rows[:14]:
    print(f"[{cnt}] {n['dot']:<7} {n['name']}")
    print(f"    一句话: {n['oneLine']}")
    print(f"    未解释: {'、'.join(t for t, _ in hits[:5])}")
    print()

print("=== 汇总 ===")
print("受影响条目:", len(rows), "/", len(nodes))
if rows:
    from collections import Counter
    c = Counter()
    for _, n, hits in rows:
        for t, _ in hits:
            c[t] += 1
    print("被提及最多的未解释术语:", "、".join(f"{k}({v})" for k, v in c.most_common(8)))

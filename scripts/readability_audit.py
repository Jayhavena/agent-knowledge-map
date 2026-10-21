"""Readability audit: find concept entries that assume knowledge the reader may not have.

Three concrete failure modes:
  1. 循环定义 — 解释里用了它自己（或同义别名）
  2. 术语前置 — 一句话里堆了多个「本图里的其它概念」，读者可能一个都不认识
  3. 没有落点 — 通篇抽象，没有任何具体例子
"""
import io, json, os, re, collections

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
DATA = os.path.join(ROOT, "data")

nodes = []
for f in ["nodes-context.json", "nodes-control.json", "nodes-orchestration.json", "nodes-extra.json"]:
    nodes += json.load(io.open(os.path.join(DATA, f), encoding="utf-8"))

meta = json.load(io.open(os.path.join(DATA, "meta.json"), encoding="utf-8"))
by_id = {n["id"]: n for n in nodes}

# every name/alias that could act as an unexplained term
lex = {}
for n in nodes:
    lex[n["name"]] = n["id"]
    for a in n.get("alias", []):
        a = a.strip()
        if 2 <= len(a) <= 12:
            lex.setdefault(a, n["id"])

def terms_in(text, self_id):
    hits = set()
    for term, nid in lex.items():
        if nid == self_id:
            continue
        if term in text:
            hits.add(term)
    return hits

def sentences(text):
    return [s for s in re.split(r"[。；;！!？?\n]", text) if s.strip()]

rows = []
for n in nodes:
    prob = n["problem"]
    onel = n["oneLine"]
    newin = n["newIn"]

    # 1. circular
    circular = []
    for label in [n["name"]] + [a for a in n.get("alias", []) if len(a) >= 2]:
        for field, txt in (("oneLine", onel), ("problem", prob), ("newIn", newin)):
            if label in txt:
                circular.append(f"{field}:{label}")

    # 2. jargon density (distinct other concepts mentioned)
    jt = terms_in(onel + prob, n["id"])
    # 3. concrete example?
    has_eg = bool(n.get("example"))
    # 4. longest sentence
    longest = max((len(s) for s in sentences(prob + newin)), default=0)

    score = len(jt) * 2 + (3 if circular else 0) + (0 if has_eg else 1) + (1 if longest > 45 else 0)
    rows.append({
        "id": n["id"], "name": n["name"], "dot": n["dot"],
        "jargon": sorted(jt), "circular": circular, "has_eg": has_eg,
        "longest": longest, "score": score,
    })

rows.sort(key=lambda r: -r["score"])

print("=== 最难读的 15 条（分数 = 术语数×2 + 循环×3 + 无例子×1 + 长句×1）===\n")
for r in rows[:15]:
    flags = []
    if r["circular"]:
        flags.append("循环:" + ",".join(r["circular"]))
    if r["jargon"]:
        flags.append("术语:" + ",".join(r["jargon"][:4]))
    if not r["has_eg"]:
        flags.append("无例子")
    if r["longest"] > 45:
        flags.append(f"长句{r['longest']}字")
    print(f"[{r['score']:>2}] {r['dot']:<7} {r['name']}")
    print(f"     {' / '.join(flags) if flags else '—'}")
    n = by_id[r["id"]]
    print(f"     一句话: {n['oneLine']}")
    print()

print("\n=== 统计 ===")
print("循环定义:", sum(1 for r in rows if r["circular"]), "条")
print("无具体例子:", sum(1 for r in rows if not r["has_eg"]), "/", len(rows))
print("单句超过 45 字:", sum(1 for r in rows if r["longest"] > 45), "条")
print("术语数 >= 3:", sum(1 for r in rows if len(r["jargon"]) >= 3), "条")

# connectivity
deg = collections.Counter()
for n in nodes:
    deg[n["id"]] += len(n["rel"])
low = [r for r in rows if deg[r["id"]] <= 3]
print("\n=== 连通性：关联 <= 3 的概念 ===")
for n in sorted(nodes, key=lambda x: deg[x["id"]])[:12]:
    print(f"  {n['name']:<16} {deg[n['id']]} 条  ({n['dot']})")

json.dump(rows, io.open(os.path.join(ROOT, "_audit.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n详细结果写入 _audit.json")

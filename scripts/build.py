import json, os, io, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
DATA = os.path.join(ROOT, "data")
OUT = ROOT

def load(name):
    with io.open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)

meta = load("meta.json")
anc = load("ancestors.json")
nodes = []
for f in ["nodes-context.json", "nodes-control.json", "nodes-orchestration.json", "nodes-extra.json"]:
    nodes += load(f)

by_id = {n["id"]: n for n in nodes}
LAYERS = meta["axes"]["layer"]["items"]
LOOPS = meta["axes"]["loop"]["items"]
FACETS = meta["axes"]["facet"]["items"]
L = {x["code"]: x for x in LAYERS}
P = {x["code"]: x for x in LOOPS}
F = {x["code"]: x for x in FACETS}
DEFAULT_CELL = {x["code"]: x for x in LOOPS}
GROUP = {"L0": "00-地基", "L1": "01-上下文", "L2": "02-记忆", "L3": "03-工具",
         "L4": "04-控制", "L5": "05-编排", "L6": "06-系统"}
MAIN_LAYERS = [x for x in LAYERS if x["code"] != "L6"]

# ---- deep dives: concept-level elaboration, a different shape from nodes ----
DEEPS = []
for f in ["deeps-evaluation.json", "deeps-memory.json", "deeps-agent-loop.json"]:
    p = os.path.join(DATA, f)
    if os.path.exists(p):
        obj = load(f)
        for k, v in obj.items():
            if k.startswith("_"):
                continue
            DEEPS.append(v)
DEEP_BY_ID = {d["id"]: d for d in DEEPS}
for d in DEEPS:
    for r in d.get("related", []):
        assert r in by_id, "deep card references unknown node: " + r
    assert d["id"] in by_id, "deep card must anchor to an existing node: " + d["id"]

# ---------------- HTML ----------------
payload = {"meta": meta, "nodes": nodes, "ancestors": anc, "deeps": DEEPS}
js = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
tpl = io.open(os.path.join(BASE, "template.html"), encoding="utf-8").read()
html = tpl.replace("/*__DATA__*/", js)
# guard: script injection safety
assert "</script" not in js.lower()
with io.open(os.path.join(OUT, "Agent知识地图.html"), "w", encoding="utf-8") as f:
    f.write(html)

# ---------------- Obsidian ----------------
VAULT = os.path.join(OUT, "Obsidian-Agent知识库")
RULES_DIR = os.path.join(VAULT, "00_导航")
NODE_DIR = os.path.join(VAULT, "10_概念")
for d in [RULES_DIR, NODE_DIR]:
    os.makedirs(d, exist_ok=True)

def safe(name):
    # "/" is a path separator in Obsidian wikilinks and invalid on Windows, so it must go.
    # Prefer readable substitutes over a bare dash: "A / B" -> "A·B", "CI/CD" -> "CI／CD".
    s = name.replace(" / ", "·")
    s = s.replace("/", "／")
    return re.sub(r'[\\:*?"<>|\[\]#^]', "-", s)

def link(name):
    # Must match the on-disk filename exactly: "/" is a path separator in Obsidian wikilinks,
    # so node names like "A/B 实验" or "CI/CD" would otherwise produce broken links.
    return "[[" + safe(name) + "]]"

DEEP_PREFIX = "深读·"
def deeplink(title):
    # Deep notes live alongside concept notes but must not collide with them
    # (e.g. deep card "Agent 评测" vs concept note "Agent 评测").
    return "[[" + DEEP_PREFIX + safe(title) + "]]"

def cell_note(lc, pc):
    return (meta.get("cellNotes") or {}).get(lc + "." + pc, "")

def layer_of(n):
    return n["dot"].split(".")[0]

def is_stack(n):
    return n["dot"] == "L6"

# --- node notes ---
for n in nodes:
    lc = layer_of(n)
    pc = n["dot"].split(".")[1] if "." in n["dot"] else ""
    lay = L[lc]
    loop = P.get(pc)
    rel = [by_id[r] for r in n.get("rel", []) if r in by_id]
    coord_label = ("L6 · 系统层 / " + (n.get("cluster") or "其他") + "（环绕全程）") if is_stack(n) \
                  else n["dot"] + " · " + lay["name"] + " / " + (loop["name"] if loop else "—")
    facet_label = "·".join(F[f]["name"] for f in n["facets"]) + "面"
    frm = []
    for item in n.get("from", []):
        fid, kind = item
        if fid in by_id:
            frm.append((by_id[fid]["name"], kind, fid, True))
        elif fid in anc:
            frm.append((anc[fid]["name"], kind, fid, False))
    child = [x for x in nodes if any(f[0] == n["id"] for f in x.get("from", []))]
    same = [x for x in nodes if x["dot"] == n["dot"] and x["id"] != n["id"]]

    tagl = ["agent", lc] + ([pc] if pc else [])
    if is_stack(n) and n.get("cluster"):
        tagl.append(n["cluster"])
    fm = ["---",
          "type: agent-concept",
          "id: " + n["id"],
          "name: " + n["name"],
          'en: "' + n["en"] + '"',
          "dot: " + n["dot"],
          "layer: " + lay["name"],
          "loop: " + (loop["name"] if loop else "全程"),
          "facets: [" + ", ".join(n["facets"]) + "]",
          "tier: " + n["tier"],
          "maturity: " + n["maturity"],
          "tags: [" + ", ".join(tagl) + "]",
          "---", ""]
    body = fm
    body.append("# " + n["name"])
    body.append("")
    body.append("> **" + coord_label + "** · " + facet_label + " · " + n["tier"] + " / " + n["maturity"])
    body.append("")
    body.append("**" + n["en"] + "**" + ("  ·  别名：" + "、".join(n["alias"]) if n.get("alias") else ""))
    body.append("")
    body.append("## 一句话")
    body.append("")
    body.append(n["oneLine"])
    body.append("")
    if n.get("example"):
        body.append("## 具体是什么样")
        body.append("")
        body.append("> " + n["example"])
        body.append("")
    if n.get("prereq"):
        pres = [by_id[r] for r in n["prereq"] if r in by_id]
        if pres:
            body.append("## 看不懂？先看这几个")
            body.append("")
            for p in pres:
                body.append("- " + link(p["name"]) + " — " + p["oneLine"])
            body.append("")
    body.append("## 它解决什么问题")
    body.append("")
    body.append(n["problem"])
    body.append("")
    body.append("## 它新在哪")
    body.append("")
    body.append(n["newIn"])
    body.append("")
    if frm:
        body.append("## 谱系")
        body.append("")
        for nm, kind, fid, internal in frm:
            if internal:
                body.append("- **" + kind + "** · " + link(nm))
            else:
                a = anc[fid]
                body.append("- **" + kind + "** · " + nm + "（" + a["field"] + "，图外旧概念）")
        body.append("")
    if child:
        body.append("## 被谁继承")
        body.append("")
        for c in child:
            body.append("- " + link(c["name"]) + " — " + c["oneLine"])
        body.append("")
    if rel:
        child_ids = {c["id"] for c in child}
        rel_dedup = [r for r in rel if r["id"] not in child_ids]
        body.append("## 关联概念")
        body.append("")
        if rel_dedup:
            for r in rel_dedup:
                body.append("- " + link(r["name"]) + " — " + r["oneLine"])
        else:
            body.append("（无额外关联，见上方谱系与继承）")
        body.append("")
    body.append("## 常见误判 / 坑")
    body.append("")
    body.append("> [!warning] 坑")
    body.append("> " + n["trap"])
    body.append("")
    if same:
        body.append("## 同一格子的邻居")
        body.append("")
        for s in same:
            body.append("- " + link(s["name"]))
        body.append("")
    body.append("## 我的掌握度")
    body.append("")
    body.append("- [ ] 知道（听过，说不清细节）")
    body.append("- [ ] 会用（能落地，需查文档）")
    body.append("- [ ] 精通（能讲清取舍与边界）")
    body.append("")
    body.append("## 备注")
    body.append("")
    body.append("")
    with io.open(os.path.join(NODE_DIR, safe(n["name"]) + ".md"), "w", encoding="utf-8") as f:
        f.write("\n".join(body))

# --- matrix note ---
m = []
m += ["---", "type: agent-map-nav", "id: matrix", "tags: [agent, nav]", "---", ""]
m.append("# Agent 知识矩阵 · 层 × 环")
m.append("")
m.append("横轴是一次运行的时间轴，纵轴是对象层级。**同一个概念落在哪一格，就说明它插在系统的哪里。**")
m.append("")
m.append("每格中的概念用双链列出，点进去就是该概念的笔记。空格子代表目前没有独立概念——也可能是尚未被单独命名的问题点。")
m.append("")
m.append("> 配套：[[00_导航/落位规则|落位规则]] · [[00_导航/学习路线|学习路线]] · [[00_导航/术语速查|术语速查]]")
m.append("")
for l in LAYERS:
    m.append("## " + l["code"] + " · " + l["name"] + "（" + l["sub"] + "）")
    m.append("")
    m.append("> " + l["scope"])
    m.append("")
    if l["code"] == "L6":
        six = [n for n in nodes if n["dot"] == "L6"]
        m.append("| 分组 | 概念 |")
        m.append("|---|---|")
        for c in ["评测与质量", "观测与成本", "安全与治理", "运行与发布", "其他"]:
            arr = [n for n in six if (n.get("cluster") or "其他") == c]
            if not arr:
                continue
            m.append("| **" + c + "** | " + " · ".join(link(n["name"]) for n in arr) + " |")
        m.append("")
        continue
    m.append("| 环 | 概念 |")
    m.append("|---|---|")
    for p in LOOPS:
        key = l["code"] + "." + p["code"]
        arr = [n for n in nodes if n["dot"] == key]
        cells = " · ".join(link(n["name"]) for n in arr) if arr else "—"
        note = cell_note(l["code"], p["code"])
        if note:
            cells += "<br/><sub>" + note + "</sub>"
        m.append("| **" + p["code"] + " " + p["name"] + "** | " + cells + " |")
    m.append("")
with io.open(os.path.join(VAULT, "00_导航", "知识矩阵.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(m))

# --- rules note ---
r = ["---", "type: agent-map-nav", "id: rules", "tags: [agent, nav, method]", "---", ""]
r.append("# 落位规则 · 新概念三问")
r.append("")
r.append("> 这张图的第一性产物不是概念清单，而是这套定位规则。概念会过时，规则不会。")
r.append("")
r.append("## 为什么需要坐标系")
r.append("")
r.append(meta["thesis"])
r.append("")
r.append("## 三条轴")
r.append("")
for ax in ["layer", "loop", "facet"]:
    a = meta["axes"][ax]
    r.append("### " + a["name"] + "轴 — " + a["question"])
    r.append("")
    r.append(a["hint"])
    r.append("")
    r.append("| 代码 | 名称 | 回答的问题 |")
    r.append("|---|---|---|")
    for it in a["items"]:
        q = it.get("question") or it.get("scope", "")
        r.append("| `" + it["code"] + "` | " + it["name"] + " | " + q + " |")
    r.append("")
r.append("## 五步流程")
r.append("")
for rule in meta["rules"]:
    r.append("### " + str(rule["step"]) + ". " + rule["title"])
    r.append("")
    r.append(rule["body"])
    r.append("")
    r.append("> [!caution] 易错")
    r.append("> " + rule["trap"])
    r.append("")
r.append("## 一个例子：把 MCP 落位")
r.append("")
r.append("1. **层**：它操作的是「Agent 能对外做什么」——L3 工具层，不是模型层。")
r.append("2. **环**：它生效在 P4 行动（每次发起工具调用），不改变 P2 取景。")
r.append("3. **面**：机制面看协议规范；安全面看工具投毒；运维面看版本治理。")
r.append("4. **减法**：格子里已有「原生工具调用」「工具定义」。MCP 不是新能力，是**把 M×N 套适配收敛成 M+N**。")
r.append("5. **谱系**：原生工具调用的下一代；同时是 OpenAPI 自动封装的替代品。")
r.append("")
r.append("做完这五步，MCP 就不「新」了——它是你已知概念的一个坐标，外加一条新的工程约束。")
r.append("")
with io.open(os.path.join(VAULT, "00_导航", "落位规则.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(r))

# --- MOC ---
moc = ["---", "type: agent-map-nav", "id: moc", "tags: [agent, nav, moc]", "---", ""]
moc.append("# Agent 知识地图 · 总览")
moc.append("")
moc.append("> " + meta["subtitle"])
moc.append("")
moc.append("一个概念的坐标写作 `L?.P?`：层决定它在系统里的位置，环决定它在运行中的时机。")
moc.append("")
moc.append("## 导航")
moc.append("")
moc.append("- [[00_导航/落位规则|落位规则]] — 遇到新概念时先走这五步")
moc.append("- [[00_导航/知识矩阵|知识矩阵]] — 全图一览，按层 × 环排布")
moc.append("- [[00_导航/学习路线|学习路线]] — 从哪开始，按什么顺序")
moc.append("- [[00_导航/深读专题|深读专题]] — 把单个概念往下挖一层")
moc.append("- [[00_导航/术语速查|术语速查]] — 一页纸查全")
moc.append("")
if DEEPS:
    moc.append("## 深读专题")
    moc.append("")
    moc.append("坐标不变，往下挖：内部结构、关键决策、失败模式、上手路径。")
    moc.append("")
    for d in DEEPS:
        a = by_id[d["id"]]
        moc.append("### " + deeplink(d["title"]))
        moc.append("")
        moc.append("锚点 " + link(a["name"]) + " · `" + a["dot"] + "` — " + d["subtitle"])
        moc.append("")
        moc.append(d["lead"])
        moc.append("")
moc.append("## 七层对象栈")
moc.append("")
for l in LAYERS:
    arr = [n for n in nodes if n["dot"].split(".")[0] == l["code"]]
    moc.append("### " + l["code"] + " · " + l["name"] + " — " + l["sub"])
    moc.append("")
    moc.append(l["scope"])
    moc.append("")
    moc.append("　".join(link(n["name"]) for n in arr))
    moc.append("")
moc.append("## 统计")
moc.append("")
moc.append("- 概念总数：**" + str(len(nodes)) + "**")
cells = {}
for n in nodes:
    cells[n["dot"]] = cells.get(n["dot"], 0) + 1
moc.append("- 已占格子：" + str(len([k for k in cells if k != "L6"])) + " / " + str(len(MAIN_LAYERS) * len(LOOPS)) + "（另有 L6 系统层支架带 " + str(cells.get("L6", 0)) + " 个）")
from collections import Counter
tc = Counter(n["tier"] for n in nodes)
mc = Counter(n["maturity"] for n in nodes)
moc.append("- 权重分布：" + "，".join(k + " " + str(v) for k, v in tc.most_common()))
moc.append("- 成熟度分布：" + "，".join(k + " " + str(v) for k, v in mc.most_common()))
moc.append("")
with io.open(os.path.join(VAULT, "00_导航", "总览.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(moc))

# --- learning path ---
lp = ["---", "type: agent-map-nav", "id: path", "tags: [agent, nav, path]", "---", ""]
lp.append("# 学习路线 · 从哪开始")
lp.append("")
lp.append("> 不要按字母序学。按**依赖关系**学：下层不通，上层只能背名词。")
lp.append("")
lp.append("## 阶段一 · 骨架（必须先有）")
lp.append("")
p1 = ["agent-loop", "react", "chain-of-thought", "tool-definition", "native-tool-calling",
      "context-engineering", "rag", "evaluation", "termination"]
lp.append("这一层决定你能不能读懂后面所有东西。任何一个不能用自己的话讲清，先补它。")
lp.append("")
for i in p1:
    if i in by_id:
        lp.append("- " + link(by_id[i]["name"]) + " — " + by_id[i]["oneLine"])
lp.append("")
lp.append("## 阶段二 · 能跑起来")
lp.append("")
p2 = ["tool-result-design", "tool-selection", "plan-and-execute", "reflexion", "working-memory",
      "chunking", "rerank", "structured-output", "system-prompt", "few-shot",
      "retry-backoff", "tool-error-handling", "mcp"]
lp.append("学完这一层，能独立搭一个可用的单 Agent。")
lp.append("")
for i in p2:
    if i in by_id:
        lp.append("- " + link(by_id[i]["name"]) + " — " + by_id[i]["oneLine"])
lp.append("")
lp.append("## 阶段三 · 跑得住")
lp.append("")
p3 = ["golden-set", "sentinel-set", "llm-as-judge", "deterministic-eval", "failure-taxonomy",
      "tracing", "regression-gate", "drift-detection", "canary-release", "cost-attribution",
      "latency-budget", "guardrails", "prompt-injection"]
lp.append("这一层是 demo 与产品的分界线。缺了它，系统会以「安静地答错」的方式失败。")
lp.append("")
for i in p3:
    if i in by_id:
        lp.append("- " + link(by_id[i]["name"]) + " — " + by_id[i]["oneLine"])
lp.append("")
lp.append("## 阶段四 · 做出差异")
lp.append("")
p4 = ["long-term-memory", "memory-write-policy", "memory-consolidation", "episodic-memory",
      "procedural-memory", "graph-rag", "agentic-rag", "prompt-caching", "model-routing",
      "multi-agent", "supervisor", "subagent", "context-transfer", "mcp-primitives",
      "tool-search", "code-interpreter", "computer-use", "human-in-the-loop"]
lp.append("这一层决定你的系统是「又一个套壳」还是「有护城河」。建议按业务需要挑 3–5 个深入，不要全学。")
lp.append("")
for i in p4:
    if i in by_id:
        lp.append("- " + link(by_id[i]["name"]) + " — " + by_id[i]["oneLine"])
lp.append("")
lp.append("## 明确可以跳过的")
lp.append("")
skip = ["tree-of-thought", "lats", "benchmark", "distillation", "small-model", "a2a", "microservice"]
lp.append("不是不重要，是**投入产出比在你当前阶段最低**。知道它们在图上哪个位置就够了，需要时再回来。")
lp.append("")
for i in skip:
    if i in by_id:
        lp.append("- " + link(by_id[i]["name"]) + " — 位置：" + by_id[i]["dot"])
lp.append("")
with io.open(os.path.join(VAULT, "00_导航", "学习路线.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(lp))

# --- glossary ---
g = ["---", "type: agent-map-nav", "id: glossary", "tags: [agent, nav, glossary]", "---", ""]
g += ["# 术语速查", "", "| 中文名 | 英文 / 别名 | 坐标 | 一句话 |", "|---|---|---|---|"]
for n in sorted(nodes, key=lambda x: (x["dot"], x["tier"], x["name"])):
    g.append("| " + link(n["name"]) + " | " + n["en"] + " | `" + n["dot"] + "` | " + n["oneLine"] + " |")
g.append("")
g.append("## 图外旧概念（作为祖先出现）")
g.append("")
g.append("| 名称 | 领域 | 定义 |")
g.append("|---|---|---|")
for k, v in anc.items():
    if k.startswith("_"):
        continue
    g.append("| " + v["name"] + " | " + v["field"] + " | " + v["def"] + " |")
with io.open(os.path.join(VAULT, "00_导航", "术语速查.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(g))

# --- deep dive notes ---
DEEP_DIR = os.path.join(VAULT, "20_深读")
os.makedirs(DEEP_DIR, exist_ok=True)
for d in DEEPS:
    anchor = by_id[d["id"]]
    out = ["---",
           "type: agent-deep",
           "id: deep-" + d["id"],
           "anchor: " + d["id"],
           "dot: " + anchor["dot"],
           "tags: [agent, deep, " + anchor["dot"].split(".")[0] + "]",
           "---", ""]
    out.append("# " + d["title"])
    out.append("")
    out.append("> 深读卡 · 锚点 " + link(anchor["name"]) + " · " + d["subtitle"])
    out.append("")
    out.append("> [!abstract] 一句话")
    out.append("> " + d["lead"])
    out.append("")

    st = d.get("structure")
    if st:
        out.append("## 01 · " + st["title"])
        out.append("")
        out.append(st["intro"])
        out.append("")
        out.append("| 环节 | 说明 |")
        out.append("|---|---|")
        for it in st["items"]:
            out.append("| **" + it["k"] + "** | " + it["v"] + " |")
        out.append("")
        if st.get("note"):
            out.append("> " + st["note"])
            out.append("")

    de = d.get("decisions")
    if de:
        out.append("## 02 · " + de["title"])
        out.append("")
        out.append(de["intro"])
        out.append("")
        for it in de["items"]:
            out.append("### " + it["q"])
            out.append("")
            out.append("**结论：** " + it["a"])
            out.append("")
            out.append(it["why"])
            out.append("")
            if it.get("cost"):
                out.append("> [!warning] 代价")
                out.append("> " + it["cost"])
                out.append("")

    fa = d.get("failures")
    if fa:
        out.append("## 03 · " + fa["title"])
        out.append("")
        out.append(fa["intro"])
        out.append("")
        for it in fa["items"]:
            out.append("### " + it["k"])
            out.append("")
            out.append(it["v"])
            out.append("")
            if it.get("fix"):
                out.append("**修法：** " + it["fix"])
                out.append("")

    pa = d.get("path")
    if pa:
        out.append("## 04 · " + pa["title"])
        out.append("")
        out.append(pa["intro"])
        out.append("")
        out.append("| 阶段 | 动作 | 产出 |")
        out.append("|---|---|---|")
        for s in pa["steps"]:
            out.append("| **" + s["w"] + "** | " + s["do"] + " | " + s["out"] + " |")
        out.append("")
        if pa.get("code"):
            out.append("```" + pa["code"].get("lang", "") )
            out.append(pa["code"]["text"])
            out.append("```")
            out.append("")
        if pa.get("note"):
            out.append("> " + pa["note"])
            out.append("")

    if d.get("refs"):
        out.append("## 05 · 参考")
        out.append("")
        for r in d["refs"]:
            if r.get("url"):
                out.append("- [" + r["t"] + " · " + r["d"] + "](" + r["url"] + ")")
            else:
                out.append("- " + r["t"] + " · " + r["d"])
        out.append("")

    if d.get("related"):
        out.append("## 相关概念")
        out.append("")
        for rid in d["related"]:
            if rid in by_id:
                out.append("- " + link(by_id[rid]["name"]) + " — " + by_id[rid]["oneLine"])
        out.append("")

    with io.open(os.path.join(DEEP_DIR, DEEP_PREFIX + safe(d["title"]) + ".md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))

# --- deep index ---
di = ["---", "type: agent-map-nav", "id: deep-index", "tags: [agent, nav, deep]", "---", ""]
di.append("# 深读专题")
di.append("")
di.append("深读卡不是新节点。坐标不变，只是把某个概念往下挖一层：内部结构、关键决策、失败模式、上手路径。")
di.append("")
for d in DEEPS:
    a = by_id[d["id"]]
    di.append("## " + deeplink(d["title"]))
    di.append("")
    di.append("> 锚点 " + link(a["name"]) + " · `" + a["dot"] + "` · " + d["subtitle"])
    di.append("")
    di.append(d["lead"])
    di.append("")
    secs = []
    if d.get("structure"): secs.append("内部结构（" + str(len(d["structure"]["items"])) + "）")
    if d.get("decisions"): secs.append("关键决策（" + str(len(d["decisions"]["items"])) + "）")
    if d.get("failures"): secs.append("失败模式（" + str(len(d["failures"]["items"])) + "）")
    if d.get("path"): secs.append("上手路径（" + str(len(d["path"]["steps"])) + " 步）")
    di.append("包含：" + " · ".join(secs))
    di.append("")
with io.open(os.path.join(VAULT, "00_导航", "深读专题.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(di))

# --- link deep cards from their anchor concept notes ---
for d in DEEPS:
    a = by_id[d["id"]]
    p = os.path.join(NODE_DIR, safe(a["name"]) + ".md")
    txt = io.open(p, encoding="utf-8").read()
    marker = "## 深读"
    if marker not in txt:
        inject = ("## 深读\n\n"
                  "> 这个概念有一张展开到可动手粒度的深读卡："
                  + deeplink(d["title"]) + "\n\n")
        idx2 = txt.find("## 关联概念")
        if idx2 < 0:
            idx2 = txt.find("## 常见误判")
        if idx2 < 0:
            txt = txt + "\n" + inject
        else:
            txt = txt[:idx2] + inject + txt[idx2:]
        with io.open(p, "w", encoding="utf-8") as f:
            f.write(txt)

print("HTML:", os.path.getsize(os.path.join(OUT, "Agent知识地图.html")), "bytes")
print("nodes:", len(nodes), "cells:", len(cells), "links:", sum(len(n.get("rel",[])) for n in nodes))
print("vault files:", len(os.listdir(NODE_DIR)), "concept notes")
print("deep cards:", len(DEEPS), "->", ", ".join(d["title"] for d in DEEPS))

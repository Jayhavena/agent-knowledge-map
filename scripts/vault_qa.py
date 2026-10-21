"""Verify the Obsidian vault: every [[wikilink]] resolves to an existing note, frontmatter parses, no dupes."""
import io, os, re, json, collections, sys

BASE = os.path.dirname(os.path.abspath(__file__))
VAULT = os.path.join(BASE, "..", "Obsidian-Agent知识库")

notes = {}
for root, dirs, files in os.walk(VAULT):
    for f in files:
        if f.endswith(".md"):
            p = os.path.join(root, f)
            rel = os.path.relpath(p, VAULT).replace("\\", "/")
            notes[rel[:-3]] = p

names = {os.path.basename(k) for k in notes}
print("notes:", len(notes))

broken = []
for rel, p in notes.items():
    txt = io.open(p, encoding="utf-8").read()
    for m in re.finditer(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]", txt):
        target = m.group(1).strip()
        base = os.path.basename(target)
        if target in notes or base in names:
            continue
        broken.append((rel, target))

print("broken links:", len(broken))
for b in broken[:15]:
    print("  ", b)

# frontmatter sanity
bad_fm = []
for rel, p in notes.items():
    txt = io.open(p, encoding="utf-8").read()
    if not txt.startswith("---\n"):
        bad_fm.append(rel); continue
    end = txt.find("\n---\n", 4)
    if end < 0:
        bad_fm.append(rel); continue
    fm = txt[4:end]
    for line in fm.split("\n"):
        if ":" not in line:
            bad_fm.append((rel, line))
print("bad frontmatter:", bad_fm[:5] or "none")

# duplicate note filenames would cause ambiguous links
dup = [k for k, v in collections.Counter(os.path.basename(k) for k in notes).items() if v > 1]
print("duplicate basenames:", dup or "none")

# concept notes must all have required sections
req = ["## 一句话", "## 它解决什么问题", "## 它新在哪", "## 常见误判 / 坑"]
missing = []
for rel, p in notes.items():
    if not rel.startswith("10_概念/"):
        continue
    txt = io.open(p, encoding="utf-8").read()
    for r in req:
        if r not in txt:
            missing.append((rel, r))
print("concept notes missing sections:", missing[:5] or "none")
print("concept note count:", sum(1 for k in notes if k.startswith("10_概念/")))

# deep notes must link back to a real anchor and carry the 4-section shape
import json
ddir = os.path.join(VAULT, "20_深读")
deep_files = [f for f in os.listdir(ddir)] if os.path.isdir(ddir) else []
print("deep notes:", len(deep_files))
anchor_re = re.compile(r"^anchor:\s*(\S+)$", re.M)
deps = set()
for f in deep_files:
    txt = io.open(os.path.join(ddir, f), encoding="utf-8").read()
    m = anchor_re.search(txt)
    if not m:
        deps.add("missing anchor: " + f); continue
    anchor = m.group(1)
    # anchor must resolve to a concept note id
    found = any(('id: ' + anchor + "\n") in io.open(notes[k], encoding="utf-8").read().split("---")[1] + "\n"
                for k in notes if k.startswith("10_概念/"))
    if not found:
        deps.add("anchor not found: " + anchor)
    for h in ["## 01 ·", "## 02 ·", "## 03 ·", "## 04 ·"]:
        if h not in txt:
            deps.add(f + " missing section " + h)
print("deep note issues:", sorted(deps) or "none")

# nav notes
for k in sorted(notes):
    if k.startswith("00_导航/"):
        sz = os.path.getsize(notes[k])
        print(f"  {k}: {sz} bytes")

# ---- gate ----
gate = []
if broken: gate.append(f"{len(broken)} 条断链")
if bad_fm: gate.append(f"{len(bad_fm)} 条 frontmatter 异常")
if dup: gate.append(f"重复文件名: {dup}")
if missing: gate.append(f"{len(missing)} 个概念笔记缺少小节")
if deps: gate.append(f"深读卡问题: {sorted(deps)}")
print()
if gate:
    print("FAILURES:")
    for g in gate: print("  -", g)
    sys.exit(1)
print("vault checks passed.")

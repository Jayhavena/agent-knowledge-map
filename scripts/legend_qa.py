"""Enumerate every rendered badge and confirm each distinct label maps to a distinct,
visually-defined class. This is the data-side companion to badge_test.js."""

import io, os, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)

html = io.open(os.path.join(ROOT, "Agent知识地图.html"), encoding="utf-8").read()
css = html[html.index("<style>"): html.index("</style>")]
js = html[html.rindex("<script>"):]

def parse_map(name):
    block = re.search(name + r"\s*=\s*\{([^}]*)\}", js).group(1)
    return dict(re.findall(r'"([^"]+)":\s*"([a-z]+)"', block))

TIER = parse_map("TIER_CLASS")
MAT = parse_map("MAT_CLASS")

print("TIER_CLASS:", TIER)
print("MAT_CLASS :", MAT)

def rule(cls):
    m = re.search(r"\.badge\." + cls + r"\{([^}]*)\}", css)
    return m.group(1) if m else None

fails = []
for label, cls in list(TIER.items()) + list(MAT.items()):
    body = rule(cls)
    if body is None:
        fails.append(f"{label} -> .badge.{cls} 规则不存在")
    elif "background" not in body:
        fails.append(f"{label} -> .badge.{cls} 未设置 background")
    else:
        print(f"  ok  {label:<4} -> .badge.{cls}")

# every value declared in meta.json's legend must have a mapping
import json
meta = json.load(io.open(os.path.join(ROOT, "data", "meta.json"), encoding="utf-8"))
expected_tiers = [x["key"] for x in meta["legend"]["must"]]
expected_mats = [x["key"] for x in meta["legend"]["maturity"]]

missing_tier = [t for t in expected_tiers if t not in TIER]
missing_mat = [m for m in expected_mats if m not in MAT]
if missing_tier:
    fails.append("图例中的权重值缺少映射: " + ",".join(missing_tier))
if missing_mat:
    fails.append("图例中的成熟度值缺少映射: " + ",".join(missing_mat))

print()
if fails:
    for f in fails:
        print("FAIL " + f)
    sys.exit(1)
print("all legend values have a distinct, styled badge class")

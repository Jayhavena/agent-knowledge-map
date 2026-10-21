"""Gate audit: prove that every script listed in publish.py's CHECKS can actually fail.

Root cause this guards against: report-only scripts that always exit 0 were listed
as "checks", so content regressions passed the pipeline silently (stage-0 finding S0-001).
"""
import io, os, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
t = io.open(os.path.join(BASE, "publish.py"), encoding="utf-8").read()

# extract only the CHECKS list (find the matching closing bracket)
i = t.index("CHECKS = [")
depth = 0
j = i
for k in range(i, len(t)):
    if t[k] == "[":
        depth += 1
    elif t[k] == "]":
        depth -= 1
        if depth == 0:
            j = k
            break
block = t[i:j]
checks = re.findall(r'os\.path\.join\((?:BASE|ROOT),\s*"([^"]+)"', block)
# build.py 是构建步骤，不是检查步骤；HTML 路径是 smoke.js 的参数，不是被检查对象
checks = [c for c in checks if c not in ("build.py", "Agent知识地图.html")]

print("publish CHECKS:", len(checks), "scripts")
fails = []

for rel in checks:
    full = os.path.join(BASE, rel)
    if not os.path.exists(full):
        fails.append(f"{rel}: 文件不存在")
        continue
    src = io.open(full, encoding="utf-8").read()
    if rel.endswith(".py"):
        can_fail = "sys.exit" in src or "raise SystemExit" in src
    else:
        can_fail = ("process.exit" in src) or ("sys.exit" in src)
    # also require at least one condition that could trigger it: a comparison or length check
    has_decision = bool(re.search(r"(if .*len\(|if .*fails|if .*bad|if .*issues|if .*gate|VERDICT)", src))
    status = "ok" if (can_fail and has_decision) else "CANNOT FAIL"
    print(f"  {rel:<24} can_fail={can_fail}  decision={has_decision}  {status}")
    if not (can_fail and has_decision):
        fails.append(f"{rel}: 无失败路径")

# the meta-check itself must also be able to fail (obviously, it exits above)
if "sys.exit" not in io.open(os.path.join(BASE, "gate_audit.py"), encoding="utf-8").read():
    fails.append("gate_audit.py 自身无失败路径")

if fails:
    print("\nFAILURES:")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("\nall gates can fail — none are report-only")

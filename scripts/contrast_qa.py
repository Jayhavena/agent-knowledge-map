"""Dark/light contrast audit: parse both variable blocks and check WCAG ratios for real text pairs."""
import io, os, re, math

BASE = os.path.dirname(os.path.abspath(__file__))
s = io.open(os.path.join(BASE, "template.html"), encoding="utf-8").read()
style = s[s.index("<style>") + 7: s.index("</style>")]

def block(selector):
    i = style.index(selector)
    j = style.index("}", i)
    txt = style[i:j]
    out = {}
    for m in re.finditer(r"(--[\w-]+)\s*:\s*([^;]+);", txt):
        out[m.group(1)] = m.group(2).strip()
    return out

light = block(":root{")
dark = block('html[data-theme="dark"]{')

def norm(c):
    c = c.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{3}", c):
        return "#" + "".join(ch * 2 for ch in c[1:])
    return c

def parse(c):
    c = norm(c)
    if c.startswith("#"):
        v = c[1:]
        if len(v) != 6:
            return None
        return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
    m = re.match(r"rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)", c)
    if m:
        return tuple(float(m.group(i)) for i in (1, 2, 3))
    return None

def lum(rgb):
    def f(u):
        u = u / 255
        return u / 12.92 if u <= 0.03928 else ((u + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)

# text/background pairs that actually co-occur in the stylesheet
PAIRS = [
    ("--ink",   "--paper",  "正文 on 页面底色"),
    ("--ink2",  "--paper",  "次级文字 on 页面底色"),
    ("--ink3",  "--paper",  "弱化文字 on 页面底色"),
    ("--ink",   "--paper2", "正文 on 卡片底色"),
    ("--ink2",  "--paper2", "次级文字 on 卡片底色"),
    ("--inkInv","--ink",    "反色文字 on 强调块"),
    ("--tCoreFg","--tCoreBg","徽章·核心"),
    ("--tMidFg", "--tMidBg", "徽章·进阶"),
    ("--tStableFg","--tStableBg","徽章·稳定"),
    ("--tMainFg", "--tMainBg", "徽章·主流"),
    ("--tOptFg",  "--tOptBg",  "徽章·可选"),
    ("--tFrontFg","--tFrontBg","徽章·前沿"),
    ("--tContraFg","--tContraBg","徽章·争议"),
    ("--tStFg",  "--tStBg",  "徽章·掌握度"),
    ("--warnTxt","--warnBg", "警示框文字"),
    ("--warnFg", "--warnBg", "警示框标题"),
    ("--ink2",  "--hover",   "行悬停文字"),
    ("--ink",   "--hover2",  "概念悬停文字"),
]

print(f"{'pair':<28} {'light':>7} {'dark':>7}  verdict")
print("-" * 62)
bad = []
for fg, bg, label in PAIRS:
    row = []
    for theme, blk in (("light", light), ("dark", dark)):
        f = parse(blk.get(fg, light[fg]))
        b = parse(blk.get(bg, light[bg]))
        if not f or not b:
            row.append(None); continue
        row.append(ratio(f, b))
    l, d = row
    ok = (l is not None and d is not None and l >= 4.45 and d >= 4.45)
    soft = (l is not None and d is not None and l >= 3.0 and d >= 3.0)
    verdict = "OK" if ok else ("large-only" if soft else "FAIL")
    if not soft:
        bad.append((label, l, d))
    ls = f"{l:.1f}" if l else "-"
    ds = f"{d:.1f}" if d else "-"
    print(f"{label:<28} {ls:>7} {ds:>7}  {verdict}")

print()
if bad:
    print("BELOW 3.0 (needs fixing):")
    for label, l, d in bad:
        print(f"  {label}: light={l:.2f} dark={d:.2f}")
else:
    print("No pair below 3.0")

# var parity: dark must define everything light does
missing = set(light) - set(dark) - {"--radius", "--sans", "--serif", "--mono"}
extra = set(dark) - set(light)
print("\nvars only in light:", sorted(missing) or "none")
print("vars only in dark:", sorted(extra) or "none")

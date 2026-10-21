// Badge rendering: every tier/maturity value must map to its own class, and that class
// must actually set a background. Guards against the "silent fallthrough" bug where a
// missing mapping made 稳定 and 主流 render identically and 可选 lose its background.
const fs = require("fs");
const path = require("path");

const html = fs.readFileSync(process.argv[2] || path.join(__dirname, "..", "Agent知识地图.html"), "utf8");
const css = html.slice(html.indexOf("<style>"), html.indexOf("</style>"));
const ALL = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
const DATA = JSON.parse(ALL[1].replace(/^const DATA = /, "").replace(/;\s*$/, ""));

// ---- minimal DOM, same shape as smoke.js ----
const ctx = { get: () => () => {}, set: () => true };
class El {
  constructor(tag, id) {
    this.tagName = (tag || "div").toUpperCase();
    this.id = id || "";
    this._html = ""; this.dataset = {}; this.style = {}; this.value = ""; this._cl = new Set();
    const self = this;
    this.classList = {
      add: (...c) => c.forEach((x) => self._cl.add(x)),
      remove: (...c) => c.forEach((x) => self._cl.delete(x)),
      toggle: (c, on) => { const want = on === undefined ? !self._cl.has(c) : on; want ? self._cl.add(c) : self._cl.delete(c); },
      contains: (c) => self._cl.has(c),
    };
    this._listeners = {};
  }
  get innerHTML() { return this._html; }
  set innerHTML(v) { this._html = String(v); }
  get textContent() { return this._html.replace(/<[^>]*>/g, ""); }
  set textContent(v) { this._html = String(v); }
  get offsetParent() { return {}; }
  appendChild(c) { return c; }
  addEventListener(t, f) { (this._listeners[t] = this._listeners[t] || []).push(f); }
  querySelectorAll() { return []; }
  querySelector() { return null; }
  getBoundingClientRect() { return { width: 1400, height: 780, left: 0, top: 0 }; }
  getContext() { return ctx; }
  focus() {}
  click() { if (this._onclick) this._onclick({ target: this, preventDefault() {} }); }
  set onclick(f) { this._onclick = f; }
  get onclick() { return this._onclick; }
  set oninput(f) { this._listeners.input = [f]; }
  set onchange(f) { this._listeners.change = [f]; }
  get onchange() { return this._listeners.change && this._listeners.change[0]; }
}
const ids = ["layerchips","ftier","fmat","fst","reset","q","count","tabs","matrix","outline","gcanvas",
  "gtip","gleg","drawer","scrim","dwtop","dwbody","help","helpbtn","helpclose","helperules","steps",
  "locbody","deepnav","deepmain","themebtn"];
const els = {};
ids.forEach((id) => (els[id] = new El("div", id)));

const THEME = {
  "--l0":"#6b7a8f","--l1":"#2f7d6b","--l2":"#7a6a9c","--l3":"#a8792c","--l4":"#bf5e48","--l5":"#3d7ea6","--l6":"#6f6a63",
};
global.window = { devicePixelRatio: 1, addEventListener: () => {}, matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }), scrollTo: () => {} };
global.document = {
  getElementById: (id) => els[id] || (els[id] = new El("div", id)),
  createElement: () => new El("div"),
  querySelectorAll: () => [],
  addEventListener: () => {},
  activeElement: { tagName: "BODY" },
  documentElement: { setAttribute() {}, getAttribute: () => "light" },
};
global.getComputedStyle = () => ({ getPropertyValue: (n) => THEME[n] || "" });
global.localStorage = { _d: {}, getItem(k) { return this._d[k] || null; }, setItem(k, v) { this._d[k] = v; } };
global.navigator = { clipboard: null };
global.location = { hash: "", pathname: "/", search: "" };
global.history = { replaceState: () => {} };
global.requestAnimationFrame = (f) => f();
global.setTimeout = () => 0;

const runApp = new Function("DATA", "window", ALL[ALL.length - 1] + "\n;return window.__agentmap;");
const APP = runApp(DATA, global.window);
if (!APP || typeof APP.openNode !== "function") {
  console.error("could not obtain app API; got:", APP);
  process.exit(1);
}

// ---- assertions ----
const fails = [];
const ok = (name, cond, extra) => { if (!cond) fails.push(name + (extra ? " <" + extra + ">" : "")); };

function ruleFor(cls) {
  const m = css.match(new RegExp("\\.badge\\." + cls + "\\{([^}]*)\\}"));
  return m ? m[1] : null;
}

// 1. every enum value gets its own distinct class
const TIERS = [...new Set(DATA.nodes.map((n) => n.tier))];
const MATS = [...new Set(DATA.nodes.map((n) => n.maturity))];
console.log("tier values:", TIERS.join(", "));
console.log("maturity values:", MATS.join(", "));

function classOf(html, label) {
  // pull the badge whose text equals the label
  const re = new RegExp('<span class="badge ([a-z-]*)"\\s*>' + label + "<");
  const m = html.match(re);
  return m ? m[1] : null;
}

const tierClasses = {}, matClasses = {};
for (const t of TIERS) {
  const h = `<span class="badge core">核心</span>`; // placeholder, real call below
}
// use the real renderer through the outline (it emits badgeHTML output)
els.outline.innerHTML = "";
// trigger a render of all nodes: open each node's drawer and read its badges
for (const cat of ["tier", "maturity"]) {
  for (const v of cat === "tier" ? TIERS : MATS) {
    const sample = DATA.nodes.find((n) => (cat === "tier" ? n.tier : n.maturity) === v);
    if (!sample) continue;
    APP.openNode(sample.id);
    const cls = classOf(els.dwtop.innerHTML, v);
    (cat === "tier" ? tierClasses : matClasses)[v] = cls;
    ok(`${cat}「${v}」有类名`, cls !== null && cls !== "", String(cls));
    if (cls) {
      const body = ruleFor(cls);
      ok(`${cat}「${v}」的类 .badge.${cls} 存在`, body !== null, "规则缺失");
      ok(`${cat}「${v}」的类 .badge.${cls} 设了背景`, body && /background/.test(body), "无 background");
    }
  }
}

// 2. no two maturity values share a class
const matVals = Object.values(matClasses).filter(Boolean);
ok("成熟度各类互不相同", new Set(matVals).size === matVals.length, matVals.join("/"));
const tierVals = Object.values(tierClasses).filter(Boolean);
ok("权重各类互不相同", new Set(tierVals).size === tierVals.length, tierVals.join("/"));

// 3. no dead badge background variable
const defined = [...new Set([...css.matchAll(/(--t[A-Za-z]+Bg)\s*:/g)].map((m) => m[1]))];
const rulesOnly = css.slice(css.lastIndexOf("color-scheme: dark"));
const dead = defined.filter((v) => !new RegExp("var\\(" + v + "\\)").test(rulesOnly));
ok("无未引用的徽章背景变量", dead.length === 0, dead.join(","));

// 4. chip geometry: the shortest label (2 CJK chars) must stay a tag, not a circle.
//    A pill radius plus a tiny font made 2-char badges render taller than wide.
const base = css.match(/\.badge\{([^}]*)\}/);
ok("存在 .badge 基础规则", !!base);
if (base) {
  const b = base[1];
  const fs = parseFloat((b.match(/font-size:\s*([\d.]+)px/) || [])[1]);
  const lh = parseFloat((b.match(/line-height:\s*([\d.]+)/) || [])[1]);
  const pad = b.match(/padding:\s*(\d+)px\s+(\d+)px/);
  const rad = parseFloat((b.match(/border-radius:\s*([\d.]+)px/) || [])[1]);

  ok("badge 字号 >= 10px", fs >= 10, fs + "px");
  ok("badge line-height 为数值且 < 1.6", !isNaN(lh) && lh < 1.6, String(lh));
  ok("badge 圆角 <= 6px（避免压成圆形）", !isNaN(rad) && rad <= 6, rad + "px");
  ok("badge 用 inline-flex 居中", /display:\s*inline-flex/.test(b) && /align-items:\s*center/.test(b));

  if (pad && !isNaN(fs) && !isNaN(lh)) {
    const h = fs * lh + 2 * parseInt(pad[1], 10) + 2;          // + borders
    const w2 = 2 * fs + 2 * parseInt(pad[2], 10) + 2;          // two CJK chars
    ok("两字徽章宽高比 > 1.5（不是圆）", w2 / h > 1.5,
       `w=${w2.toFixed(1)} h=${h.toFixed(1)} ratio=${(w2 / h).toFixed(2)}`);
  }
  ok("徽章容器垂直居中（不拉伸）",
     /\.dw-badges\{[^}]*align-items:\s*center/.test(css), "dw-badges 缺 align-items");
}

console.log("\nclass mapping:");
console.log("  tier:", JSON.stringify(tierClasses));
console.log("  maturity:", JSON.stringify(matClasses));

if (fails.length) {
  console.error("\nFAILURES:\n - " + fails.join("\n - "));
  process.exit(1);
}
console.log("\nall badge checks passed");

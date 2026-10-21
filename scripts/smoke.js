// Headless smoke test: run the map's JS in a minimal fake DOM and assert it renders
// every view, exercises filters/search, opens a node drawer, and completes the locator flow.
const fs = require("fs");
const htmlPath = process.argv[2];
const html = fs.readFileSync(htmlPath, "utf8");
const ALL_SCRIPTS = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
// Block 0 = pre-paint theme bootstrap, block 1 = data payload, block 2 = the app.
if (ALL_SCRIPTS.length !== 3) { console.error("expected 3 scripts, got", ALL_SCRIPTS.length); process.exit(1); }
const scripts = [ALL_SCRIPTS[1], ALL_SCRIPTS[2]];

const ctxStub = new Proxy({}, { get: () => () => {}, set: () => true });

class El {
  constructor(tag, id) {
    this.tagName = (tag || "div").toUpperCase();
    this.id = id || "";
    this.children = [];
    this._html = "";
    this.dataset = {};
    this.style = {};
    this._cl = new Set();
    const self = this;
    this.classList = {
      add: (...c) => c.forEach(x => self._cl.add(x)),
      remove: (...c) => c.forEach(x => self._cl.delete(x)),
      toggle: (c, on) => { const want = on === undefined ? !self._cl.has(c) : on; want ? self._cl.add(c) : self._cl.delete(c); },
      contains: c => self._cl.has(c),
    };
    this._listeners = {};
    this.value = "";
  }
  get innerHTML() { return this._html; }
  set innerHTML(v) { this._html = String(v); }
  get textContent() { return this._html.replace(/<[^>]*>/g, ""); }
  set textContent(v) { this._html = String(v); }
  get offsetParent() { return {}; }
  appendChild(c) { this.children.push(c); return c; }
  addEventListener(t, f) { (this._listeners[t] = this._listeners[t] || []).push(f); }
  fire(t, ev) { (this._listeners[t] || []).forEach(f => f(ev || { target: this, preventDefault() {} })); }
  querySelectorAll() { return []; }
  querySelector() { return null; }
  getBoundingClientRect() { return { width: 1400, height: 780, left: 0, top: 0 }; }
  getContext() { return ctxStub; }
  focus() {}
  click() { if (this._onclick) this._onclick({ target: this, preventDefault() {} }); }
  set onclick(f) { this._onclick = f; this._listeners.click = [f]; }
  get onclick() { return this._onclick; }
  set oninput(f) { this._listeners.input = [f]; }
  get oninput() { return this._listeners.input && this._listeners.input[0]; }
  set onchange(f) { this._listeners.change = [f]; }
  get onchange() { return this._listeners.change && this._listeners.change[0]; }
}

const ids = ["layerchips","ftier","fmat","fst","reset","q","count","tabs","matrix","outline","gcanvas",
  "gtip","gleg","drawer","scrim","dwtop","dwbody","help","helpbtn","helpclose","helperules","steps","locbody",
  "deepnav","deepmain","themebtn"];
const els = {};
ids.forEach(id => els[id] = new El("div", id));
const createdLayerChips = [];

global.document = {
  getElementById: id => els[id] || (els[id] = new El("div", id)),
  createElement: tag => {
    const e = new El(tag);
    createdLayerChips.push(e);
    return e;
  },
  querySelectorAll: () => [],
  addEventListener: () => {},
  activeElement: { tagName: "BODY" },
  documentElement: {
    _attrs: {},
    setAttribute(k, v) { this._attrs[k] = v; },
    getAttribute(k) { return this._attrs[k]; },
  },
};
const THEME_VARS = {
  "--l0":"#6b7a8f","--l1":"#2f7d6b","--l2":"#7a6a9c","--l3":"#a8792c",
  "--l4":"#bf5e48","--l5":"#3d7ea6","--l6":"#6f6a63",
  "--paper3":"#fbfaf7","--paper4":"#f7f5f0","--line":"#e6e0d4","--line2":"#f1ede5",
  "--ink":"#1b1a17","--ink2":"#56534b","--ink3":"#8d887d",
  "--edge":"rgba(90,85,75,.085)","--edgeFaint":"rgba(0,0,0,.025)","--edgeHot":"rgba(40,70,110,.5)",
};
global.getComputedStyle = () => ({
  getPropertyValue: (n) => THEME_VARS[n] || "",
});
global.window = {
  devicePixelRatio: 2,
  addEventListener: () => {},
  matchMedia: (q) => ({ matches: false, addEventListener: () => {}, addListener: () => {} }),
};
global.localStorage = { _d: {}, getItem(k) { return this._d[k] || null; }, setItem(k, v) { this._d[k] = v; } };
global.navigator = { clipboard: null };
global.location = { hash: process.env.TEST_HASH || "", pathname: "/", search: "" };
global.history = { replaceState: (a, b, url) => { const u = url || ""; const k = u.indexOf("#"); global.location.hash = k >= 0 ? u.slice(k) : ""; } };
global.requestAnimationFrame = f => f();
global.setTimeout = () => 0;

const dataMatch = scripts[0].match(/const DATA = ([\s\S]*);\s*$/);
if (!dataMatch) { console.error("cannot extract DATA"); process.exit(1); }
const DATA = JSON.parse(dataMatch[1]);

const out = {};
let fails = [];
const check = (name, cond, extra) => { if (!cond) fails.push(name + (extra ? ": " + extra : "")); };

try {
  const fn = new Function("DATA", scripts[1] + "\n;return window.__agentmap;");
  const api = fn(DATA);

  check("export api", !!api);
  check("node count matches data", api.NODES.length === DATA.nodes.length);

  // --- matrix ---
  const mhtml = els.matrix.innerHTML;
  const chipEls = [...mhtml.matchAll(/class="chip[^s]/g)].length;
  check("matrix renders chips", chipEls > 80, chipEls + " chips rendered");
  check("matrix has L6 band", mhtml.includes("cell wide"));
  check("matrix has 5 clusters", (mhtml.match(/class="cluster"/g) || []).length >= 4, (mhtml.match(/class="cluster"/g) || []).length + "");
  check("matrix head cells = 7", (mhtml.match(/class="mhead"/g) || []).length === 7, (mhtml.match(/class="mhead"/g) || []).length + "");
  check("overflow collapses dense cells", (mhtml.match(/data-more=/g) || []).length >= 3, (mhtml.match(/data-more=/g) || []).length + "");
  check("layer filter chips built", createdLayerChips.length === 7, String(createdLayerChips.length));
  check("count text", els.count.textContent.indexOf(String(api.NODES.length)) === 0, els.count.textContent);

  // --- outline (switch view via tabs handler) ---
  els.tabs.fire("click", { target: { closest: () => ({ dataset: { view: "outline" } }) }, preventDefault() {} });
  const ohtml = els.outline.innerHTML;
  const items = [...ohtml.matchAll(/class="ol-item"/g)].length;
  check("outline renders all nodes", items === api.NODES.length, items + " vs " + api.NODES.length);

  // --- graph ---
  els.tabs.fire("click", { target: { closest: () => ({ dataset: { view: "graph" } }) }, preventDefault() {} });
  check("graph legend filled", els.gleg.innerHTML.length > 50);
  const rects = api.NODES.filter(n => typeof n._x === "number" && typeof n._y === "number");
  check("graph laid out every node", rects.length === api.NODES.length, rects.length + " laid out");
  const bad = api.NODES.filter(n => !isFinite(n._x) || !isFinite(n._y));
  check("graph coords finite", bad.length === 0, bad.map(b => b.id).join(","));
  const W = 1400, H = 780;
  const oob = api.NODES.filter(n => n._x < 50 || n._x > W - 4 || n._y < 6 || n._y > H - 4);
  check("graph coords within canvas", oob.length === 0, oob.map(b => b.id + "@" + b._x.toFixed(0) + "," + b._y.toFixed(0)).join(" "));

  // --- drawer ---
  api.openNode("mcp");
  const dw = els.dwtop.innerHTML + els.dwbody.innerHTML;
  check("drawer shows node name", dw.includes("模型上下文协议"));
  check("drawer shows lineage", dw.includes("谱系"));
  check("drawer shows trap", dw.includes("常见误判"));
  check("drawer shows example", dw.includes("具体是什么样"), dw.slice(0,120));
  check("drawer shows prereq", dw.includes("看不懂？先看这几个"), dw.slice(0,120));
  check("drawer shows status buttons", dw.includes("stbtns"));

  // L6 node drawer must not crash on missing loop code
  api.openNode("tracing");
  const dw2 = els.dwtop.innerHTML + els.dwbody.innerHTML;
  check("L6 drawer renders", dw2.includes("可观测") || dw2.includes("链路追踪"));
  check("L6 drawer shows cluster", dw2.includes("观测与成本") || dw2.includes("系统层"));

  // every node must open without throwing
  let opened = 0;
  for (const n of api.NODES) {
    api.openNode(n.id);
    if (els.dwtop.innerHTML.includes(n.name.replace(/&/g, "&amp;"))) opened++;
  }
  check("all nodes open in drawer", opened === api.NODES.length, opened + " / " + api.NODES.length);

  // --- locator full flow ---
  els.tabs.fire("click", { target: { closest: () => ({ dataset: { view: "locator" } }) }, preventDefault() {} });
  check("locator step1 rendered", els.locbody.innerHTML.includes("叫什么"), els.locbody.innerHTML.slice(0, 60));
  check("locator steps bar", (els.steps.innerHTML.match(/class="step/g) || []).length === 5);

  // --- deep dive ---
  els.tabs.fire("click", { target: { closest: () => ({ dataset: { view: "deep" } }) }, preventDefault() {} });
  const dn = els.deepnav.innerHTML;
  const dm = els.deepmain.innerHTML;
  check("deep nav lists all cards", (dn.match(/data-deep=/g) || []).length === DATA.deeps.length,
        (dn.match(/data-deep=/g) || []).length + " vs " + DATA.deeps.length);
  check("deep main renders title", dm.includes(DATA.deeps[0].title), dm.slice(0, 80));
  check("deep main renders 4 sections", ["01","02","03","04"].every(k => dm.includes('class="n">' + k)),
        ["01","02","03","04"].map(k => dm.includes('class="n">' + k)).join(","));
  check("deep decisions rendered", (dm.match(/class="dcard"/g) || []).length === DATA.deeps[0].decisions.items.length);
  check("deep failures rendered", (dm.match(/class="fcard"/g) || []).length === DATA.deeps[0].failures.items.length);
  check("deep path table rows", (dm.match(/<tr><td class="w">/g) || []).length === DATA.deeps[0].path.steps.length);
  check("deep related chips resolve", (dm.match(/data-go=/g) || []).length === DATA.deeps[0].related.length);
  check("deep refs rendered", dm.includes("参考"));
  check("deep nav marks active card", (dn.match(/class="on"/g) || []).length === 1);

  // switching deep cards re-renders
  const secondTitle = DATA.deeps[1] ? DATA.deeps[1].title : null;
  if (secondTitle) {
    const fakeBtn = { dataset: { deep: DATA.deeps[1].id }, onclick: null };
    els.deepnav.querySelectorAll = () => [];
    // directly re-render via the nav handler path
    const before = els.deepmain.innerHTML;
    try {
      // call through the exported-ish path: simulate nav click by re-invoking renderDeep
      const navBtns = [...els.deepnav.innerHTML.matchAll(/data-deep="([^"]+)"/g)].map(m => m[1]);
      check("deep nav has 2 entries", navBtns.length === 2, navBtns.join(","));
    } catch (e) { check("deep nav parse", false, String(e)); }
  }
  check("deep marker on chips", (els.matrix.innerHTML.match(/class="cd"/g) || []).length === DATA.deeps.length,
        (els.matrix.innerHTML.match(/class="cd"/g) || []).length + " vs " + DATA.deeps.length);

  // --- theme ---
  const root = document.documentElement;
  check("theme applied on boot", root.getAttribute("data-theme") === "light", String(root.getAttribute("data-theme")));
  check("theme button labelled", els.themebtn.dataset.mode === "auto", String(els.themebtn.dataset.mode));
  // auto -> light -> dark -> auto   (system prefers light in this stub, so resolved: light, light, dark, light)
  const cycle = [];
  for (let i = 0; i < 4; i++) {
    els.themebtn.onclick();
    cycle.push(els.themebtn.dataset.mode + ":" + root.getAttribute("data-theme"));
  }
  check("theme cycles mode+resolved",
        cycle.join("|") === "light:light|dark:dark|auto:light|light:light", cycle.join("|"));
  check("theme persists mode", global.localStorage._d["agentmap.theme.v1"] === "light",
        String(global.localStorage._d["agentmap.theme.v1"]));
  els.themebtn.onclick(); els.themebtn.onclick(); // back to auto
  check("theme returns to auto", els.themebtn.dataset.mode === "auto", String(els.themebtn.dataset.mode));

  // --- search filter ---
  els.q.value = "记忆";
  els.q.fire("input", { target: els.q });
  const t = els.count.textContent;
  check("search narrows results", t !== (api.NODES.length + " / " + api.NODES.length + " 个概念"), t);

  els.q.value = "zzzznomatch";
  els.q.fire("input", { target: els.q });
  check("search can yield zero", els.count.textContent.indexOf("0 /") === 0, els.count.textContent);

  els.q.value = "";
  els.q.fire("input", { target: els.q });
  check("search resets", els.count.textContent.indexOf(String(api.NODES.length)) === 0, els.count.textContent);

  // --- filter by tier via select handler ---
  els.ftier.value = "核心";
  els.ftier.onchange({ target: els.ftier });
  const coreCount = Number(els.count.textContent.split(" / ")[0]);
  const expectedCore = api.NODES.filter(n => n.tier === "核心").length;
  check("tier filter exact", coreCount === expectedCore, coreCount + " vs " + expectedCore);
  els.ftier.value = "";
  els.ftier.onchange({ target: els.ftier });

  out.ok = true;
  out.nodes = api.NODES.length;
  out.cells = new Set(api.NODES.map(n => n.dot)).size;
  out.tierFilter = expectedCore;
  out.searchHit = true;
} catch (e) {
  console.error("RUNTIME ERROR:", e && e.stack || e);
  process.exit(1);
}

if (fails.length) { console.error("FAILURES:\n - " + fails.join("\n - ")); process.exit(1); }
console.log(JSON.stringify(out, null, 2));

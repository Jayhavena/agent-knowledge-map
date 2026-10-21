// Deep-link behaviour: a shared URL must open the right view and node, and navigation must update the hash.
const fs = require("fs");
const path = require("path");
const html = fs.readFileSync(path.join(__dirname, "..", "Agent知识地图.html"), "utf8");
const ALL = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
const dataRaw = ALL[1].replace(/^const DATA = /, "").replace(/;\s*$/, "");
const DATA = JSON.parse(dataRaw);

function run(hash) {
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
    fire(t, ev) { (this._listeners[t] || []).forEach((f) => f(ev || { target: this, preventDefault() {} })); }
    querySelectorAll() { return []; }
    querySelector() { return null; }
    getBoundingClientRect() { return { width: 1400, height: 780, left: 0, top: 0 }; }
    getContext() { return ctx; }
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
    "gtip","gleg","drawer","scrim","dwtop","dwbody","help","helpbtn","helpclose","helperules","steps",
    "locbody","deepnav","deepmain","themebtn"];
  const els = {};
  ids.forEach((id) => (els[id] = new El("div", id)));

  const win = {
    devicePixelRatio: 1,
    addEventListener: () => {},
    matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }),
    scrollTo: () => {},
    requestAnimationFrame: (f) => f(),
  };
  global.window = win;
  global.document = {
    getElementById: (id) => els[id] || (els[id] = new El("div", id)),
    createElement: () => new El("div"),
    querySelectorAll: () => [],
    addEventListener: () => {},
    activeElement: { tagName: "BODY" },
    documentElement: { setAttribute() {}, getAttribute: () => "light" },
  };
  global.getComputedStyle = () => ({ getPropertyValue: () => "" });
  global.localStorage = { _d: {}, getItem: (k) => this._d[k] || null, setItem() {} };
  global.localStorage = { _d: {}, getItem(k) { return this._d[k] || null; }, setItem(k, v) { this._d[k] = v; } };
  global.navigator = { clipboard: null };
  global.location = { hash, pathname: "/agent-knowledge-map/", search: "" };
  global.history = { replaceState: (a, b, url) => {
    const k = url.indexOf("#");
    global.location.hash = k >= 0 ? url.slice(k) : "";
  }};
  global.setTimeout = () => 0;

  const fn = new Function("DATA", ALL[ALL.length - 1] + "\n;return window.__agentmap;");
  const api = fn(DATA);
  return { api, els, loc: global.location };
}

const results = [];
function check(name, cond, extra) { results.push({ name, ok: !!cond, extra }); }

// 1. hash opens a node directly
let r = run("#node=mcp");
check("hash opens node drawer", r.els.dwtop.innerHTML.includes("模型上下文协议"), r.els.dwtop.innerHTML.slice(0, 50));
check("hash normalised back", r.loc.hash === "#node=mcp", r.loc.hash);

// 2. hash opens a view
r = run("#view=deep");
check("hash opens deep view", r.els.deepmain.innerHTML.length > 200, String(r.els.deepmain.innerHTML.length));
check("deep view hash preserved", r.loc.hash === "#view=deep", r.loc.hash);

// 3. view + node combined
r = run("#view=outline&node=rag");
check("combined hash sets view", r.els.outline.innerHTML.includes("ol-item"), String(r.els.outline.innerHTML.length));
check("combined hash opens node", r.els.dwtop.innerHTML.includes("检索增强生成"));

// 4. bad hash is ignored gracefully
r = run("#node=does-not-exist");
check("unknown node hash ignored", r.api.NODES.length === DATA.nodes.length && r.els.dwtop.innerHTML === "", "ok");

// 5. opening a node updates the hash (shareable)
r = run("");
r.api.openNode("memory-consolidation");
check("openNode writes hash", r.loc.hash === "#node=memory-consolidation", r.loc.hash);

// 6. switching view updates the hash and keeps the node out
r = run("");
r.api.showView("graph");
check("showView writes hash", r.loc.hash === "#view=graph", r.loc.hash);

// 7. every node id round-trips through the hash
r = run("");
let bad = [];
for (const n of DATA.nodes) {
  r.api.openNode(n.id);
  if (r.loc.hash !== "#node=" + n.id) bad.push(n.id);
}
check("all node ids produce valid hashes", bad.length === 0, bad.slice(0, 5).join(","));

const failed = results.filter((x) => !x.ok);
results.forEach((x) => console.log((x.ok ? "PASS " : "FAIL ") + x.name + (x.ok ? "" : "  <" + (x.extra || "") + ">")));
console.log("\n" + (results.length - failed.length) + "/" + results.length + " passed");
process.exit(failed.length ? 1 : 0);

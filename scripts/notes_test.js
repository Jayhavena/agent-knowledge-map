// v1.1 新功能测试：概念笔记 / 待深入标记 / 待整理清单 / 导出导入兼容 / 刷新后保留。
// 关键点：跑两遍应用实例（模拟刷新），确认数据真的来自 localStorage 而不是内存。
const fs = require("fs");
const path = require("path");

const html = fs.readFileSync(process.argv[2] || path.join(__dirname, "..", "Agent知识地图.html"), "utf8");
const ALL = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
const DATA = JSON.parse(ALL[1].replace(/^const DATA = /, "").replace(/;\s*$/, ""));

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
      toggle: (c, on) => { const w = on === undefined ? !self._cl.has(c) : on; w ? self._cl.add(c) : self._cl.delete(c); },
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
  setAttribute(name, value) { this[name] = String(value); }
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
  "locbody","deepnav","deepmain","themebtn","progmain","plegend","pExport","pImport","pFile","pClear","ptag",
  "nores","noq","pendAdd","pendOk","pendList","pendCount","memoInfo",
  "notepanel","npclose","dwNoteToggle","dnote","dflag","dnhint","dwModeCenter","dwModeSide"];
const els = {};
ids.forEach((id) => (els[id] = new El("div", id)));

let exported = "";
global.window = { devicePixelRatio: 1, addEventListener: () => {}, matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }), scrollTo: () => {} };
global.document = {
  getElementById: (id) => els[id] || (els[id] = new El("div", id)),
  createElement: () => new El("div"),
  body: { appendChild() {} },
  querySelectorAll: () => [],
  addEventListener: () => {},
  activeElement: { tagName: "BODY" },
  documentElement: { setAttribute() {}, getAttribute: () => "light" },
};
global.getComputedStyle = () => ({ getPropertyValue: (n) => ({ "--l1": "#2f7d6b" }[n] || "") });
// 注意：这里故意从空开始，由测试自己写入，验证写入路径
global.localStorage = {
  _d: {},
  getItem(k) { return Object.prototype.hasOwnProperty.call(this._d, k) ? this._d[k] : null; },
  setItem(k, v) { this._d[k] = String(v); },
  removeItem(k) { delete this._d[k]; },
};
global.navigator = { clipboard: null };
global.location = { hash: "", pathname: "/", search: "" };
global.history = { replaceState: () => {} };
global.requestAnimationFrame = (f) => f();
global.setTimeout = () => 0;
global.Blob = class { constructor(parts) { exported = parts.join(""); } };
global.URL = { createObjectURL: () => "blob:x", revokeObjectURL: () => {} };

const boot = () => new Function("DATA", "window", ALL[ALL.length - 1] + "\n;return window.__agentmap;")(DATA, global.window);

const fails = [];
const ok = (n, c, e) => { if (!c) fails.push(n + (e ? " <" + e + ">" : "")); };

// ---------- 1. 打开概念，写笔记 ----------
let APP = boot();
APP.openNode("mcp");

// 展示位置：初始居中，可切换侧边，偏好跨刷新；切换不重建详情正文。
ok("详情默认居中", els.drawer.classList.contains("center-mode"));
ok("标题区有两种展示位置", els.dwtop.innerHTML.includes("dwModeCenter") && els.dwtop.innerHTML.includes("dwModeSide"));
const detailBefore = els.dwbody.innerHTML;
els.dwModeSide.onclick();
ok("切成侧边栏", !els.drawer.classList.contains("center-mode"));
ok("位置选择已保存", global.localStorage.getItem("agentmap.detailMode.v1") === "side");
ok("切换位置不重建正文", els.dwbody.innerHTML === detailBefore);
APP = boot();
APP.openNode("mcp");
ok("刷新沿用侧边偏好", !els.drawer.classList.contains("center-mode"));
APP.setDetailMode("center");
ok("能切回居中", els.drawer.classList.contains("center-mode") && global.localStorage.getItem("agentmap.detailMode.v1") === "center");

// 笔记现在是独立的右侧栏，不在正文里；标题区有「笔记」入口（带铅笔图标）
ok("标题区有笔记入口", els.dwtop.innerHTML.includes("dwNoteToggle"), els.dwtop.innerHTML.slice(-160));
ok("笔记入口带铅笔图标", els.dwtop.innerHTML.includes("✎"), "按钮应含 ✎ 图标");
ok("正文不再内嵌笔记编辑器", !els.dwbody.innerHTML.includes("dnote"), "dwbody 不应含 dnote");

const tb = els.dnote;
const NOTE_TEXT = "MCP 是协议层，不是 RPC；关键在 Host 管理多个 client。";
ok("textarea 已绑定 input", typeof tb.oninput === "function");
ok("打开概念时笔记栏为当前概念内容", tb.value === "", String(tb.value));
tb.value = NOTE_TEXT;
tb.oninput();

const memoRaw = JSON.parse(global.localStorage.getItem("agentmap.notes.v1"));
ok("笔记写入 localStorage", memoRaw && memoRaw.notes && memoRaw.notes.mcp === NOTE_TEXT,
   JSON.stringify(memoRaw && memoRaw.notes));
ok("笔记未污染 status 键", !global.localStorage.getItem("agentmap.status.v1"));

// 笔记入口的小圆点随内容点亮
ok("有笔记时标题入口点亮", els.dwNoteToggle.classList.contains("has"));

// ---------- 2. 待深入标记 ----------
const fb = els.dflag;
ok("待深入按钮已绑定", typeof fb.onclick === "function");
fb.onclick();
const memo2 = JSON.parse(global.localStorage.getItem("agentmap.notes.v1"));
ok("待深入写入 localStorage", memo2.flags && memo2.flags.mcp === true, JSON.stringify(memo2.flags));
fb.onclick();
const memo3 = JSON.parse(global.localStorage.getItem("agentmap.notes.v1"));
ok("待深入可取消", !memo3.flags.mcp, JSON.stringify(memo3.flags));

// 重新标上，供刷新测试
els.dflag.onclick();

// ---------- 2b. 笔记栏开合：只切类名，不重建正文 ----------
ok("初始笔记栏关闭", !els.notepanel.classList.contains("on") && !els.drawer.classList.contains("note-open"));
const bodyBefore = els.dwbody.innerHTML;
els.dwNoteToggle.onclick();
ok("点入口后笔记栏打开", els.notepanel.classList.contains("on") && els.drawer.classList.contains("note-open"));
ok("打开笔记栏不重建正文", els.dwbody.innerHTML === bodyBefore);
ok("中央弹窗可同时打开笔记", els.drawer.classList.contains("center-mode") && els.drawer.classList.contains("note-open"));
els.dwModeSide.onclick();
ok("开着笔记切模式不会关闭笔记", els.notepanel.classList.contains("on") && els.drawer.classList.contains("note-open"));
els.dwModeCenter.onclick();
els.dwNoteToggle.onclick();
ok("再点一次笔记栏关闭", !els.notepanel.classList.contains("on") && !els.drawer.classList.contains("note-open"));

// ---------- 2c. 笔记位置偏好：紧贴知识点（默认）/ 屏幕右侧 ----------
ok("默认紧贴模式生效", els.drawer.classList.contains("tight") && els.notepanel.classList.contains("tight"));
ok("紧贴按钮默认选中", els.npPosClose.classList.contains("on") && !els.npPosAside.classList.contains("on"));
const noteBeforeSwitch = els.dnote.value;
els.npPosAside.onclick();
ok("切到屏幕右侧后紧贴解除", !els.drawer.classList.contains("tight") && !els.notepanel.classList.contains("tight"));
ok("切换位置不清空笔记", els.dnote.value === noteBeforeSwitch, String(els.dnote.value));
ok("右侧按钮选中", els.npPosAside.classList.contains("on") && !els.npPosClose.classList.contains("on"));
const posRaw = global.localStorage.getItem("agentmap.notePos.v1");
ok("位置偏好写入 localStorage", posRaw === "aside", String(posRaw));
els.npPosClose.onclick();
ok("切回紧贴后双栏恢复", els.drawer.classList.contains("tight") && els.notepanel.classList.contains("tight"));

// 侧边详情下不套用紧贴排版（保留原有双侧行为）
els.dwModeSide.onclick();
ok("侧边详情下紧贴排版不生效", !els.drawer.classList.contains("tight") && !els.notepanel.classList.contains("tight"));
els.dwModeCenter.onclick();
ok("回到居中详情后紧贴排版恢复", els.drawer.classList.contains("tight") && els.notepanel.classList.contains("tight"));
els.npPosAside.onclick();

// ---------- 3. 模拟刷新：新实例必须从 localStorage 恢复 ----------
APP = boot();
ok("刷新后笔记仍在", APP.MEMO.notes.mcp === NOTE_TEXT, JSON.stringify(APP.MEMO.notes));
ok("刷新后待深入仍在", APP.MEMO.flags.mcp === true, JSON.stringify(APP.MEMO.flags));
ok("刷新后笔记位置偏好保留（上次选了屏幕右侧）", !els.drawer.classList.contains("tight"), "aside 应保持");
els.npPosClose.onclick();
ok("切回紧贴后刷新仍记得", els.drawer.classList.contains("tight"));

// 重开后笔记栏应回填正文
APP.openNode("mcp");
ok("重开概念后笔记栏回填正文", els.dnote.value === NOTE_TEXT, String(els.dnote.value).slice(0, 40));

// ---------- 3b. 切换概念：笔记栏跟随当前概念 ----------
APP.openNode("rag");
ok("切换概念后笔记栏换为 rag 的内容", els.dnote.value === "", String(els.dnote.value));
APP.openNode("mcp");
ok("切回 mcp 后笔记恢复", els.dnote.value === NOTE_TEXT, String(els.dnote.value).slice(0, 40));
// 关闭抽屉时笔记栏也关闭
APP.openNode("rag");
els.dwNoteToggle.onclick();
APP.closeDrawer && APP.closeDrawer();
ok("关闭抽屉时笔记栏一并关闭", !els.notepanel.classList.contains("on"));

// ---------- 4. 搜索无结果 → 待整理清单 ----------
els.q.oninput({ target: { value: "量子编排协议" } });
ok("无结果时显示提示条", els.nores.classList.contains("on"));
ok("提示条回显关键词", els.noq.textContent === "量子编排协议", els.noq.textContent);
els.pendAdd.onclick();
ok("关键词进入待整理", APP.MEMO.pending.indexOf("量子编排协议") > -1, JSON.stringify(APP.MEMO.pending));

// 有结果时不显示
els.q.oninput({ target: { value: "MCP" } });
ok("有结果时隐藏提示条", !els.nores.classList.contains("on"));

// 重复添加不产生重复项
els.q.oninput({ target: { value: "量子编排协议" } });
els.pendAdd.onclick();
ok("待整理去重", APP.MEMO.pending.filter((x) => x === "量子编排协议").length === 1, JSON.stringify(APP.MEMO.pending));

// ---------- 5. 导出包含新数据 ----------
APP.downloadProgress();
let payload = null;
try { payload = JSON.parse(exported); } catch (e) {}
ok("导出可解析", !!payload);
ok("导出 version=2", payload && payload.version === 2, String(payload && payload.version));
ok("导出含 notes", payload && payload.notes && payload.notes.mcp === NOTE_TEXT);
ok("导出含 flags", payload && payload.flags && payload.flags.mcp === true);
ok("导出含 pending", payload && Array.isArray(payload.pending) && payload.pending.indexOf("量子编排协议") > -1);

// ---------- 6. 导入 v2 完整包 ----------
const fresh = boot();
fresh.applyImport({
  tool: "agent-knowledge-map", version: 2, total: DATA.nodes.length,
  status: { rag: "精通" },
  notes: { rag: "导入的笔记" },
  flags: { rag: true },
  pending: ["旧词B"],
});
ok("v2 导入 status", fresh.STATUS.rag === "精通", JSON.stringify(fresh.STATUS));
ok("v2 导入 notes", fresh.MEMO.notes.rag === "导入的笔记", JSON.stringify(fresh.MEMO.notes));
ok("v2 导入 flags", fresh.MEMO.flags.rag === true, JSON.stringify(fresh.MEMO.flags));
ok("v2 导入 pending", fresh.MEMO.pending.indexOf("旧词B") > -1, JSON.stringify(fresh.MEMO.pending));

// ---------- 7. 旧版文件（只有 status）仍可导入 ----------
const legacy = boot();
const notesBefore = Object.keys(legacy.MEMO.notes).length;
legacy.applyImport({ tool: "agent-knowledge-map", version: 1, total: DATA.nodes.length, status: { lats: "待补" } });
ok("v1 导入 status", legacy.STATUS.lats === "待补", JSON.stringify(legacy.STATUS));
ok("v1 导入不新增笔记", Object.keys(legacy.MEMO.notes).length === notesBefore,
   notesBefore + " -> " + Object.keys(legacy.MEMO.notes).length);

// ---------- 8. 裸 status 对象（最早的手工文件）仍可导入 ----------
const bare = boot();
bare.applyImport({ "agent-loop": "知道", "mcp": "会用" });
ok("裸 status 兼容", bare.STATUS.mcp === "会用" && bare.STATUS["agent-loop"] === "知道", JSON.stringify(bare.STATUS));

// ---------- 9. 无效 id 不应写入 ----------
const guard = boot();
guard.applyImport({ status: { __nope: "精通" }, notes: { __nope: "x" }, flags: { __nope: true } });
ok("无效 id 被丢弃", !guard.STATUS.__nope && !guard.MEMO.notes.__nope && !guard.MEMO.flags.__nope);

if (fails.length) {
  console.error("FAILURES:\n - " + fails.join("\n - "));
  process.exit(1);
}
console.log("v1.1 notes/collection checks passed");
console.log("  keys:", Object.keys(payload).join(", "));

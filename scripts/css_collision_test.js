// CSS collision guard: a badge modifier class must never share a name with a
// standalone class selector, otherwise that rule silently overrides badge padding,
// border-radius, background, etc. (this made 「可选」 20px taller than its siblings).
const fs = require("fs");
const path = require("path");

const html = fs.readFileSync(process.argv[2] || path.join(__dirname, "..", "Agent知识地图.html"), "utf8");
const css = html.slice(html.indexOf("<style>"), html.indexOf("</style>"));

const fails = [];
const ok = (n, c, e) => { if (!c) fails.push(n + (e ? " <" + e + ">" : "")); };

// all `.badge.<modifier>` rules
const mods = [...new Set([...css.matchAll(/\.badge\.([\w-]+)\{/g)].map((m) => m[1]))];
ok("找到徽章修饰类", mods.length >= 6, mods.join(","));

// every standalone `.<name>{` / `.<name>,` selector in the sheet
const standalone = new Set();
for (const m of css.matchAll(/(^|\})\s*\.([\w-]+)\s*(?=[,{])/g)) standalone.add(m[2]);

const clashes = mods.filter((m) => standalone.has(m));
ok("徽章修饰类无同名独立选择器", clashes.length === 0, clashes.join(","));

// every modifier must be namespaced
const bad = mods.filter((m) => !m.startsWith("b-"));
ok("徽章修饰类统一 b- 前缀", bad.length === 0, bad.join(","));

// the locator's option-card class must stay distinct
ok("落位器 .opt 卡片与徽章不冲突", !mods.includes("opt"), mods.join(","));

console.log("badge modifiers:", mods.join(", "));
if (fails.length) {
  console.error("\nFAILURES:\n - " + fails.join("\n - "));
  process.exit(1);
}
console.log("no badge class collisions");

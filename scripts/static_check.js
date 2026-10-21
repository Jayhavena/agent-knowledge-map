// Static consistency check: every getElementById in JS must exist as an id (or be created later), and CSS classes used by JS must be defined.
const fs = require("fs");
const html = fs.readFileSync("Agent知识地图.html", "utf8");

const declaredIds = new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]));
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
const js = scripts[scripts.length - 1];

const usedIds = new Set([...js.matchAll(/getElementById\("([^"]+)"\)/g)].map((m) => m[1]));
const dynamic = new Set(["dwclose", "dwtop", "dwbody", "stbtns", "prevn", "nextn", "locname", "n1", "b2", "n2",
  "b3", "n3", "b4", "n4", "b5", "n5", "lineage", "snip", "copy", "again", "copytag", "helperules", "matrix",
  "outline", "locbody", "steps", "count", "gleg", "gtip", "gcanvas"]);

const missing = [...usedIds].filter((id) => !declaredIds.has(id) && !dynamic.has(id));
console.log("ids in HTML:", declaredIds.size, "| referenced in JS:", usedIds.size);
console.log("missing ids (not declared, not dynamic):", missing.length ? missing : "none");

// css class tokens defined
const css = (html.match(/<style>([\s\S]*?)<\/style>/) || [, ""])[1];
const definedClasses = new Set([...css.matchAll(/\.([a-zA-Z][\w-]*)/g)].map((m) => m[1]));
const usedClasses = new Set();
for (const m of js.matchAll(/class="([^"'+]+)"/g)) {
  m[1].split(/\s+/).forEach((c) => c && usedClasses.add(c));
}
const undef = [...usedClasses].filter((c) => !definedClasses.has(c));
console.log("classes used by JS but not in CSS:", undef.length ? undef : "none");

// var() defined?
const definedVars = new Set([...css.matchAll(/(--[\w-]+)\s*:/g)].map((m) => m[1]));
const usedVars = new Set([...html.matchAll(/var\((--[\w-]+)\)/g)].map((m) => m[1]));
const undefVars = [...usedVars].filter((v) => !definedVars.has(v));
console.log("undefined CSS vars:", undefVars.length ? undefVars : "none");

// balanced tags rough check
for (const tag of ["div", "section", "button", "span"]) {
  const open = (html.match(new RegExp("<" + tag + "[\\s>]", "g")) || []).length;
  const close = (html.match(new RegExp("</" + tag + ">", "g")) || []).length;
  if (open !== close) console.log(`tag imbalance <${tag}>: ${open} open vs ${close} close`);
}
console.log("done");

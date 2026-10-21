# Agent 知识地图

> 一套「层 × 环 × 面」的坐标系，用来把任何新出现的 Agent 概念，在 30 秒内定位到「它属于哪个已知位置、它是谁的下一代」。

**在线浏览**：https://jayhavena.github.io/agent-knowledge-map/

---

## 这是什么

大多数人觉得「AI 领域什么都是新的」，并不是知识不够，而是缺少坐标系。有坐标系时，绝大多数新名词都能被还原为「某个已知概念在某个格子里的一次变体」。

所以这个仓库的第一性产物不是一份概念清单，而是**一套定位规则**：

- **层**（它作用在哪一层对象上）：L0 模型 → L1 上下文 → L2 记忆 → L3 工具 → L4 控制 → L5 编排 → L6 系统
- **环**（它在一次运行的第几步起作用）：P1 输入 → P2 取景 → P3 规划 → P4 行动 → P5 观察 → P6 反思 → P7 交付
- **面**（它回答哪一类工程问题）：定义 / 机制 / 质量 / 成本 / 时延 / 安全 / 运维

任何概念都必须同时回答这三个问题才能落位。落位之后再去同格子里找邻居——邻居往往就是它的前身。

## 有哪些内容

| 视图 | 说明 |
|---|---|
| **矩阵** | 主视图。横轴环、纵轴层，一眼看出密度分布；L6 是底部虚线支架带 |
| **图谱** | 同样的坐标，加上概念间的继承与依赖连线，可看出该先吃透的枢纽 |
| **大纲** | 按层 → 环展开的完整清单，适合核对覆盖率 |
| **深读** | 把单个概念往下挖一层：内部结构、关键决策、失败模式、上手路径 |
| **落位器** | 交互式走完五问，给出该格子的邻居清单 + 可直接粘进 Obsidian 的笔记骨架 |

当前规模：**134 个概念**、**734 条双向关系**、**24 个已占格子**、**2 张深读卡**（评测、记忆）。

支持深浅两套主题（跟随系统 / 浅色 / 深色），所有颜色经 WCAG AA 对比度校验。

## 怎么用

**在线看**：直接打开 https://jayhavena.github.io/agent-knowledge-map/ 。按 `/` 搜索，按 `t` 切换主题。

**本地看**：下载 `Agent知识地图.html`，双击即可，无需联网、无需服务器。

**在 Obsidian 里用**：把 `Obsidian-Agent知识库/` 作为 vault 打开，会得到 134 篇双链笔记 + 导航页 + 深读笔记。

**分享某个概念**：地址栏会随导航更新，例如 `#node=memory-consolidation`，复制即直达。

## 更新与发布

改完数据后一条命令发布：

```bash
python scripts/publish.py
```

它做四件事：重新生成 → 跑全套校验（任何一项失败就中止）→ 组装站点 → 推送到 `gh-pages` 分支。GitHub Pages 监听该分支，推送后一两分钟内自动生效。

```bash
python scripts/publish.py --dry-run   # 只构建和校验，生成 _site/ 供本地预览
python scripts/publish.py --skip-checks
```

**为什么用分支而不是 Actions 部署**：推送分支只需要 `repo` 权限，而提交 workflow 文件需要额外的 `workflow` 权限，后者很多令牌没有。分支方案对任何能 push 的人都成立，也更少依赖。

`.github/workflows/` 的 CI 是可选的，装法见 `ci-templates/README.md`。不装也能正常发布——`publish.py` 内部跑的是同一套校验。

## 发现错误或有建议

三种方式，按成本从低到高：

1. **提 Issue** — 概念定位错了、解释不准、有更好的说法，都欢迎。请说明是哪个概念（或哪一格）。
2. **提 PR** — 改 `data/*.json` 即可，不要手改 HTML（它由脚本生成，CI 会检查一致性）。
3. **讨论** — 如果你认为某个坐标轴的划分本身有问题，那比单个概念的修正更值得聊。

### 提 PR 的正确姿势

```bash
# 1. 只改数据，别改生成物
vim data/nodes-context.json      # 加一条概念，或修一条现有条目

# 2. 重新生成 HTML 与 Obsidian 库
python scripts/build.py

# 3. 跑校验（CI 也会跑同样的东西）
python scripts/validate.py
python scripts/content_qa.py
python scripts/contrast_qa.py
node scripts/smoke.js Agent知识地图.html

# 4. 提交（数据 + 生成物一起）
git add -A && git commit -m "add: 概念 X" && git push
```

只改数据没重新生成，是这类项目最常见的问题——所以 `publish.py` 会先重跑构建再比对，产物对不上就不发布。

### 新增概念需要哪些字段

照抄 `data/nodes-*.json` 里现有条目的结构。其中两项如果空着，就等于没落位：

- `newIn` — 它新在哪。写不出来，说明它其实不新。
- `from` — 它是谁的下一代。确实没有前身的极少，写成「旧想法 + 新约束」。

其余字段（`oneLine` / `problem` / `trap` / `tier` / `maturity` / `facets`）见现有条目。

## 仓库结构

```
data/                 唯一数据源，改这里
  meta.json             三条坐标轴的定义与落位规则
  nodes-*.json          134 个概念节点
  deeps-*.json          深读卡
  ancestors.json        图外的「旧概念」祖先
scripts/              构建与校验
  build.py              数据 → HTML + Obsidian 库
  template.html         页面模板（含样式与交互）
  其余 *.py / *.js       各类校验，CI 与本地共用
Agent知识地图.html      生成物，勿手改
Obsidian-Agent知识库/   生成物，勿手改
.github/workflows/    CI 与 Pages 部署
```

## 已知取舍

- **L6 不在环上**：评测、观测、发布环绕全程，硬塞进 P1–P7 会造出「一格 30 个概念」的假象，所以单列成支架带。
- **格子空着是有信息的**：42 个主格只占了 24 个，空位要么是真没有独立概念，要么是还没被命名。
- **「争议」标签刻意保留**：多 Agent、角色设计、长上下文有实证反例，没被打成主流。
- **不追求穷尽**：目标是一套能持续往里放的坐标，不是一份一次性清单。

## License

内容采用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 许可，代码采用 MIT。

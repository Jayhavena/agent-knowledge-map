# CI 工作流（可选，需手动安装一次）

`ci.yml` 放在这里而不是 `.github/workflows/`，是因为推送带 workflow 的文件需要额外的 `workflow` 权限，普通仓库令牌通常没有。

**不装也能用**：`scripts/publish.py` 会在发布前跑同一套校验，坏数据同样发布不出去。区别只是——装了 CI，别人提的 PR 也会被自动检查。

## 安装（30 秒）

1. 打开 https://github.com/Jayhavena/agent-knowledge-map
2. **Add file → Create new file**
3. 文件名填 `.github/workflows/ci.yml`
4. 粘贴 `ci.yml` 的内容，提交

装好之后删掉本文件即可。

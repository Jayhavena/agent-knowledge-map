#!/usr/bin/env python3
"""Build the site and publish it to the `gh-pages` branch.

Why a branch instead of GitHub Actions: pushing to a branch only needs the `repo`
scope, while committing a workflow file needs the extra `workflow` scope. That
makes `publish.py` the zero-setup path — anyone who can push to the repo can ship.

Usage:
    python scripts/publish.py            # build, verify, publish
    python scripts/publish.py --dry-run  # build and verify, stop before pushing
    python scripts/publish.py --skip-checks

Environment:
    GH_TOKEN / GITHUB_TOKEN  if set, used to authenticate the push
"""
import base64
import io
import os
import shutil
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
SITE = os.path.join(ROOT, "_site")
WORK = os.path.join(ROOT, "_pages")
BRANCH = "gh-pages"

CHECKS = [
    ["python", os.path.join(BASE, "validate.py")],
    ["python", os.path.join(BASE, "content_qa.py")],
    ["python", os.path.join(BASE, "contrast_qa.py")],
    ["python", os.path.join(BASE, "legend_qa.py")],
    ["node", os.path.join(BASE, "smoke.js"), os.path.join(ROOT, "Agent知识地图.html")],
    ["node", os.path.join(BASE, "deeplink_test.js")],
    ["node", os.path.join(BASE, "badge_test.js")],
    ["node", os.path.join(BASE, "css_collision_test.js")],
]


def run(cmd, cwd=None, check=True, quiet=False):
    r = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        print("命令失败: " + " ".join(cmd))
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])
        sys.exit(1)
    if not quiet and r.stdout.strip():
        print(r.stdout.strip()[-1200:])
    return r


def git(*args, cwd=None, check=True, quiet=True):
    cmd = ["git"] + list(args)
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        b64 = base64.b64encode(("x-access-token:" + token).encode()).decode()
        cmd = ["git", "-c", "http.extraheader=AUTHORIZATION: basic " + b64] + list(args)
    return run(cmd, cwd=cwd, check=check, quiet=quiet)


def main():
    dry = "--dry-run" in sys.argv
    skip = "--skip-checks" in sys.argv

    print("== 1/4 构建 ==")
    run(["python", os.path.join(BASE, "build.py")])

    if not skip:
        print("\n== 2/4 校验（坏数据不发布）==")
        for c in CHECKS:
            r = run(c, check=False, quiet=True)
            name = os.path.basename(c[1])
            print(("  ok   " if r.returncode == 0 else "  FAIL ") + name)
            if r.returncode != 0:
                print(r.stdout[-2000:])
                print(r.stderr[-2000:])
                print("\n校验未通过，已中止发布。")
                sys.exit(1)

    print("\n== 3/4 组装站点 ==")
    if os.path.isdir(SITE):
        shutil.rmtree(SITE)
    os.makedirs(SITE)
    shutil.copy(os.path.join(ROOT, "Agent知识地图.html"), os.path.join(SITE, "index.html"))
    shutil.copytree(os.path.join(ROOT, "Obsidian-Agent知识库"), os.path.join(SITE, "Obsidian-Agent知识库"))
    # .nojekyll: stop GitHub Pages from running Jekyll over Chinese filenames.
    io.open(os.path.join(SITE, ".nojekyll"), "w", encoding="utf-8").close()
    if os.path.exists(os.path.join(ROOT, "README.md")):
        shutil.copy(os.path.join(ROOT, "README.md"), os.path.join(SITE, "README.md"))
    print("  index.html + Obsidian-Agent知识库/ + .nojekyll")

    if dry:
        print("\n--dry-run：已停在推送之前。站点在 " + SITE)
        return

    print("\n== 4/4 发布到 " + BRANCH + " ==")
    if os.path.isdir(WORK):
        git("worktree", "remove", "--force", WORK, check=False)
        shutil.rmtree(WORK, ignore_errors=True)

    has_branch = git("rev-parse", "--verify", "--quiet", BRANCH, check=False).returncode == 0
    if has_branch:
        git("worktree", "add", "--force", WORK, BRANCH)
    else:
        print("  " + BRANCH + " 不存在，新建孤儿分支")
        git("worktree", "add", "--force", "--orphan", "-b", BRANCH, WORK)

    # 清空上一次的产物（保留 .git）
    for name in os.listdir(WORK):
        if name == ".git":
            continue
        p = os.path.join(WORK, name)
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)

    for name in os.listdir(SITE):
        src = os.path.join(SITE, name)
        dst = os.path.join(WORK, name)
        shutil.copytree(src, dst) if os.path.isdir(src) else shutil.copy(src, dst)

    git("add", "-A", cwd=WORK)
    status = git("status", "--porcelain", cwd=WORK)
    if not status.stdout.strip():
        print("  站点内容无变化，跳过提交")
    else:
        stamp = run(["git", "log", "-1", "--format=%h %s"], cwd=ROOT).stdout.strip()
        git("-c", "user.name=" + (os.environ.get("GIT_AUTHOR_NAME") or "agent-map-bot"),
            "-c", "user.email=" + (os.environ.get("GIT_AUTHOR_EMAIL") or "bot@users.noreply.github.com"),
            "commit", "-q", "-m", "deploy: " + stamp, cwd=WORK)
        git("push", "origin", BRANCH, cwd=WORK)
        print("  已推送至 origin/" + BRANCH)

    git("worktree", "remove", "--force", WORK, check=False)
    shutil.rmtree(WORK, ignore_errors=True)
    print("\n完成。若这是第一次发布，请在仓库 Settings → Pages 里把 Source 设为 " + BRANCH + " 分支的 / 根目录。")


if __name__ == "__main__":
    main()

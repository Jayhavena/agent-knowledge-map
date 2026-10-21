#!/usr/bin/env python3
"""Check the local build is reproducible: running build.py must not change tracked output."""
import subprocess, sys, os

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)

def git(*args):
    return subprocess.run(["git"] + list(args), cwd=ROOT, capture_output=True, text=True)

if git("rev-parse", "--is-inside-work-tree").returncode != 0:
    print("skip: not a git repository")
    sys.exit(0)

before = git("status", "--porcelain").stdout

r = subprocess.run([sys.executable, os.path.join(BASE, "build.py")], cwd=BASE, capture_output=True, text=True)
if r.returncode != 0:
    print("build failed:\n" + r.stdout + r.stderr)
    sys.exit(1)

after = git("status", "--porcelain").stdout
if before != after:
    print("build is NOT reproducible — these paths changed:")
    b = set(before.splitlines())
    a = set(after.splitlines())
    for line in sorted(a - b):
        print("  " + line)
    sys.exit(1)

print("build reproducible: no pending changes")

#!/usr/bin/env python3
"""Build a versioned Cowork/Claude-Code plugin bundle (.plugin) with the MCP
server + bundled skill + generation library.

Usage:
    python scripts/build_plugin.py                # build current VERSION
    python scripts/build_plugin.py --bump patch   # bump VERSION then build
    python scripts/build_plugin.py --set 1.2.0    # set VERSION then build

Artifacts go to build/heroquarium-artgen-v<version>.plugin (a zip), plus a
`-latest.plugin` copy and a BUILDS.md log. `.plugin` files render with an
install button in the Cowork app.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
PLUGIN_NAME = "heroquarium-artgen"

# (source path relative to repo root) -> (path inside the plugin bundle)
INCLUDE = [
    ("plugin/.claude-plugin/plugin.json", ".claude-plugin/plugin.json"),
    ("plugin/.mcp.json", ".mcp.json"),
    ("plugin/requirements.txt", "requirements.txt"),
    ("plugin/README.md", "README.md"),
    ("mcp/server.py", "mcp/server.py"),
    ("mcp/README.md", "mcp/README.md"),
    ("skills/heroquarium-artgen/SKILL.md", "skills/heroquarium-artgen/SKILL.md"),
    ("palette.json", "palette.json"),
    ("docs/iso_integration.md", "docs/iso_integration.md"),
]
INCLUDE_DIRS = [("artgen", "artgen")]          # whole package (minus pycache)


def read_version() -> str:
    return open(os.path.join(ROOT, "VERSION")).read().strip()


def write_version(v: str):
    open(os.path.join(ROOT, "VERSION"), "w").write(v + "\n")


def bump(v: str, part: str) -> str:
    major, minor, patch = (int(x) for x in v.split("."))
    if part == "major":
        major, minor, patch = major + 1, 0, 0
    elif part == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    return f"{major}.{minor}.{patch}"


def _iter_pkg(src_dir):
    for base, _dirs, files in os.walk(src_dir):
        if "__pycache__" in base:
            continue
        for f in files:
            if f.endswith((".pyc", ".pyo")):
                continue
            yield os.path.join(base, f)


def build(version: str) -> str:
    os.makedirs(BUILD, exist_ok=True)
    # stamp plugin.json version to match VERSION
    manifest_path = os.path.join(ROOT, "plugin/.claude-plugin/plugin.json")
    manifest = json.load(open(manifest_path))
    manifest["version"] = version
    json.dump(manifest, open(manifest_path, "w"), indent=2)

    out = os.path.join(BUILD, f"{PLUGIN_NAME}-v{version}.plugin")
    files_written = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for src, arc in INCLUDE:
            p = os.path.join(ROOT, src)
            if os.path.exists(p):
                z.write(p, arc)
                files_written += 1
        for src_dir, arc_dir in INCLUDE_DIRS:
            for p in _iter_pkg(os.path.join(ROOT, src_dir)):
                arc = os.path.join(arc_dir, os.path.relpath(p, os.path.join(ROOT, src_dir)))
                z.write(p, arc)
                files_written += 1
    shutil.copyfile(out, os.path.join(BUILD, f"{PLUGIN_NAME}-latest.plugin"))

    log = os.path.join(BUILD, "BUILDS.md")
    if not os.path.exists(log):
        open(log, "w").write("# Plugin builds\n\n| version | date (UTC) | files | artifact |\n|---|---|---|---|\n")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    with open(log, "a") as f:
        f.write(f"| {version} | {stamp} | {files_written} | {os.path.basename(out)} |\n")
    return out, files_written


def main(argv=None):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--bump", choices=["major", "minor", "patch"])
    g.add_argument("--set", dest="set_v")
    args = ap.parse_args(argv)

    v = read_version()
    if args.set_v:
        v = args.set_v
        write_version(v)
    elif args.bump:
        v = bump(v, args.bump)
        write_version(v)

    out, n = build(v)
    print(f"built {os.path.relpath(out, ROOT)} ({n} files, v{v})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

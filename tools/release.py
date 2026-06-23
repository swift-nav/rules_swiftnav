#!/usr/bin/env python3
# Copyright (C) 2022 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.
"""Bump the rules_swiftnav module version and open a release PR.

Stdlib-only so CI can run it with plain `python3` (no Bazel/deps required).
"""

import argparse
import os
import re
import subprocess
import sys

_VERSION_RE = re.compile(r'(?m)^(\s*version\s*=\s*")(\d+\.\d+\.\d+)(")')
_PARTS = ("major", "minor", "patch")

REPO = "swift-nav/rules_swiftnav"
EXAMPLE_LOCK_DIR = "examples/small_world"


def parse_version(module_text):
    """Return the X.Y.Z version string from a MODULE.bazel module() block."""
    m = _VERSION_RE.search(module_text)
    if not m:
        raise ValueError("no `version = \"X.Y.Z\"` found in MODULE.bazel")
    return m.group(2)


def bump_version(version, part):
    """Return version with the given semver part incremented."""
    if part not in _PARTS:
        raise ValueError(f"part must be one of {_PARTS}, got {part!r}")
    major, minor, patch = (int(x) for x in version.split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def set_version(module_text, new_version):
    """Return module_text with the module() version replaced."""
    new_text, n = _VERSION_RE.subn(rf"\g<1>{new_version}\g<3>", module_text, count=1)
    if n != 1:
        raise ValueError("could not substitute version in MODULE.bazel")
    return new_text


def read_current_version(path="MODULE.bazel", use_stdin=False):
    """Read MODULE.bazel (from path or stdin) and return its version."""
    text = sys.stdin.read() if use_stdin else open(path, encoding="utf-8").read()
    return parse_version(text)


def _run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)


def _git_out(cmd):
    return subprocess.run(["git", *cmd], check=True, text=True,
                          capture_output=True).stdout.strip()


def main(argv=None):
    p = argparse.ArgumentParser(description="Bump version and open a release PR.")
    p.add_argument("part", nargs="?", choices=_PARTS, help="semver part to bump")
    p.add_argument("--current", action="store_true",
                   help="print the current version and exit (used by CI)")
    p.add_argument("--file", default="MODULE.bazel")
    p.add_argument("--stdin", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    # Run from the workspace root, not the bazel execroot.
    workspace = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace:
        os.chdir(workspace)

    if args.current:
        print(read_current_version(None if args.stdin else args.file, args.stdin))
        return 0

    if not args.part:
        p.error("a bump part (major/minor/patch) is required")

    if _git_out(["status", "--porcelain"]):
        raise SystemExit("working tree is dirty; commit or stash first")

    text = open(args.file, encoding="utf-8").read()
    old = parse_version(text)
    new = bump_version(old, args.part)
    branch = f"release/{new}"
    tag = f"v{new}"

    existing_tags = _git_out(["tag", "--list", tag])
    if existing_tags:
        raise SystemExit(f"tag {tag} already exists")

    if args.dry_run:
        print(f"[dry-run] {old} -> {new} (branch {branch}, tag {tag})")
        return 0

    try:
        with open(args.file, "w", encoding="utf-8") as f:
            f.write(set_version(text, new))

        # Keep the committed example lockfile in sync with the bumped version.
        _run(["bazel", "mod", "deps", "--lockfile_mode=update"], cwd=EXAMPLE_LOCK_DIR)
        # Normalize formatting.
        _run(["bazel", "run", "//tools/buildifier:buildifier"])

        _run(["git", "checkout", "-b", branch])
        _run(["git", "add", "MODULE.bazel", f"{EXAMPLE_LOCK_DIR}/MODULE.bazel.lock"])
        _run(["git", "commit", "-m", f"Bump version to {new}"])
        _run(["git", "push", "-u", "origin", branch])
        _run(["gh", "pr", "create", "--repo", REPO, "--fill",
              "--title", f"Bump version to {new}"])
        print(f"Opened release PR for {new}.")
        return 0
    except Exception:
        print(
            f"release failed mid-way. To reset:\n"
            f"  git checkout main && git branch -D {branch} 2>/dev/null; "
            f"git checkout -- {args.file} {EXAMPLE_LOCK_DIR}/MODULE.bazel.lock",
            file=sys.stderr,
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())

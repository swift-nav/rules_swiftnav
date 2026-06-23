#!/usr/bin/env python3
# Copyright (C) 2022-2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.
"""Bump the rules_swiftnav module version and open a release PR.

Stdlib-only so CI can run it with plain `python3` (no Bazel/deps required).
"""

import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys

_VERSION_RE = re.compile(r'(?m)^(\s*version\s*=\s*")(\d+\.\d+\.\d+)(")')
_PARTS = ("major", "minor", "patch")

# Matches "Copyright (C) 2022" or "Copyright (C) 2022-2025" in a Swift
# Navigation header, capturing the start year and (optional) end year.
_COPYRIGHT_RE = re.compile(
    r"(Copyright \(C\) )(\d{4})(?:-(\d{4}))?( Swift Navigation)"
)

REPO = "swift-nav/rules_swiftnav"
EXAMPLE_LOCK_DIR = "examples/small_world"

_BAZELISK_PIN_RE = re.compile(r'(?m)^\s*USE_BAZEL_VERSION\s*=\s*(\S+)')
_BAZEL_VERSION_RE = re.compile(r'\bbazel\s+(\d+\.\d+\.\d+)')
_CONCRETE_VERSION_RE = re.compile(r'\d+\.\d+\.\d+')


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


def set_copyright_years(text, year):
    """Return text with Swift Navigation copyright headers extended to year.

    The first-publication year is preserved and the end of the range is set to
    `year`, producing "(C) <start>-<year>". A header already ending at `year`
    (single year or range) is left unchanged, so the transform is idempotent.
    """
    def repl(m):
        start = int(m.group(2))
        if start >= year:
            return m.group(0)
        return f"{m.group(1)}{start}-{year}{m.group(4)}"

    return _COPYRIGHT_RE.sub(repl, text)


def list_tracked_files():
    """Return the repo's git-tracked file paths (relative to the workspace)."""
    return _git_out(["ls-files"]).splitlines()


def bump_copyrights(year, dry_run=False):
    """Extend Swift Navigation copyright headers in tracked files to `year`.

    Returns the list of files that changed (or would change, when dry_run).
    Binary or non-UTF-8 files are skipped.
    """
    changed = []
    for path in list_tracked_files():
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        new_text = set_copyright_years(text, year)
        if new_text != text:
            changed.append(path)
            if not dry_run:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_text)
    return changed


def parse_bazelisk_pin(text):
    """Return the USE_BAZEL_VERSION pinned in a .bazeliskrc, or None."""
    m = _BAZELISK_PIN_RE.search(text)
    return m.group(1) if m else None


def parse_bazel_version(output):
    """Return the X.Y.Z version from `bazel --version` output, or None."""
    m = _BAZEL_VERSION_RE.search(output)
    return m.group(1) if m else None


def check_pinned_bazel(pin, version_output):
    """Fail unless the running Bazel matches the .bazeliskrc `pin`.

    The example lockfile's bzlTransitiveDigest is Bazel-version-specific, and CI
    builds the example with the version bazelisk resolves from .bazeliskrc. A
    release cut with a `bazel` that bypassed bazelisk (or overrode
    USE_BAZEL_VERSION) would regenerate the lockfile with a different version,
    desyncing the digest from CI. No-op when `pin` is not a concrete X.Y.Z
    version (nothing to enforce against).
    """
    if not pin or not _CONCRETE_VERSION_RE.fullmatch(pin):
        return
    actual = parse_bazel_version(version_output)
    if actual != pin:
        raise SystemExit(
            f"release must use the pinned Bazel {pin} (from .bazeliskrc), but "
            f"`bazel --version` reports {actual or version_output.strip()!r}. "
            f"Cut the release through bazelisk (and without a USE_BAZEL_VERSION "
            f"override) so the example lockfile digest matches CI."
        )


def read_current_version(path="MODULE.bazel", use_stdin=False):
    """Read MODULE.bazel (from path or stdin) and return its version."""
    text = sys.stdin.read() if use_stdin else open(path, encoding="utf-8").read()
    return parse_version(text)


def _run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)


def _git_out(cmd):
    return subprocess.run(["git", *cmd], check=True, text=True,
                          capture_output=True).stdout.strip()


def require_gh():
    """Fail early if the GitHub CLI (used to open the release PR) is missing.

    Like `git` and `bazel`, `gh` is expected on the maintainer's PATH; this
    just turns a late, cryptic "command not found" into an actionable message
    before any of the release mutations below run.
    """
    if shutil.which("gh") is None:
        raise SystemExit(
            "gh CLI is required to open the release PR; install it from "
            "https://cli.github.com and authenticate with `gh auth login`"
        )


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

    year = datetime.date.today().year

    if args.dry_run:
        stale = bump_copyrights(year, dry_run=True)
        print(f"[dry-run] {old} -> {new} (branch {branch}, tag {tag})")
        print(f"[dry-run] would bump copyright year to {year} in {len(stale)} file(s)")
        return 0

    # Fail before mutating anything if the tool that opens the PR is absent.
    require_gh()

    # The example lockfile is regenerated below; ensure we'll do so with the
    # same Bazel version CI uses, i.e. that bazelisk honored .bazeliskrc.
    rc_path = os.path.join(EXAMPLE_LOCK_DIR, ".bazeliskrc")
    pin = parse_bazelisk_pin(open(rc_path, encoding="utf-8").read()) \
        if os.path.exists(rc_path) else None
    bazel_version = subprocess.run(["bazel", "--version"], cwd=EXAMPLE_LOCK_DIR,
                                   text=True, capture_output=True).stdout
    check_pinned_bazel(pin, bazel_version)

    try:
        with open(args.file, "w", encoding="utf-8") as f:
            f.write(set_version(text, new))

        # Refresh copyright headers to the current year across the repo.
        bumped = bump_copyrights(year)

        # Keep the committed example lockfile in sync with the bumped version.
        _run(["bazel", "mod", "deps", "--lockfile_mode=update"], cwd=EXAMPLE_LOCK_DIR)
        # Normalize formatting.
        _run(["bazel", "run", "//tools/buildifier:buildifier"])

        _run(["git", "checkout", "-b", branch])
        _run(["git", "add", "MODULE.bazel", f"{EXAMPLE_LOCK_DIR}/MODULE.bazel.lock",
              *bumped])
        _run(["git", "commit", "-m", f"Bump version to {new}"])
        _run(["git", "push", "-u", "origin", branch])
        body = (
            f"Automated release PR opened by `bazel run //tools:release`.\n\n"
            f"- Bumps the module version: `{old}` -> `{new}`\n"
            f"- Refreshes the example lockfile "
            f"(`{EXAMPLE_LOCK_DIR}/MODULE.bazel.lock`)\n"
            f"- Extends Swift Navigation copyright headers to {year}\n\n"
            f"Merging to `main` triggers `.github/workflows/release.yaml`, "
            f"which tags `{tag}` and creates the GitHub release."
        )
        _run(["gh", "pr", "create", "--repo", REPO,
              "--title", f"Bump version to {new}", "--body", body])
        print(f"Opened release PR for {new}.")
        return 0
    except Exception:
        print(
            f"release failed mid-way. To reset:\n"
            f"  git checkout main && git branch -D {branch} 2>/dev/null; "
            f"git checkout -- .",
            file=sys.stderr,
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())

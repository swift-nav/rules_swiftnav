# Copyright (C) 2022-2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""Emit the LFS lockfile (workspace path -> sha256 oid) for the LFS-tracked files.

Works on both LFS pointers and pulled files, so the lockfile does not depend on
whether `git lfs pull` ran. Reads no git state: a Bazel sandbox has no .git.
"""

import argparse
import hashlib
import json
import re

_SPEC = b"version https://git-lfs.github.com/spec/v1"
_OID = re.compile(rb"^oid sha256:([0-9a-f]{64})$", re.MULTILINE)


def pattern_to_regex(pattern):
    """Translates a gitattributes pattern to a regex matching workspace paths."""
    # shortcut: subset of git's wildmatch; port https://github.com/git-lfs/wildmatch when a repo needs more.
    if "\\" in pattern or "[:" in pattern:
        raise ValueError(
            f"unsupported gitattributes pattern {pattern!r}: escapes and [[:class:]] are not implemented"
        )
    anchored = "/" in pattern
    pattern = pattern.removeprefix("/")
    out = []
    i = 0
    while i < len(pattern):
        at_segment_start = i == 0 or pattern[i - 1] == "/"
        if at_segment_start and pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif at_segment_start and pattern[i:] == "**":
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        elif pattern[i] == "[" and "]" in pattern[i + 2 :]:
            end = pattern.index("]", i + 2)
            body = pattern[i + 1 : end].replace("\\", "\\\\")
            if body[0] in "!^":
                body = "^" + body[1:]
            out.append("[" + body + "]")
            i = end + 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    prefix = "" if anchored else "(?:.*/)?"
    return re.compile(prefix + "".join(out))


def parse_gitattributes(text):
    """Returns [(regex, is_lfs)] for every line that sets or unsets `filter`.

    shortcut: reads one root .gitattributes; nested ones in subdirectories are
    ignored. Support them when a consumer repo has any.
    """
    rules = []
    for line in text.splitlines():
        # shortcut: quoted patterns and macro attributes are not supported; orion uses neither.
        fields = line.split()
        if not fields or fields[0].startswith("#"):
            continue
        for attr in fields[1:]:
            if attr in ("-filter", "!filter") or attr.startswith("filter="):
                rules.append((pattern_to_regex(fields[0]), attr == "filter=lfs"))
    return rules


def is_lfs(rules, path):
    tracked = False
    for regex, value in rules:
        if regex.fullmatch(path):
            tracked = value
    return tracked


def oid(file):
    """The pointer's oid, or the content's sha256, which is the same value by spec."""
    with open(file, "rb") as f:
        head = f.read(len(_SPEC))
        if head == _SPEC:
            match = _OID.search(head + f.read(1024))
            if not match:
                raise ValueError(f"{file}: LFS pointer without sha256 oid")
            return match.group(1).decode()
        digest = hashlib.sha256(head)
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
        return digest.hexdigest()


def generate(gitattributes, files):
    """Maps each LFS-tracked workspace path in `files` [(file, path)] to its oid."""
    rules = parse_gitattributes(gitattributes)
    return {path: oid(file) for file, path in files if is_lfs(rules, path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, fromfile_prefix_chars="@")
    parser.add_argument("--gitattributes", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--file",
        action="append",
        default=[],
        nargs=2,
        metavar=("FILE", "PATH"),
        help="File to read and its workspace-relative path.",
    )
    args = parser.parse_args()

    with open(args.gitattributes, encoding="utf-8") as f:
        lock = generate(f.read(), args.file)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(json.dumps(dict(sorted(lock.items())), indent=2) + "\n")


if __name__ == "__main__":
    main()

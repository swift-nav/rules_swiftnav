# Copyright (C) 2022-2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""Upload data files to a content-addressed S3 bucket, or fetch them into the workspace.

`upload` stores each file at `s3://<bucket>/<prefix>/<sha256>`, skipping objects
that already exist, and records `path -> sha256` in the lockfile. `fetch` copies
lockfile entries into the workspace for use outside Bazel. Both shell out to the
`aws` CLI, so they use the caller's AWS credentials.

Paths are workspace-relative; `bazel run` sets BUILD_WORKSPACE_DIRECTORY.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile


def sha256(file):
    digest = hashlib.sha256()
    with open(file, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_lock(lockfile):
    if not os.path.exists(lockfile):
        return {}
    with open(lockfile, encoding="utf-8") as f:
        return json.load(f)


def write_lock(lockfile, lock):
    with open(lockfile, "w", encoding="utf-8") as f:
        f.write(json.dumps(dict(sorted(lock.items())), indent=2) + "\n")


def normalize(path):
    """Workspace-relative path in the form the lockfile uses."""
    path = os.path.normpath(path).replace(os.sep, "/")
    if path.startswith("../") or path == ".." or os.path.isabs(path):
        raise ValueError(f"{path}: must be inside the workspace")
    return path


class AwsCliStore:
    """Objects at `s3://<bucket>/<prefix>/<sha256>`, accessed with the `aws` CLI."""

    def __init__(self, bucket, prefix, endpoint_url=None):
        self.bucket = bucket
        self.prefix = prefix
        self.endpoint_args = ["--endpoint-url", endpoint_url] if endpoint_url else []

    def key(self, digest):
        return f"{self.prefix}/{digest}" if self.prefix else digest

    def _aws(self, *args, check=True):
        return subprocess.run(
            ["aws", *self.endpoint_args, *args],
            check=check,
            capture_output=True,
            text=True,
        )

    def exists(self, digest):
        result = self._aws(
            "s3api",
            "head-object",
            "--bucket",
            self.bucket,
            "--key",
            self.key(digest),
            check=False,
        )
        if result.returncode == 0:
            return True
        if "Not Found" in result.stderr or "404" in result.stderr:
            return False
        raise RuntimeError(f"aws s3api head-object failed: {result.stderr.strip()}")

    def put(self, file, digest):
        self._aws(
            "s3",
            "cp",
            "--only-show-errors",
            file,
            f"s3://{self.bucket}/{self.key(digest)}",
        )

    def get(self, digest, file):
        self._aws(
            "s3",
            "cp",
            "--only-show-errors",
            f"s3://{self.bucket}/{self.key(digest)}",
            file,
        )


def upload(store, workspace, lockfile, paths, log=print):
    """Uploads `paths` and records them in `lockfile`. Returns the updated lock."""
    lock = read_lock(lockfile)
    for path in sorted({normalize(p) for p in paths}):
        file = os.path.join(workspace, path)
        if not os.path.isfile(file):
            raise FileNotFoundError(f"{path}: no such file in the workspace")
        digest = sha256(file)
        if store.exists(digest):
            log(f"{path}: {digest} already in bucket")
        else:
            log(f"{path}: uploading {digest}")
            store.put(file, digest)
        lock[path] = digest
    write_lock(lockfile, lock)
    return lock


def select(lock, patterns):
    """Lockfile paths equal to or under any of `patterns`; all paths when empty."""
    if not patterns:
        return sorted(lock)
    prefixes = [normalize(p).rstrip("/") for p in patterns]
    selected = [
        p for p in lock if any(p == q or p.startswith(q + "/") for q in prefixes)
    ]
    if not selected:
        raise ValueError(f"no lockfile entry matches {' '.join(patterns)}")
    return sorted(selected)


def fetch(store, workspace, lockfile, patterns, log=print):
    """Downloads the selected lockfile entries into `workspace`, verifying sha256."""
    lock = read_lock(lockfile)
    for path in select(lock, patterns):
        digest = lock[path]
        dest = os.path.join(workspace, path)
        if os.path.isfile(dest) and sha256(dest) == digest:
            continue
        log(f"{path}: fetching {digest}")
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
        with tempfile.TemporaryDirectory(dir=os.path.dirname(dest) or ".") as tmp:
            part = os.path.join(tmp, "object")
            store.get(digest, part)
            actual = sha256(part)
            if actual != digest:
                raise RuntimeError(f"{path}: expected sha256 {digest}, got {actual}")
            shutil.move(part, dest)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", default="sha256")
    parser.add_argument("--endpoint-url", help="Passed to the aws CLI.")
    parser.add_argument(
        "--lockfile", required=True, help="Workspace-relative lockfile path."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    up = sub.add_parser("upload", help="Upload files and record them in the lockfile.")
    up.add_argument("paths", nargs="+", metavar="PATH")
    down = sub.add_parser("fetch", help="Download lockfile entries into the workspace.")
    down.add_argument(
        "paths", nargs="*", metavar="PATH", help="Files or directories; all when empty."
    )
    args = parser.parse_args(argv)

    workspace = os.environ.get("BUILD_WORKSPACE_DIRECTORY", os.getcwd())
    # Resolve paths given relative to the directory `bazel run` was invoked from.
    cwd = os.environ.get("BUILD_WORKING_DIRECTORY", workspace)
    paths = [os.path.relpath(os.path.join(cwd, p), workspace) for p in args.paths]
    store = AwsCliStore(args.bucket, args.prefix, args.endpoint_url)
    lockfile = os.path.join(workspace, args.lockfile)
    try:
        if args.command == "upload":
            upload(store, workspace, lockfile, paths)
        else:
            fetch(store, workspace, lockfile, paths)
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as e:
        stderr = getattr(e, "stderr", None)
        print(f"s3_data: {e}{': ' + stderr.strip() if stderr else ''}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

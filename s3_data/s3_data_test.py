# Copyright (C) 2022-2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.
"""Tests for s3_data.py. Run with: bazel test //s3_data:s3_data_test"""

import hashlib
import json
import os
import shutil
import tempfile
import unittest

from s3_data.s3_data import fetch, normalize, select, upload


class FakeStore:
    def __init__(self):
        self.objects = {}
        self.puts = []

    def exists(self, digest):
        return digest in self.objects

    def put(self, file, digest):
        with open(file, "rb") as f:
            self.objects[digest] = f.read()
        self.puts.append(digest)

    def get(self, digest, file):
        with open(file, "wb") as f:
            f.write(self.objects[digest])


def _digest(content):
    return hashlib.sha256(content).hexdigest()


class S3DataTest(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.workspace)
        self.lockfile = os.path.join(self.workspace, "data.lock.json")
        self.store = FakeStore()

    def write(self, path, content):
        file = os.path.join(self.workspace, path)
        os.makedirs(os.path.dirname(file), exist_ok=True)
        with open(file, "wb") as f:
            f.write(content)

    def read(self, path):
        with open(os.path.join(self.workspace, path), "rb") as f:
            return f.read()

    def test_upload_records_sorted_lockfile_and_dedups_content(self):
        self.write("data/b.bin", b"same")
        self.write("data/a.bin", b"same")
        upload(
            self.store,
            self.workspace,
            self.lockfile,
            ["data/b.bin", "./data/a.bin"],
            log=lambda _: None,
        )

        with open(self.lockfile, encoding="utf-8") as f:
            text = f.read()
        self.assertEqual(list(json.loads(text)), ["data/a.bin", "data/b.bin"])
        self.assertEqual(set(json.loads(text).values()), {_digest(b"same")})
        self.assertEqual(self.store.puts, [_digest(b"same")])
        self.assertTrue(text.endswith("}\n"))

    def test_upload_keeps_other_entries_and_updates_changed_file(self):
        self.write("data/a.bin", b"v1")
        self.write("data/b.bin", b"other")
        upload(
            self.store,
            self.workspace,
            self.lockfile,
            ["data/a.bin", "data/b.bin"],
            log=lambda _: None,
        )
        self.write("data/a.bin", b"v2")
        lock = upload(
            self.store,
            self.workspace,
            self.lockfile,
            ["data/a.bin"],
            log=lambda _: None,
        )

        self.assertEqual(
            lock, {"data/a.bin": _digest(b"v2"), "data/b.bin": _digest(b"other")}
        )

    def test_upload_rejects_missing_file_and_paths_outside_workspace(self):
        with self.assertRaises(FileNotFoundError):
            upload(
                self.store,
                self.workspace,
                self.lockfile,
                ["nope.bin"],
                log=lambda _: None,
            )
        with self.assertRaises(ValueError):
            normalize("../outside.bin")

    def test_fetch_restores_selected_files(self):
        self.write("data/x/a.bin", b"a")
        self.write("data/y/b.bin", b"b")
        upload(
            self.store,
            self.workspace,
            self.lockfile,
            ["data/x/a.bin", "data/y/b.bin"],
            log=lambda _: None,
        )
        os.remove(os.path.join(self.workspace, "data/x/a.bin"))
        os.remove(os.path.join(self.workspace, "data/y/b.bin"))

        fetch(self.store, self.workspace, self.lockfile, ["data/x"], log=lambda _: None)

        self.assertEqual(self.read("data/x/a.bin"), b"a")
        self.assertFalse(os.path.exists(os.path.join(self.workspace, "data/y/b.bin")))

    def test_fetch_rejects_corrupt_object(self):
        self.write("data/a.bin", b"good")
        upload(
            self.store,
            self.workspace,
            self.lockfile,
            ["data/a.bin"],
            log=lambda _: None,
        )
        os.remove(os.path.join(self.workspace, "data/a.bin"))
        self.store.objects[_digest(b"good")] = b"bad"

        with self.assertRaises(RuntimeError):
            fetch(self.store, self.workspace, self.lockfile, [], log=lambda _: None)
        self.assertFalse(os.path.exists(os.path.join(self.workspace, "data/a.bin")))

    def test_select_matches_whole_path_segments(self):
        lock = {"data/ab/c.bin": "0", "data/a/c.bin": "1", "data/a.bin": "2"}
        self.assertEqual(select(lock, ["data/a"]), ["data/a/c.bin"])
        self.assertEqual(select(lock, []), sorted(lock))
        with self.assertRaises(ValueError):
            select(lock, ["missing"])


if __name__ == "__main__":
    unittest.main()

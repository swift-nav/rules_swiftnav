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
"""Tests for generate_lockfile.py. Run with: bazel test //lfs:generate_lockfile_test"""

import hashlib
import os
import sys
import tempfile
import unittest
from unittest import mock

from lfs import generate_lockfile
from lfs.generate_lockfile import generate, is_lfs, parse_gitattributes

_GITATTRIBUTES = """\
# comment
test_data/**/*.atx filter=lfs diff=lfs merge=lfs -text
test_data/**/*.pb.a[a-z] filter=lfs diff=lfs merge=lfs -text
tools/data/** filter=lfs diff=lfs merge=lfs -text
tools/data/keep.txt -filter
*.bin filter=lfs -text
*.bin !filter
*.bin filter=lfs
docs/*.bin -filter
"""

_CONTENT = b"real LFS content\n"
_OID = hashlib.sha256(_CONTENT).hexdigest()
_POINTER = (
    f"version https://git-lfs.github.com/spec/v1\noid sha256:{_OID}\nsize {len(_CONTENT)}\n"
).encode()


class PatternTest(unittest.TestCase):
    def setUp(self):
        self.rules = parse_gitattributes(_GITATTRIBUTES)

    def test_double_star_matches_zero_or_more_dirs(self):
        self.assertTrue(is_lfs(self.rules, "test_data/a.atx"))
        self.assertTrue(is_lfs(self.rules, "test_data/x/y/a.atx"))
        self.assertFalse(is_lfs(self.rules, "other/test_data/a.atx"))
        self.assertFalse(is_lfs(self.rules, "test_data/a.atxx"))

    def test_bracket_range(self):
        self.assertTrue(is_lfs(self.rules, "test_data/x/a.pb.aa"))
        self.assertTrue(is_lfs(self.rules, "test_data/a.pb.az"))
        self.assertFalse(is_lfs(self.rules, "test_data/a.pb.a1"))
        self.assertFalse(is_lfs(self.rules, "test_data/a.pb"))

    def test_trailing_double_star_matches_everything_below(self):
        self.assertTrue(is_lfs(self.rules, "tools/data/a"))
        self.assertTrue(is_lfs(self.rules, "tools/data/x/y/z.csv"))
        self.assertFalse(is_lfs(self.rules, "tools/data"))

    def test_basename_pattern_matches_at_any_depth(self):
        self.assertTrue(is_lfs(self.rules, "a.bin"))
        self.assertTrue(is_lfs(self.rules, "x/y/a.bin"))
        self.assertFalse(is_lfs(self.rules, "x/a.bin.txt"))

    def test_later_lines_override_and_unset(self):
        self.assertFalse(is_lfs(self.rules, "tools/data/keep.txt"))
        self.assertFalse(is_lfs(self.rules, "docs/a.bin"))
        self.assertTrue(is_lfs(self.rules, "docs/x/a.bin"))


class GenerateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, content):
        path = os.path.join(self.tmp.name, name)
        with open(path, "wb") as f:
            f.write(content)
        return path

    def test_pointer_and_pulled_file_yield_same_oid(self):
        files = [
            (self.write("pointer", _POINTER), "test_data/p.atx"),
            (self.write("pulled", _CONTENT), "test_data/q.atx"),
            (self.write("plain", b"not lfs"), "test_data/readme.md"),
        ]
        self.assertEqual(
            generate(_GITATTRIBUTES, files),
            {"test_data/p.atx": _OID, "test_data/q.atx": _OID},
        )

    def test_output_is_sorted_and_deterministic(self):
        attrs = self.write("attrs", _GITATTRIBUTES.encode())
        b = self.write("b", _CONTENT)
        a = self.write("a", _POINTER)
        outputs = []
        for order in (
            ["--file", b, "z.bin", "--file", a, "a.bin"],
            ["--file", a, "a.bin", "--file", b, "z.bin"],
        ):
            out = os.path.join(self.tmp.name, "out.json")
            argv = ["prog", "--gitattributes", attrs, "--output", out, *order]
            with mock.patch.object(sys, "argv", argv):
                generate_lockfile.main()
            with open(out, encoding="utf-8") as f:
                outputs.append(f.read())
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(
            outputs[0], f'{{\n  "a.bin": "{_OID}",\n  "z.bin": "{_OID}"\n}}\n'
        )


if __name__ == "__main__":
    unittest.main()

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
"""Tests for release.py. Run with: bazel test //tools:release_test"""

import io
import unittest
from unittest import mock

from tools.release import bump_version, parse_version, read_current_version, set_version

MODULE = '''module(
    name = "rules_swiftnav",
    version = "0.20.0",
    compatibility_level = 1,
)

bazel_dep(name = "bazel_skylib", version = "1.8.2")
bazel_dep(name = "platforms", version = "1.0.0")
'''


class ParseVersionTest(unittest.TestCase):
    def test_reads_version_from_module_block(self):
        self.assertEqual(parse_version(MODULE), "0.20.0")

    def test_raises_when_missing(self):
        with self.assertRaises(ValueError):
            parse_version('module(name = "x")\n')


class BumpVersionTest(unittest.TestCase):
    def test_patch(self):
        self.assertEqual(bump_version("0.20.0", "patch"), "0.20.1")

    def test_minor(self):
        self.assertEqual(bump_version("0.20.3", "minor"), "0.21.0")

    def test_major(self):
        self.assertEqual(bump_version("0.20.3", "major"), "1.0.0")

    def test_rejects_bad_part(self):
        with self.assertRaises(ValueError):
            bump_version("0.20.0", "huge")


class SetVersionTest(unittest.TestCase):
    def test_replaces_only_module_version(self):
        out = set_version(MODULE, "0.21.0")
        self.assertEqual(parse_version(out), "0.21.0")
        self.assertIn('compatibility_level = 1', out)

    def test_leaves_bazel_dep_versions_untouched(self):
        out = set_version(MODULE, "0.21.0")
        self.assertEqual(parse_version(out), "0.21.0")
        self.assertIn('version = "1.8.2"', out)
        self.assertIn('version = "1.0.0"', out)

    def test_idempotent_round_trip(self):
        self.assertEqual(parse_version(set_version(MODULE, "9.9.9")), "9.9.9")


class ReadCurrentVersionTest(unittest.TestCase):
    def test_reads_from_stdin(self):
        with mock.patch("sys.stdin", io.StringIO(MODULE)):
            self.assertEqual(read_current_version(path=None, use_stdin=True), "0.20.0")


if __name__ == "__main__":
    unittest.main()

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
"""Tests for release.py. Run with: bazel test //tools:release_test"""

import io
import os
import tempfile
import unittest
from unittest import mock

from tools.release import (
    bump_copyrights,
    bump_version,
    parse_version,
    read_current_version,
    set_copyright_years,
    set_version,
)

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


class SetCopyrightYearsTest(unittest.TestCase):
    HEADER = "# Copyright (C) {} Swift Navigation Inc.\n"

    def test_single_year_becomes_range(self):
        out = set_copyright_years(self.HEADER.format("2022"), 2026)
        self.assertEqual(out, self.HEADER.format("2022-2026"))

    def test_extends_existing_range_end(self):
        out = set_copyright_years(self.HEADER.format("2022-2025"), 2026)
        self.assertEqual(out, self.HEADER.format("2022-2026"))

    def test_single_year_already_current_is_unchanged(self):
        text = self.HEADER.format("2026")
        self.assertEqual(set_copyright_years(text, 2026), text)

    def test_range_already_current_is_idempotent(self):
        text = self.HEADER.format("2022-2026")
        self.assertEqual(set_copyright_years(text, 2026), text)

    def test_leaves_non_swiftnav_copyright_untouched(self):
        text = "# Copyright (C) 2019 Some Other Corp.\n"
        self.assertEqual(set_copyright_years(text, 2026), text)

    def test_updates_every_header_in_text(self):
        text = self.HEADER.format("2022") + self.HEADER.format("2023-2024")
        expected = self.HEADER.format("2022-2026") + self.HEADER.format("2023-2026")
        self.assertEqual(set_copyright_years(text, 2026), expected)


class BumpCopyrightsTest(unittest.TestCase):
    # Built via format() so the source has no literal "(C) <year> Swift
    # Navigation" header for the release tool itself to rewrite.
    HEADER = "# Copyright (C) {} Swift Navigation Inc.\n"

    def _write(self, d, name, text):
        path = os.path.join(d, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def test_rewrites_only_changed_files(self):
        with tempfile.TemporaryDirectory() as d:
            stale = self._write(d, "a.py", self.HEADER.format("2022"))
            current = self._write(d, "b.py", self.HEADER.format("2022-2026"))
            no_header = self._write(d, "c.txt", "nothing here\n")
            with mock.patch("tools.release.list_tracked_files",
                            return_value=[stale, current, no_header]):
                changed = bump_copyrights(2026)
            self.assertEqual(changed, [stale])
            with open(stale, encoding="utf-8") as f:
                self.assertEqual(f.read(), self.HEADER.format("2022-2026"))

    def test_dry_run_reports_without_writing(self):
        with tempfile.TemporaryDirectory() as d:
            original = self.HEADER.format("2022")
            stale = self._write(d, "a.py", original)
            with mock.patch("tools.release.list_tracked_files", return_value=[stale]):
                changed = bump_copyrights(2026, dry_run=True)
            self.assertEqual(changed, [stale])
            with open(stale, encoding="utf-8") as f:
                self.assertEqual(f.read(), original)

    def test_skips_binary_or_undecodable_files(self):
        with tempfile.TemporaryDirectory() as d:
            binary = os.path.join(d, "blob.bin")
            with open(binary, "wb") as f:
                f.write(b"\xff\xfe\x00\x01")
            with mock.patch("tools.release.list_tracked_files", return_value=[binary]):
                self.assertEqual(bump_copyrights(2026), [])


class ReadCurrentVersionTest(unittest.TestCase):
    def test_reads_from_stdin(self):
        with mock.patch("sys.stdin", io.StringIO(MODULE)):
            self.assertEqual(read_current_version(path=None, use_stdin=True), "0.20.0")


if __name__ == "__main__":
    unittest.main()

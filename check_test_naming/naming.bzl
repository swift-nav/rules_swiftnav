# Copyright (C) 2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""Test naming convention shared by the check_test_naming aspect and rule."""

load("@bazel_skylib//lib:paths.bzl", "paths")

# Extensions of the source files whose names are checked. Only languages that
# name files in snake_case are listed; headers and data files are ignored.
SOURCE_EXTENSIONS = ["c", "cc", "cpp", "cxx", "go", "py", "rs", "sh"]

def _stem(path):
    return paths.split_extension(paths.basename(path))[0]

def test_naming_errors(name, srcs):
    """Checks a test target against the test naming convention.

    The convention is:
      * the target name ends with '_test' and does not start with 'test_',
      * no source file name starts with 'test_',
      * at least one source file name ends with '_test' (when the target has
        source files at all).

    Args:
        name: The name of the test target.
        srcs: Paths of the test's source files. Files whose extension is not in
            SOURCE_EXTENSIONS are ignored.

    Returns:
        A list of error messages, empty when the target follows the convention.
    """
    errors = []

    if not name.endswith("_test"):
        errors.append("target name '{}' must end with '_test'".format(name))
    if name.startswith("test_"):
        errors.append("target name '{}' must not start with 'test_'".format(name))

    checked = [src for src in srcs if paths.split_extension(src)[1][1:] in SOURCE_EXTENSIONS]

    for src in checked:
        if _stem(src).startswith("test_"):
            errors.append("source '{}' must not start with 'test_'".format(src))

    if checked and not [src for src in checked if _stem(src).endswith("_test")]:
        errors.append("at least one source must end with '_test', got: {}".format(", ".join(checked)))

    return errors
